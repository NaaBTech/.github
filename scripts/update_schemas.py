#!/usr/bin/env python3
"""Refresh the vendored JSON Schemas used to validate GitHub forms.

This script is a MAINTENANCE tool. It is not run by CI, because CI must not
depend on network access. Run it manually when the upstream schemas change:

    python scripts/update_schemas.py

The refresh is transactional. Everything is downloaded, parsed, validated,
patched and hashed in memory first. The complete new artifact set is written to
a staging directory, verified there, and only then promoted over the existing
files. If any step fails, the previous schemas and provenance are left
untouched, and the staging directory is removed.

It downloads the upstream schemas from SchemaStore, applies the documented
patch described in schemas/README.md, regenerates the private vulnerability
reporting form schema from the patched issue forms schema, refreshes the
Apache-2.0 license and NOTICE files for the vendored material, and rewrites
schemas/PROVENANCE.json.
"""

import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover
    sys.stderr.write("jsonschema is required: pip install -r requirements-docs.txt\n")
    raise SystemExit(2)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "schemas")

# The upstream schema files, and where they live in the SchemaStore repository.
UPSTREAM_SCHEMAS = {
    "github-issue-forms.json": {
        "url": "https://www.schemastore.org/github-issue-forms.json",
        "repository_path": "src/schemas/json/github-issue-forms.json",
    },
    "github-issue-config.json": {
        "url": "https://www.schemastore.org/github-issue-config.json",
        "repository_path": "src/schemas/json/github-issue-config.json",
    },
}

# The license and notice that cover the vendored material. They are refreshed
# with the schemas so that the attribution cannot drift away from them.
UPSTREAM_THIRD_PARTY = {
    "third-party/LICENSE-Apache-2.0.txt": "https://raw.githubusercontent.com/SchemaStore/schemastore/master/LICENSE",
    "third-party/NOTICE-SchemaStore.txt": "https://raw.githubusercontent.com/SchemaStore/schemastore/master/NOTICE",
}

# The SchemaStore repository distributes these files under its own license.
UPSTREAM_LICENSE = "Apache-2.0"
UPSTREAM_REPOSITORY = "https://github.com/SchemaStore/schemastore"

# Element types GitHub supports in a private vulnerability reporting form.
# https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository
VULNERABILITY_TYPES = ["checkboxes", "dropdown", "input", "markdown", "textarea"]

# Top-level keys GitHub accepts in a private vulnerability reporting form.
VULNERABILITY_TOP_LEVEL = ["name", "description", "body"]

# GitHub's documentation lists `min_length` as a valid validation for `input`
# and `textarea`. The upstream SchemaStore schema only lists `required`, so a
# documented, valid form would be rejected. schemas/README.md records this.
PATCH_NOTE = "min_length added for input and textarea per GitHub's form schema documentation"

# Apache License 2.0 section 4(b) requires modified files to carry a
# prominent notice that they were changed. This key is that notice.
MODIFICATION_KEY = "x-naabtech-modification"
MODIFICATION_NOTE = (
    "Modified by NaaB Tech. Change: added the 'min_length' validation to the "
    "'input' and 'textarea' elements, which GitHub's form schema documentation "
    "lists as supported but the upstream SchemaStore schema omits. No other "
    "part of the upstream schema was changed. Upstream file: "
    "src/schemas/json/github-issue-forms.json in https://github.com/SchemaStore/schemastore "
    "(Apache License 2.0). See schemas/README.md and schemas/PROVENANCE.json."
)

DERIVED_MODIFICATION_NOTE = (
    "Derived work created by NaaB Tech. This schema was generated from the "
    "vendored github-issue-forms.json by restricting the element types and the "
    "top-level keys that GitHub documents as supported for private "
    "vulnerability reporting forms. It is not a schema published by GitHub. "
    "See schemas/README.md and schemas/PROVENANCE.json."
)


class UpdateError(RuntimeError):
    """Raised when a refresh cannot be completed safely."""


class RollbackError(UpdateError):
    """Raised when a promotion failed and the rollback could not fully restore.

    The surviving backups are the only recoverable copies of the original
    files, and their location is reported in the message.
    """


# Where the original files are kept while a promotion is in progress. A
# backup that could not be restored is left here on purpose.
BACKUP_DIR_NAME = ".naabtech-backups"

# Every promotion transaction gets its own directory below the backup root, so
# a later transaction can never overwrite the recovery copy of an earlier one.
TRANSACTION_PREFIX = "transaction-"

# Held for the duration of a refresh so that two refreshes cannot interfere
# with each other's backup or promotion state.
LOCK_FILE_NAME = ".naabtech-update.lock"


# --------------------------------------------------------------------------
# Path containment
# --------------------------------------------------------------------------

def _is_within(root, path):
    """True when path is the root itself or sits underneath it."""
    try:
        return os.path.commonpath([root, path]) == root
    except ValueError:
        # Different drives on Windows, or a mix of absolute and relative paths.
        return False


def contained_path(root, relative, description, allow_missing=False):
    """Return the path for a location under a trusted root, or raise UpdateError.

    The whole candidate path is canonicalized, so a symbolic link in any
    parent component is resolved as well. A path whose canonical destination
    lies outside the trusted root is rejected *before* it is read, created,
    written, overwritten or deleted.

    The returned path is the lexical location under the canonical root, so an
    operation never writes through a symbolic link.
    """
    canonical_root = os.path.realpath(root)
    candidate = os.path.join(canonical_root, relative.replace("/", os.sep))
    try:
        resolved = os.path.realpath(candidate)
    except (OSError, ValueError):
        raise UpdateError(f"{description} cannot be resolved: {candidate}")
    if not _is_within(canonical_root, resolved):
        raise UpdateError(
            f"{description} is outside {canonical_root}: {candidate} resolves to {resolved}"
        )
    if not os.path.lexists(candidate):
        if not allow_missing:
            raise UpdateError(f"{description} does not exist: {candidate}")
        return candidate
    if not os.path.exists(resolved):
        raise UpdateError(f"{description} is a broken symbolic link: {candidate}")
    return candidate


def canonical_repository_root(root=None):
    """The canonical repository root that every path is checked against.

    ``root`` defaults to the repository that holds this script. The parameter
    exists so that the behaviour can be exercised against a temporary
    directory without weakening the containment check.
    """
    return os.path.realpath(root) if root else os.path.realpath(ROOT)


def canonical_schema_dir(root=None):
    """The canonical schema directory, which must be inside the repository.

    A schemas directory that is a symbolic link to an internal directory is
    accepted, because it stays inside the repository. One that points outside
    is rejected before anything is read or written.

    ``root`` is the repository the schema directory must sit inside. It
    defaults to the repository that holds this script.
    """
    canonical_root = canonical_repository_root(root)
    try:
        return contained_path(canonical_root, "schemas", "the schemas directory")
    except UpdateError as exc:
        raise UpdateError(
            "the schemas directory is not usable: it must be a directory inside the "
            f"repository {canonical_root}. {exc}"
        )


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "naabtech-docs-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def encode_json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n").encode("utf-8")


def apply_min_length_patch(schema):
    """Add `min_length` to the input and textarea validations, and a notice."""
    definitions = schema.setdefault("definitions", {})
    base = definitions.get("validations", {})
    extended = {
        "title": base.get("title", "validation options"),
        "description": base.get("description", "") + "\n" + PATCH_NOTE,
        "type": "object",
        "properties": dict(base.get("properties", {})),
        "additionalProperties": False,
    }
    extended["properties"]["min_length"] = {
        "description": "Prevents form submission until the response contains at least the specified number of characters.",
        "type": "integer",
        "minimum": 0,
    }
    definitions["input_validations"] = extended
    definitions["textarea_validations"] = json.loads(json.dumps(extended))

    patched = 0
    for branch in definitions.get("form_item", {}).get("allOf", []):
        const = branch.get("if", {}).get("properties", {}).get("type", {}).get("const")
        if const in ("input", "textarea"):
            ref = f"#/definitions/{const}_validations"
            branch["then"]["properties"]["validations"]["$ref"] = ref
            patched += 1
    if patched != 2:
        raise UpdateError(f"expected to patch 2 validations blocks, patched {patched}")

    schema[MODIFICATION_KEY] = MODIFICATION_NOTE
    return schema


def derive_vulnerability_schema(issue_forms_schema):
    """Restrict the issue forms schema to the vulnerability reporting form rules."""
    schema = json.loads(json.dumps(issue_forms_schema))
    # The identifier points at the file in this repository. It is not a URL that
    # is published anywhere, so it must not look like one.
    schema["$id"] = "https://github.com/NaaBTech/.github/schemas/github-vulnerability-report-form.json"
    schema["title"] = "NaaB Tech private vulnerability reporting form schema (derived, not an official GitHub schema)"
    schema["$comment"] = (
        "Derived from github-issue-forms.json by restricting the element types and "
        "top-level keys that GitHub supports for private vulnerability reporting "
        "forms. This is not a schema published by GitHub. Regenerate with "
        "scripts/update_schemas.py. See schemas/README.md."
    )
    schema[MODIFICATION_KEY] = DERIVED_MODIFICATION_NOTE

    definitions = schema["definitions"]
    definitions["type"]["enum"] = [
        value for value in definitions["type"]["enum"] if value in VULNERABILITY_TYPES
    ]
    kept = []
    for branch in definitions.get("form_item", {}).get("allOf", []):
        const = branch.get("if", {}).get("properties", {}).get("type", {}).get("const")
        if const in VULNERABILITY_TYPES:
            kept.append(branch)
    if len(kept) != len(VULNERABILITY_TYPES):
        raise UpdateError(f"expected {len(VULNERABILITY_TYPES)} element branches, kept {len(kept)}")
    definitions["form_item"]["allOf"] = kept

    schema["properties"] = {k: v for k, v in schema["properties"].items() if k in VULNERABILITY_TOP_LEVEL}
    schema["required"] = ["name", "description", "body"]
    return schema


def check_is_schema(name, data):
    """Raise unless the document is a valid JSON Schema."""
    try:
        validator_for(data).check_schema(data)
    except Exception as exc:  # noqa: BLE001
        raise UpdateError(f"{name} is not a valid JSON Schema: {exc}")


def build_artifacts(downloads):
    """Build the complete artifact set in memory.

    ``downloads`` maps a file name to the bytes fetched for it. Nothing is
    written to disk here, so a failure leaves the repository untouched.
    """
    for name, meta in UPSTREAM_SCHEMAS.items():
        if name not in downloads:
            raise UpdateError(f"missing download for {name}")
    for name in UPSTREAM_THIRD_PARTY:
        if name not in downloads:
            raise UpdateError(f"missing download for {name}")

    parsed = {}
    for name in UPSTREAM_SCHEMAS:
        try:
            parsed[name] = json.loads(downloads[name].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateError(f"{name} could not be parsed as JSON: {exc}")
        check_is_schema(name, parsed[name])

    issue_forms = apply_min_length_patch(parsed["github-issue-forms.json"])
    check_is_schema("github-issue-forms.json", issue_forms)
    vulnerability = derive_vulnerability_schema(issue_forms)
    check_is_schema("github-vulnerability-report-form.json", vulnerability)

    artifacts = {
        "github-issue-forms.json": encode_json(issue_forms),
        "github-issue-config.json": encode_json(parsed["github-issue-config.json"]),
        "github-vulnerability-report-form.json": encode_json(vulnerability),
    }
    for name in UPSTREAM_THIRD_PARTY:
        artifacts[name] = downloads[name]

    provenance = {
        "retrieved_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "https://www.schemastore.org/",
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_license": UPSTREAM_LICENSE,
        "upstream_license_note": (
            "The vendored schema files carry no individual license header. They are "
            "distributed as part of the SchemaStore repository, which is licensed "
            "under Apache-2.0. A copy of that license is at "
            "schemas/third-party/LICENSE-Apache-2.0.txt and the upstream notice is "
            "at schemas/third-party/NOTICE-SchemaStore.txt."
        ),
        "modification_notice": {
            "key": MODIFICATION_KEY,
            "github-issue-forms.json": MODIFICATION_NOTE,
            "github-vulnerability-report-form.json": DERIVED_MODIFICATION_NOTE,
        },
        "schemas": {},
        "third_party": {},
    }

    for name, meta in UPSTREAM_SCHEMAS.items():
        provenance["schemas"][name] = {
            "upstream_url": meta["url"],
            "upstream_repository_path": meta["repository_path"],
            "upstream_sha256": sha256_bytes(downloads[name]),
            "vendored_sha256": sha256_bytes(artifacts[name]),
            "upstream_license": UPSTREAM_LICENSE,
            "patched": name == "github-issue-forms.json",
            "derived": False,
            "modification_notice_key": MODIFICATION_KEY if name == "github-issue-forms.json" else None,
        }

    derived_name = "github-vulnerability-report-form.json"
    provenance["schemas"][derived_name] = {
        "derived_from": "github-issue-forms.json",
        "upstream_url": "https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository",
        "vendored_sha256": sha256_bytes(artifacts[derived_name]),
        "upstream_license": UPSTREAM_LICENSE,
        "license_note": (
            "Derived in this repository from github-issue-forms.json. The restriction "
            "to the element types and top-level keys documented by GitHub is NaaB "
            "Tech's own work. This is not a schema published by GitHub."
        ),
        "patched": False,
        "derived": True,
        "modification_notice_key": MODIFICATION_KEY,
    }

    for name, url in UPSTREAM_THIRD_PARTY.items():
        provenance["third_party"][name] = {
            "upstream_url": url,
            "upstream_sha256": sha256_bytes(downloads[name]),
            "vendored_sha256": sha256_bytes(artifacts[name]),
            "upstream_license": UPSTREAM_LICENSE,
            "role": "license text" if "LICENSE" in name else "upstream notice attribution",
        }

    provenance["schemas"][derived_name]["vendored_sha256"] = sha256_bytes(artifacts[derived_name])
    artifacts["PROVENANCE.json"] = encode_json(provenance)
    return artifacts


def stage_artifacts(artifacts, staging_dir):
    """Write the artifact set into a staging directory.

    Every artifact path is checked against the staging directory, so a
    symbolic link cannot redirect a write outside it.
    """
    staging_root = os.path.realpath(staging_dir)
    for name, payload in artifacts.items():
        path = contained_path(
            staging_root, name, f"the staged artifact {name}", allow_missing=True
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())


def verify_staged(artifacts, staging_dir):
    """Verify that the staged files match what was built, before promotion."""
    staging_root = os.path.realpath(staging_dir)
    for name, payload in artifacts.items():
        path = contained_path(
            staging_root, name, f"the staged artifact {name}", allow_missing=True
        )
        if not os.path.exists(path):
            raise UpdateError(f"staged file is missing: {name}")
        with open(path, "rb") as handle:
            staged = handle.read()
        if sha256_bytes(staged) != sha256_bytes(payload):
            raise UpdateError(f"staged file does not match the built artifact: {name}")
        if name.endswith(".json"):
            try:
                json.loads(staged.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise UpdateError(f"staged file is not valid JSON: {name}: {exc}")


def cleanup_transaction_dir(transaction_dir, backup_root):
    """Remove a transaction directory and the empty directories inside it.

    Directories are removed from the bottom up, so a nested artifact path such
    as ``third-party/NOTICE-SchemaStore.txt`` leaves no empty child directory
    behind. A directory that still holds a backup is never removed, and every
    path that could not be removed is returned.

    The transaction directory is checked against the backup root first, so a
    backup root that is a symbolic link pointing outside the repository cannot
    redirect the removal.
    """
    backup_root = os.path.realpath(backup_root)
    transaction_dir = contained_path(
        backup_root, os.path.basename(transaction_dir), "the transaction directory"
    )
    leftovers = []
    for dirpath, _dirnames, _filenames in os.walk(transaction_dir, topdown=False):
        try:
            os.rmdir(dirpath)
        except OSError:
            leftovers.append(dirpath)
    return leftovers


def acquire_update_lock(target_dir, trusted_root=None):
    """Take the update lock so two refreshes cannot run at the same time.

    Returns the path of the lock file. Raises UpdateError when another
    refresh already holds it.

    The schema directory is checked against the trusted root before the lock
    is created, so a schema directory that points outside the repository
    cannot redirect the lock file.
    """
    root = os.path.realpath(trusted_root) if trusted_root else canonical_repository_root()
    target_root = os.path.realpath(target_dir)
    if not _is_within(root, target_root):
        raise UpdateError(
            f"the schema directory is outside the repository {root}: {target_dir}"
        )
    path = contained_path(
        os.path.realpath(target_dir), LOCK_FILE_NAME, "the update lock", allow_missing=True
    )
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise UpdateError(
            f"another schema refresh appears to be running: {path} exists. "
            "If no refresh is in progress, remove that file and try again."
        )
    with os.fdopen(handle, "w") as stream:
        stream.write(f"pid={os.getpid()}\n")
    return path


def release_update_lock(path):
    """Release the update lock. A failure here is reported, not raised."""
    try:
        os.remove(path)
    except OSError as exc:
        sys.stderr.write(f"update_schemas: could not remove the lock {path}: {exc}\n")


def promote(artifacts, staging_dir, target_dir, trusted_root=None):
    """Move the staged files into place, rolling back on failure.

    ``trusted_root`` is the directory that the schema directory and the
    staging directory must sit inside. It defaults to the repository root. The
    parameter exists so that the behaviour can be exercised against a
    temporary directory without weakening the containment check.

    Each file is replaced individually, so a failure part way through can leave
    a mixture. The previous content of every file is kept in a backup
    directory until the promotion has fully succeeded.

    If the promotion fails, the backups are restored in reverse order and the
    original artifact set is left byte-for-byte unchanged. The restoration
    itself is failure-safe: a backup that cannot be restored is *not* deleted,
    because it is the only remaining recoverable copy of that file, and its
    location is reported instead.

    This is an exception rollback, not a filesystem transaction. A crash or a
    power loss between two replacements can still leave a mixture, and the
    backup directory is what makes that recoverable by hand.
    """
    repository_root = os.path.realpath(trusted_root) if trusted_root else canonical_repository_root()
    target_root = os.path.realpath(target_dir)
    if not _is_within(repository_root, target_root):
        raise UpdateError(
            f"the schema directory is outside the repository {repository_root}: {target_dir}"
        )
    staging_root = os.path.realpath(staging_dir)
    if not _is_within(repository_root, staging_root):
        raise UpdateError(
            f"the staging directory is outside the repository {repository_root}: {staging_dir}"
        )
    # The backup root is checked before it is created, so a symbolic link
    # pointing outside the repository cannot redirect the backups.
    backup_root = contained_path(
        target_root, BACKUP_DIR_NAME, "the backup directory", allow_missing=True
    )
    os.makedirs(backup_root, exist_ok=True)
    # A unique directory per transaction. A later transaction can therefore
    # never overwrite the recovery copy of an earlier one.
    transaction_dir = tempfile.mkdtemp(prefix=TRANSACTION_PREFIX, dir=backup_root)
    backups = {}        # name -> backup path, or None when the file is new
    promoted = []        # names that were successfully replaced
    restored = set()     # names whose original content is back in place
    failures = []        # (name, error) for backups that could not be restored
    succeeded = False

    try:
        for name in artifacts:
            source = contained_path(
                staging_root, name, f"the staged artifact {name}", allow_missing=True
            )
            # The target is checked before it is read, backed up or replaced,
            # so an artifact that is a symbolic link pointing outside the
            # repository is rejected rather than followed.
            target = contained_path(
                target_root, name, f"the target for {name}", allow_missing=True
            )
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if os.path.exists(target):
                # The backup keeps the nested artifact layout.
                backup = contained_path(
                    transaction_dir, name, f"the backup for {name}", allow_missing=True
                )
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                shutil.copy2(target, backup)
                backups[name] = backup
            else:
                backups[name] = None
            os.replace(source, target)
            promoted.append(name)
        succeeded = True
    except Exception as promotion_error:
        for name in reversed(promoted):
            target = os.path.join(target_dir, name.replace("/", os.sep))
            backup = backups.get(name)
            try:
                if backup is not None and os.path.exists(backup):
                    # Copy to a temporary name and move it into place, so the
                    # destination is never left partially overwritten.
                    restore = contained_path(
                        target_root,
                        name.replace("/", os.sep) + ".naabtech-restore",
                        f"the restore file for {name}",
                        allow_missing=True,
                    )
                    shutil.copy2(backup, restore)
                    os.replace(restore, target)
                    restored.add(name)
                elif os.path.exists(target):
                    os.remove(target)
                    restored.add(name)
            except Exception as rollback_error:
                failures.append((name, rollback_error))
                # The backup is the only recoverable copy of this file. It is
                # deliberately kept, and its location is reported.
                sys.stderr.write(
                    f"update_schemas: could not restore {name}: {rollback_error}\n"
                    f"update_schemas: the recoverable copy is kept at {backup}\n"
                )
        if failures:
            raise RollbackError(
                f"promotion failed ({promotion_error}) and {len(failures)} file(s) could not "
                "be restored: " + ", ".join(name for name, _ in failures)
                + f". Recoverable copies are kept in {transaction_dir}"
            ) from promotion_error
        raise
    finally:
        for name, backup in backups.items():
            if not backup or not os.path.exists(backup):
                continue
            # A backup is removed when the file was restored, when the file
            # was never replaced, or when the whole promotion succeeded. A
            # backup that was not restored is the only recoverable copy and
            # is never removed.
            if not (succeeded or name in restored or name not in promoted):
                continue
            try:
                os.remove(backup)
            except OSError as cleanup_error:
                sys.stderr.write(
                    f"update_schemas: could not remove the backup for {name}: {cleanup_error}\n"
                )
        if not failures:
            # Only this transaction's directory is cleaned, and only the empty
            # directories inside it. A recovery directory from an earlier
            # transaction, or one that still holds an un-restored backup, is
            # never removed.
            for leftover in cleanup_transaction_dir(transaction_dir, backup_root):
                sys.stderr.write(
                    f"update_schemas: could not remove {leftover}\n"
                )
            # The backup root is removed only when it is empty, so an earlier
            # recovery directory is never destroyed.
            try:
                os.rmdir(backup_root)
            except OSError:
                pass


def refresh(root=None):
    """Run a complete refresh. Returns the artifact set that was promoted.

    ``root`` is the repository the schema directory must sit inside. It
    defaults to the repository that holds this script.
    """
    # The canonical schema directory is resolved first. If it is a symbolic
    # link pointing outside the repository, the refresh stops before anything
    # is read, created or written.
    repository_root = canonical_repository_root(root)
    schema_dir = canonical_schema_dir(root)
    lock_path = acquire_update_lock(schema_dir, repository_root)
    staging_dir = None
    try:
        downloads = {}
        for name, meta in UPSTREAM_SCHEMAS.items():
            print(f"fetching {meta['url']}")
            downloads[name] = download(meta["url"])
        for name, url in UPSTREAM_THIRD_PARTY.items():
            print(f"fetching {url}")
            downloads[name] = download(url)

        artifacts = build_artifacts(downloads)

        staging_dir = tempfile.mkdtemp(prefix=".staging-", dir=schema_dir)
        stage_artifacts(artifacts, staging_dir)
        verify_staged(artifacts, staging_dir)
        promote(artifacts, staging_dir, schema_dir, repository_root)
    finally:
        if staging_dir:
            shutil.rmtree(staging_dir, ignore_errors=True)
        release_update_lock(lock_path)

    for name in artifacts:
        print(f"promoted schemas/{name}")
    return artifacts


def main():
    try:
        os.makedirs(SCHEMA_DIR, exist_ok=True)
    except OSError as exc:
        sys.stderr.write(
            f"schema refresh failed: the schemas directory could not be created: {exc}\n"
        )
        return 1
    try:
        refresh()
    except RollbackError as exc:
        # The rollback did not fully succeed, so the schema directory may hold
        # partially updated files. Saying otherwise would be wrong.
        sys.stderr.write(
            "schema refresh failed and the rollback was INCOMPLETE.\n"
            f"  {exc}\n"
            "  The schema directory may contain partially updated files. Restore the\n"
            "  affected files from the recovery directory above before running the\n"
            "  refresh again.\n"
        )
        return 1
    except UpdateError as exc:
        sys.stderr.write(
            f"schema refresh failed: {exc}\n"
            "  The refresh was stopped. The schema directory is only guaranteed to be\n"
            "  unchanged when the failure happened before the promotion step.\n"
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            f"schema refresh failed with an unexpected error: {type(exc).__name__}: {exc}\n"
            "  The state of the schema directory cannot be asserted. Check it before\n"
            "  running the refresh again.\n"
        )
        return 1
    print("\nSchemas updated. Review schemas/README.md and re-run the validation tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
