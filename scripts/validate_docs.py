#!/usr/bin/env python3
"""Validate the NaaB Tech organization default files.

The checks read only files inside this repository. Nothing is downloaded and no
external URL is fetched, so validation does not depend on the availability of
any third-party service. (The CI job that runs this script still needs access
to the Python and npm package registries to install its tooling.)

Three severities are reported:

- **error** - a problem that must be fixed. Any error makes the run fail.
- **warning** - something worth a maintainer's attention that does not
  necessarily block a change. Warnings are reported but do not fail the run.
- **info** - contextual output, such as the summary of what was checked.

Usage:
    python scripts/validate_docs.py [repository_root]

Exit code is 0 when no errors were found, 1 otherwise.
"""

import json
import os
import re
import sys
import urllib.parse

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required: pip install -r requirements-docs.txt\n")
    raise SystemExit(2)

try:
    from jsonschema import Draft7Validator
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover
    sys.stderr.write("jsonschema is required: pip install -r requirements-docs.txt\n")
    raise SystemExit(2)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Status codes returned by resolve_repository_path.
PATH_OK = "ok"
PATH_MISSING = "missing"
PATH_BROKEN_LINK = "broken link"
PATH_OUTSIDE = "outside the repository"
SCHEMA_DIR = os.path.join(ROOT, "schemas")

# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------


def schema_validator(schema):
    """Return the validator class for a schema's declared JSON Schema dialect.

    Falls back to Draft 7 when the schema does not declare a dialect.
    """
    try:
        return validator_for(schema)
    except Exception:  # noqa: BLE001 - an unknown dialect must not stop the run
        return Draft7Validator


def _broken_symlink_component(path):
    """True when a component of the path is a symbolic link whose target is missing."""
    current = os.path.dirname(path)
    while current:
        if os.path.islink(current) and not os.path.exists(current):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return False


def resolve_repository_path(root, relative):
    """Resolve a repository-relative path safely.

    The whole candidate path is canonicalized, so a symbolic link in *any*
    parent component is resolved as well. A path whose canonical destination
    lies outside the canonical repository root is rejected, and is never
    opened or enumerated.

    Returns (status, resolved_path). The status is one of PATH_OK,
    PATH_MISSING, PATH_BROKEN_LINK or PATH_OUTSIDE. ``resolved_path`` is
    only meaningful when the status is PATH_OK.
    """
    if relative is None:
        return PATH_MISSING, None
    try:
        canonical_root = os.path.realpath(root)
        candidate = os.path.join(canonical_root, relative.replace("/", os.sep))
        resolved = os.path.realpath(candidate)
    except (OSError, ValueError):
        return PATH_MISSING, None
    if not _is_within(canonical_root, resolved):
        return PATH_OUTSIDE, None
    if not os.path.lexists(candidate):
        if _broken_symlink_component(candidate):
            return PATH_BROKEN_LINK, None
        return PATH_MISSING, None
    return PATH_OK, resolved


def load_schema(root, relative):
    """Load a vendored schema and verify that it is a valid JSON Schema.

    The schema path is resolved through the repository containment check
    first, so a schema whose file, or whose parent directory, is a symbolic
    link pointing outside the repository is never read.

    Parsing a JSON document successfully does not mean the document is a
    valid schema, so the schema is also checked against its own declared
    meta-schema.
    """
    status, resolved = resolve_repository_path(root, relative)
    if status == PATH_MISSING:
        raise SystemExit(
            f"missing schema {relative} in {root}. "
            "Run scripts/update_schemas.py to vendor it."
        )
    if status != PATH_OK:
        raise SystemExit(f"schema {relative} cannot be used: it is {status}")
    with open(resolved, encoding="utf-8") as handle:
        schema = json.load(handle)
    try:
        schema_validator(schema).check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"{relative} is not a valid JSON Schema: {exc}")
    return schema


def load_schemas(root):
    """Load the vendored schemas that belong to a repository root.

    The schemas are read from the repository being validated, not from the
    directory this script happens to live in, so that validating a different
    checkout uses that checkout's schemas.
    """
    return {
        "issue_form": load_schema(root, "schemas/github-issue-forms.json"),
        "vulnerability_form": load_schema(root, "schemas/github-vulnerability-report-form.json"),
        "issue_config": load_schema(root, "schemas/github-issue-config.json"),
    }



# --------------------------------------------------------------------------
# Expectations
# --------------------------------------------------------------------------

# Files that must exist, and the GitHub-recognized role each one plays.
REQUIRED_FILES = {
    "README.md": "repository readme",
    "profile/README.md": "organization profile readme",
    "CONTRIBUTING.md": "contribution guidelines",
    "CODE_OF_CONDUCT.md": "code of conduct",
    "SECURITY.md": "security policy",
    "SUPPORT.md": "support guidance",
    "PULL_REQUEST_TEMPLATE.md": "pull request template",
    "REPOSITORY_ONBOARDING.md": "repository onboarding checklist",
    ".github/ISSUE_TEMPLATE/bug_report.yml": "issue form: bug report",
    ".github/ISSUE_TEMPLATE/feature_request.yml": "issue form: feature request",
    ".github/ISSUE_TEMPLATE/question.yml": "issue form: question",
    ".github/ISSUE_TEMPLATE/config.yml": "issue template chooser",
    ".github/VULNERABILITY_REPORT.yml": "vulnerability report form",
}

# Tooling this repository needs for its own validation to be reproducible.
# These are not organization defaults; they are required for the checks in
# this script and in the CI workflow to run at all.
REQUIRED_TOOLING_FILES = {
    ".gitattributes": "line-ending normalization",
    ".gitignore": "ignored build artifacts",
    ".markdownlint.json": "markdownlint configuration",
    ".markdownlintignore": "markdownlint exclusions",
    ".yamllint.yml": "yamllint configuration",
    "package.json": "Node tooling declaration",
    "package-lock.json": "pinned Node dependency tree",
    "requirements-docs.txt": "pinned Python tooling",
    "schemas/github-issue-forms.json": "vendored issue form schema",
    "schemas/github-issue-config.json": "vendored chooser schema",
    "schemas/github-vulnerability-report-form.json": "derived vulnerability form schema",
    "schemas/PROVENANCE.json": "schema provenance record",
    "schemas/third-party/LICENSE-Apache-2.0.txt": "Apache-2.0 license text for the vendored schemas",
    "schemas/third-party/NOTICE-SchemaStore.txt": "upstream NOTICE attribution for the vendored schemas",
    "scripts/validate_docs.py": "documentation validator",
    "scripts/test_validate_docs.py": "validator tests",
    "scripts/update_schemas.py": "schema refresh tool",
}

# The GitHub form files. Only these are checked for keys that YAML parses as
# booleans: a workflow's `on:` key is parsed the same way but is legitimate.
FORM_FILES = (
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/question.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/VULNERABILITY_REPORT.yml",
)

# Labels the default issue forms apply. They must also exist in every
# repository that uses the forms -- see REPOSITORY_ONBOARDING.md.
EXPECTED_LABELS = {"bug", "enhancement", "question"}

# Key names that YAML 1.1 readers parse as booleans. GitHub rejects these as
# form keys, either as a boolean or as the corresponding string.
BOOLEAN_KEY_NAMES = {
    "y", "Y", "yes", "Yes", "YES", "n", "N", "no", "No", "NO",
    "true", "True", "TRUE", "false", "False", "FALSE",
    "on", "On", "ON", "off", "Off", "OFF",
}

# Option values that YAML 1.1 readers parse as booleans.
BOOLEAN_LIKE = {"y", "n", "yes", "no", "true", "false", "on", "off"}

ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# Inline Markdown links: [text](target) where the target may be wrapped in
# angle brackets, and may be followed by a title.
INLINE_LINK_PATTERN = re.compile(
    r"(?<!!)\[(?:[^\]\\]|\\.)*\]\(\s*(<[^>]*>|[^)\s]*)(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)

# Reference-style link definitions: [label]: target
REFERENCE_LINK_PATTERN = re.compile(
    r"^[ \t]{0,3}\[(?:[^\]\\]|\\.)+\]:[ \t]*(<[^>]*>|\S+)", re.MULTILINE
)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


class UniqueKeyLoader(yaml.SafeLoader):
    """A SafeLoader that rejects duplicate mapping keys.

    PyYAML silently keeps the last value for a duplicated key, which hides a
    real authoring mistake. This is still a safe loader: no YAML tags are
    constructed beyond the standard safe set.
    """


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError:
            # An unhashable key cannot be stored in a mapping. PyYAML raises a
            # bare TypeError for this; it is turned into a normal YAML error
            # so that the validator reports the problem instead of crashing.
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found unhashable key of type {type(key).__name__}",
                key_node.start_mark,
            )
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def parse_yaml_text(text):
    """Parse YAML text. Returns (data, error_message). error_message is None on success."""
    try:
        return yaml.load(text, Loader=UniqueKeyLoader), None
    except yaml.YAMLError as exc:
        return None, "YAML parse error: " + str(exc).replace("\n", " ")


def schema_errors(name, data, schema):
    """Validate a document against a JSON Schema. Returns a list of error strings."""
    validator = schema_validator(schema)(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        location = "/".join(str(part) for part in error.absolute_path) or "<document>"
        errors.append(f"{name}: schema: {location}: {error.message}")
    return errors


def boolean_key_errors(name, data):
    """Report keys that YAML parses as booleans.

    GitHub's form parser rejects them. PyYAML turns an unquoted `yes:` or
    `on:` into a Python boolean, so the check has to look at the key's type
    as well as its name.
    """
    errors = []

    def walk(node, trail):
        if isinstance(node, dict):
            for key in node.keys():
                if isinstance(key, bool) or (isinstance(key, str) and key in BOOLEAN_KEY_NAMES):
                    errors.append(
                        f"{trail}.{key!r}: key is parsed as a boolean by YAML and is rejected by GitHub"
                    )
                walk(node[key], f"{trail}.{key!r}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{trail}[{index}]")

    walk(data, name)
    return errors


def form_rule_errors(name, data, expected_labels=None):
    """Organization-specific form rules that a JSON Schema cannot express.

    Every value is type-checked before it is used. A malformed but parseable
    document must produce a list of errors, never a traceback.
    """
    errors = []
    if not isinstance(data, dict):
        return [f"{name}: the document must be a mapping"]

    labels = data.get("labels")
    if labels is not None and expected_labels is not None:
        if not isinstance(labels, list):
            errors.append(f"{name}: 'labels' must be a list")
        else:
            for index, label in enumerate(labels):
                if not isinstance(label, str):
                    errors.append(
                        f"{name}: labels[{index}]: must be a string, got {type(label).__name__}"
                    )
                elif label not in expected_labels:
                    errors.append(
                        f"{name}: label '{label}' is not one of the labels declared for the "
                        f"organization forms ({sorted(expected_labels)}). It must exist in every "
                        "repository that uses the form."
                    )

    name_value = data.get("name")
    if isinstance(name_value, str) and len(name_value) < 4:
        errors.append(f"{name}: 'name' must be more than 3 characters")

    body = data.get("body")
    if not isinstance(body, list):
        return errors

    ids, field_labels, inputs = [], [], 0
    for index, item in enumerate(body):
        where = f"{name}: body[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        item_type = item.get("type")
        attributes = item.get("attributes")
        if not isinstance(attributes, dict):
            attributes = {}

        if item_type != "markdown":
            inputs += 1
            label = attributes.get("label")
            if isinstance(label, str) and label.strip():
                field_labels.append(label.strip())

        if "id" in item:
            item_id = item["id"]
            if not isinstance(item_id, str):
                errors.append(
                    f"{where}: id must be a string, got {type(item_id).__name__}"
                )
            else:
                if not ID_PATTERN.match(item_id):
                    errors.append(
                        f"{where}: id '{item_id}' may only contain letters, numbers, '-' and '_'"
                    )
                # Only valid, hashable identifiers take part in duplicate detection.
                ids.append(item_id)

        if item_type == "markdown" and "id" in item:
            errors.append(f"{where}: a markdown element must not declare an id")
        if item_type == "checkboxes" and "validations" in item:
            errors.append(f"{where}: a checkboxes element does not accept a 'validations' block")

        if item_type in ("dropdown", "checkboxes"):
            options = attributes.get("options")
            if isinstance(options, list):
                texts = []
                for option in options:
                    if isinstance(option, str):
                        texts.append(option)
                    elif isinstance(option, dict):
                        label = option.get("label")
                        texts.append(label if isinstance(label, str) else str(label))
                    else:
                        # A bare scalar here is already a YAML type error, and a
                        # boolean is the case worth reporting explicitly.
                        texts.append(str(option))
                if len(set(texts)) != len(texts):
                    errors.append(f"{where}: option labels are not unique")
                for text in texts:
                    lowered = text.strip().lower()
                    if lowered == "none":
                        errors.append(f"{where}: options must not include the reserved word 'none'")
                    if lowered in BOOLEAN_LIKE:
                        errors.append(f"{where}: option '{text}' is parsed as a boolean by YAML; quote it")

    if len(set(ids)) != len(ids):
        errors.append(f"{name}: body ids are not unique: {ids}")
    if len(set(field_labels)) != len(field_labels):
        errors.append(f"{name}: body labels are not unique: {field_labels}")
    if inputs == 0:
        errors.append(f"{name}: body must contain at least one field that accepts input")
    return errors


def validate_form_document(name, data, schema, expected_labels=None):
    """Validate one issue form or vulnerability report form. Returns error strings."""
    errors = schema_errors(name, data, schema)
    errors.extend(boolean_key_errors(name, data))
    errors.extend(form_rule_errors(name, data, expected_labels))
    return errors


def validate_config_document(name, data, schema):
    """Validate the issue template chooser configuration. Returns error strings.

    The schema is passed in explicitly so that the configuration is always
    checked against the schema that belongs to the repository being validated.
    """
    errors = schema_errors(name, data, schema)
    errors.extend(boolean_key_errors(name, data))
    if isinstance(data, dict):
        links = data.get("contact_links")
        if isinstance(links, list):
            for index, link in enumerate(links):
                if not isinstance(link, dict):
                    errors.append(f"{name}: contact_links[{index}]: must be a mapping")
                    continue
                url = link.get("url")
                if isinstance(url, str) and not re.match(r"^https?://", url):
                    errors.append(
                        f"{name}: contact_links[{index}]: url must start with http:// or https:// "
                        f"(got '{url}')"
                    )
                about = link.get("about")
                if isinstance(about, str) and len(about) > 1024:
                    errors.append(f"{name}: contact_links[{index}]: 'about' must be 1024 characters or fewer")
    return errors


def guarded(label, function, *args):
    """Run a validation function, turning an unexpected failure into an error.

    A malformed document must produce a readable validation error rather than
    an unhandled traceback.
    """
    try:
        return function(*args)
    except Exception as exc:  # noqa: BLE001
        return [f"{label}: internal validation error: {type(exc).__name__}: {exc}"]


# --------------------------------------------------------------------------
# Repository-wide checks
# --------------------------------------------------------------------------


def strip_code_blocks(text):
    """Remove fenced code blocks so their contents are not parsed as Markdown.

    Without this, a link or heading inside an example block would be
    validated as if it were real content.
    """
    kept = []
    fence = None
    for line in text.split("\n"):
        stripped = line.strip()
        if fence is None:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence = stripped[:3]
                continue
            kept.append(line)
        elif stripped.startswith(fence):
            fence = None
    return "\n".join(kept)


def slugify(text):
    """Turn heading text into a GitHub-style anchor slug."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "-", text)


def headings(path):
    """Return the set of anchors a Markdown file defines.

    GitHub gives a repeated heading a numeric suffix, so the second '## Usage'
    becomes '#usage-1'. The same rule is applied here so that a link to
    either occurrence is accepted.
    """
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    anchors = set()
    counts = {}
    for line in strip_code_blocks(text).split("\n"):
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            base = slugify(match.group(2))
            if not base:
                continue
            seen = counts.get(base, 0)
            counts[base] = seen + 1
            anchors.add(base if seen == 0 else f"{base}-{seen}")
    return anchors


# Directories that are never part of the validated content.
EXCLUDED_DIRECTORIES = {".git", "node_modules", "__pycache__"}

# Working directories used by scripts/update_schemas.py: the staging area and
# the per-transaction backup directories.
EXCLUDED_DIRECTORY_PREFIXES = (".staging-", ".naabtech-")


def repo_files(root, suffixes):
    """Enumerate files for validation, rejecting anything outside the repository.

    A symbolic link whose canonical destination is outside the repository is
    never opened and never enters the inventory. Symlinked directories are
    followed only when they resolve inside the repository, and the files they
    contain are reported under the path as written, so that a link through
    the alias resolves. A cycle is detected by the chain of real directories
    currently being walked, so a link back to an ancestor is not followed.

    Returns (files, rejected). ``files`` holds (path, repository-relative
    name) pairs; ``rejected`` holds (repository-relative path, reason) for
    everything that was skipped.
    """
    found = []
    rejected = []

    def walk(directory, chain, display):
        real_dir = os.path.realpath(directory)
        if real_dir in chain:
            # A link back to a directory already being walked.
            return
        chain = chain | {real_dir}
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            return
        for name in entries:
            shown = os.path.join(display, name)
            relative = shown.replace(os.sep, "/")
            # Every candidate goes through the containment check, so a
            # symbolic link in any parent component is caught as well.
            status, resolved = resolve_repository_path(root, relative)
            if status == PATH_OUTSIDE:
                rejected.append((relative, "points outside the repository"))
                continue
            if status == PATH_BROKEN_LINK:
                rejected.append((relative, "points to a target that does not exist"))
                continue
            if status == PATH_MISSING:
                continue
            if os.path.isdir(resolved):
                if (name in EXCLUDED_DIRECTORIES
                        or name.startswith(EXCLUDED_DIRECTORY_PREFIXES)):
                    continue
                walk(resolved, chain, shown)
                continue
            if name.endswith(suffixes):
                found.append((resolved, relative))

    walk(root, frozenset(), "")
    return sorted(found, key=lambda item: item[1]), sorted(set(rejected))


def required_file_status(root, relative):
    """Return (ok, reason) for a required file.

    The whole path is canonicalized, so a required file whose parent
    directory is a symbolic link pointing outside the repository is reported
    as unusable and is never opened.
    """
    status, _resolved = resolve_repository_path(root, relative)
    if status == PATH_OK:
        return True, ""
    if status == PATH_MISSING:
        return False, "is missing"
    if status == PATH_BROKEN_LINK:
        return False, "is a symbolic link whose target does not exist"
    return False, "is a symbolic link pointing outside the repository"


def extract_link_targets(text):
    """Return the link targets in a Markdown document.

    Both inline links and reference-style link definitions are collected.
    Fenced code blocks are excluded.
    """
    body = strip_code_blocks(text)
    targets = []
    for match in INLINE_LINK_PATTERN.finditer(body):
        targets.append(match.group(1))
    for match in REFERENCE_LINK_PATTERN.finditer(body):
        targets.append(match.group(1))
    return targets


def split_link_target(target):
    """Split a Markdown link target into (path, anchor, query).

    Returns (None, None, None) for a target that points somewhere other than
    a file in this repository.
    """
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if not target or target.startswith("#"):
        return "", target[1:] if target.startswith("#") else None, None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
        # An absolute URL with a scheme, including mailto:.
        return None, None, None
    path, _, fragment = target.partition("#")
    path, _, query = path.partition("?")
    if not path:
        return "", fragment or None, query or None
    return urllib.parse.unquote(path), fragment or None, query or None


def _is_within(root, path):
    """True when path is the root itself or sits underneath it."""
    try:
        return os.path.commonpath([root, path]) == root
    except ValueError:
        # Different drives on Windows, or a mix of absolute and relative paths.
        return False


def resolve_within(root, relative):
    """Resolve a repository-relative path and confirm it stays inside root.

    The root and the candidate are canonicalized, so a symbolic link inside
    the repository that points outside it is rejected rather than followed.

    Returns the absolute path, or None when the target escapes the repository.
    """
    if relative is None:
        return None
    try:
        canonical_root = os.path.realpath(root)
        candidate = os.path.join(canonical_root, relative.replace("/", os.sep))
        # Reject an obviously outside path before touching the filesystem.
        if not _is_within(canonical_root, os.path.normpath(candidate)):
            return None
        canonical = os.path.realpath(candidate)
    except (OSError, ValueError):
        return None
    if not _is_within(canonical_root, canonical):
        return None
    return canonical


def run_checks(root):
    """Run every check. Returns (errors, warnings)."""
    errors = []
    warnings = []
    schemas = load_schemas(root)

    for name, purpose in REQUIRED_FILES.items():
        ok, reason = required_file_status(root, name)
        if not ok:
            if reason == "is missing":
                errors.append(f"missing required file: {name} ({purpose})")
            else:
                errors.append(f"required file: {name} ({purpose}) {reason}")

    for name, purpose in REQUIRED_TOOLING_FILES.items():
        ok, reason = required_file_status(root, name)
        if not ok:
            if reason == "is missing":
                errors.append(f"missing required tooling file: {name} ({purpose})")
            else:
                errors.append(f"required tooling file: {name} ({purpose}) {reason}")

    parsed = {}
    rejected = {}
    yaml_files, yaml_rejected = repo_files(root, (".yml", ".yaml"))
    for name, reason in yaml_rejected:
        rejected[name] = reason
    for path, name in yaml_files:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        data, error = parse_yaml_text(text)
        if error:
            errors.append(f"{name}: {error}")
            continue
        parsed[name] = data

    markdown_files = {}
    markdown_paths, markdown_rejected = repo_files(root, (".md",))
    for name, reason in markdown_rejected:
        rejected[name] = reason
    for path, name in markdown_paths:
        markdown_files[name] = path
    for name, reason in sorted(rejected.items()):
        errors.append(f"{name}: was not validated because the file {reason}")
    linked = set()

    validated_forms = set()

    template_status, template_dir = resolve_repository_path(root, ".github/ISSUE_TEMPLATE")
    if template_status == PATH_OUTSIDE:
        errors.append(
            ".github/ISSUE_TEMPLATE: was not listed because the directory is outside the repository"
        )
    elif template_status == PATH_BROKEN_LINK:
        errors.append(
            ".github/ISSUE_TEMPLATE: was not listed because the directory is a broken symbolic link"
        )
    elif template_status == PATH_OK and os.path.isdir(template_dir):
        form_names = sorted(
            name for name in os.listdir(template_dir)
            if name.endswith((".yml", ".yaml")) and name != "config.yml"
        )
        for filename in form_names:
            name = f".github/ISSUE_TEMPLATE/{filename}"
            if name not in parsed:
                errors.append(f"{name}: could not be parsed, so it was not validated")
                continue
            validated_forms.add(name)
            if name not in FORM_FILES:
                warnings.append(
                    f"{name}: is not listed in FORM_FILES in scripts/validate_docs.py, "
                    "so it is validated as an issue form by default"
                )
            errors.extend(
                guarded(
                    name,
                    validate_form_document,
                    name,
                    parsed[name],
                    schemas["issue_form"],
                    EXPECTED_LABELS,
                )
            )

    vuln_name = ".github/VULNERABILITY_REPORT.yml"
    if vuln_name in parsed:
        validated_forms.add(vuln_name)
        errors.extend(
            guarded(
                vuln_name,
                validate_form_document,
                vuln_name,
                parsed[vuln_name],
                schemas["vulnerability_form"],
            )
        )

    config_name = ".github/ISSUE_TEMPLATE/config.yml"
    if config_name in parsed:
        validated_forms.add(config_name)
        errors.extend(
            guarded(
                config_name,
                validate_config_document,
                config_name,
                parsed[config_name],
                schemas["issue_config"],
            )
        )

    for name in FORM_FILES:
        if name not in validated_forms:
            errors.append(f"{name}: declared as a form file but was not validated")

    # Labels that are declared for the organization forms but are not used by
    # any of them are dead weight and usually mean the set has drifted.
    used_labels = set()
    for name in FORM_FILES:
        data = parsed.get(name)
        if isinstance(data, dict) and isinstance(data.get("labels"), list):
            used_labels.update(label for label in data["labels"] if isinstance(label, str))
    for label in sorted(EXPECTED_LABELS - used_labels):
        warnings.append(
            f"label '{label}' is declared for the organization forms but no form applies it"
        )

    linked = set()
    for name, path in markdown_files.items():
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for raw_target in extract_link_targets(text):
            relative, anchor, _query = split_link_target(raw_target)
            if relative is None:
                continue
            if relative:
                target = os.path.normpath(
                    os.path.join(os.path.dirname(name), relative)
                ).replace(os.sep, "/")
                linked.add(target)
            else:
                target = name
            resolved = resolve_within(root, target)
            if resolved is None:
                errors.append(
                    f"{name}: link '{raw_target}' resolves outside the repository and was rejected"
                )
                continue
            if not os.path.exists(resolved):
                errors.append(f"{name}: link '{raw_target}' points to '{target}', which does not exist")
                continue
            if anchor:
                if target not in markdown_files:
                    errors.append(f"{name}: link '{raw_target}' has an anchor but '{target}' is not a Markdown file")
                elif anchor not in headings(markdown_files[target]):
                    errors.append(f"{name}: link '{raw_target}' points to an anchor that does not exist in '{target}'")

    # Markdown that nothing links to is hard to find. The organization profile
    # README is linked from the repository root, so only documents below the
    # root are reported.
    for name in sorted(markdown_files):
        if name == "README.md" or name in linked:
            continue
        warnings.append(f"{name}: no Markdown file links to it, so it is hard to discover")

    return errors, warnings


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ROOT)
    errors, warnings = run_checks(root)
    print(f"validate_docs: {root}")
    for message in warnings:
        print(f"  warning: {message}")
    if errors:
        for message in errors:
            print(f"  error: {message}")
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"  no errors ({len(warnings)} warning(s))")
    return 0


# The default repository's schemas, for direct use by the test suite. They are
# loaded after every function is defined, because the containment helpers
# they rely on are declared further down the module.
# The default repository's schemas, for direct use by the test suite.
ISSUE_FORM_SCHEMA = load_schema(ROOT, "schemas/github-issue-forms.json")
VULNERABILITY_FORM_SCHEMA = load_schema(ROOT, "schemas/github-vulnerability-report-form.json")
ISSUE_CONFIG_SCHEMA = load_schema(ROOT, "schemas/github-issue-config.json")


if __name__ == "__main__":
    raise SystemExit(main())
