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
    """Write the artifact set into a staging directory."""
    for name, payload in artifacts.items():
        path = os.path.join(staging_dir, name.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())


def verify_staged(artifacts, staging_dir):
    """Verify that the staged files match what was built, before promotion."""
    for name, payload in artifacts.items():
        path = os.path.join(staging_dir, name.replace("/", os.sep))
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


def promote(artifacts, staging_dir, target_dir):
    """Move the staged files into place, rolling back on failure.

    Each file is replaced individually, so a failure part way through can leave
    a mixture. The previous content is restored in that case, so the schemas
    and the provenance record always agree with each other.
    """
    backups = {}
    promoted = []
    try:
        for name in artifacts:
            source = os.path.join(staging_dir, name.replace("/", os.sep))
            target = os.path.join(target_dir, name.replace("/", os.sep))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if os.path.exists(target):
                backup = target + ".naabtech-backup"
                shutil.copy2(target, backup)
                backups[name] = backup
            else:
                backups[name] = None
            os.replace(source, target)
            promoted.append(name)
    except Exception:
        for name in promoted:
            target = os.path.join(target_dir, name.replace("/", os.sep))
            backup = backups.get(name)
            if backup and os.path.exists(backup):
                shutil.copy2(backup, target)
            elif os.path.exists(target):
                os.remove(target)
        raise
    finally:
        for backup in backups.values():
            if backup and os.path.exists(backup):
                os.remove(backup)


def refresh():
    """Run a complete refresh. Returns the artifact set that was promoted."""
    downloads = {}
    for name, meta in UPSTREAM_SCHEMAS.items():
        print(f"fetching {meta['url']}")
        downloads[name] = download(meta["url"])
    for name, url in UPSTREAM_THIRD_PARTY.items():
        print(f"fetching {url}")
        downloads[name] = download(url)

    artifacts = build_artifacts(downloads)

    staging_dir = tempfile.mkdtemp(prefix=".staging-", dir=SCHEMA_DIR)
    try:
        stage_artifacts(artifacts, staging_dir)
        verify_staged(artifacts, staging_dir)
        promote(artifacts, staging_dir, SCHEMA_DIR)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    for name in artifacts:
        print(f"promoted schemas/{name}")
    return artifacts


def main():
    os.makedirs(SCHEMA_DIR, exist_ok=True)
    try:
        refresh()
    except UpdateError as exc:
        sys.stderr.write(f"schema refresh failed, nothing was changed: {exc}\n")
        return 1
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"schema refresh failed, nothing was changed: {type(exc).__name__}: {exc}\n")
        return 1
    print("\nSchemas updated. Review schemas/README.md and re-run the validation tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
