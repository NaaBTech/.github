#!/usr/bin/env python3
"""Validate the NaaB Tech organization default files.

The checks read only files inside this repository. Nothing is downloaded and no
external URL is fetched, so validation does not depend on the availability of
any third-party service. (The CI job that runs this script still needs access
to the Python and npm package registries to install its tooling.)

Usage:
    python scripts/validate_docs.py [repository_root]

Exit code is 0 when every check passes, 1 otherwise.
"""

import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required: pip install -r requirements-docs.txt\n")
    raise SystemExit(2)

try:
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover
    sys.stderr.write("jsonschema is required: pip install -r requirements-docs.txt\n")
    raise SystemExit(2)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "schemas")

# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

def load_schema(name):
    path = os.path.join(SCHEMA_DIR, name)
    if not os.path.exists(path):
        raise SystemExit(f"missing schema {name}. Run scripts/update_schemas.py to vendor it.")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


ISSUE_FORM_SCHEMA = load_schema("github-issue-forms.json")
VULNERABILITY_FORM_SCHEMA = load_schema("github-vulnerability-report-form.json")
ISSUE_CONFIG_SCHEMA = load_schema("github-issue-config.json")

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

# Labels the default issue forms apply. They must also exist in every
# repository that uses the forms -- see REPOSITORY_ONBOARDING.md.
EXPECTED_LABELS = {"bug", "enhancement", "question"}

# Keys YAML parses as booleans, which GitHub rejects as form keys.
FORBIDDEN_KEYS = {
    "y", "Y", "yes", "Yes", "YES", "n", "N", "no", "No", "NO",
    "true", "True", "TRUE", "false", "False", "FALSE",
    "on", "On", "ON", "off", "Off", "OFF",
}

ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BOOLEAN_LIKE = {"y", "n", "yes", "no", "true", "false", "on", "off"}

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def parse_yaml_text(text):
    """Parse YAML text. Returns (data, error_message). error_message is None on success."""
    try:
        return yaml.safe_load(text), None
    except yaml.YAMLError as exc:
        return None, "YAML parse error: " + str(exc).replace("\n", " ")


def schema_errors(name, data, schema):
    """Validate a document against a JSON Schema. Returns a list of error strings."""
    validator = Draft7Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        location = "/".join(str(part) for part in error.absolute_path) or "<document>"
        errors.append(f"{name}: schema: {location}: {error.message}")
    return errors


def form_rule_errors(name, data, expected_labels=None):
    """Organization-specific form rules that a JSON Schema cannot express."""
    errors = []
    if not isinstance(data, dict):
        return [f"{name}: the document must be a mapping"]

    labels = data.get("labels")
    if labels is not None and expected_labels is not None:
        if not isinstance(labels, list):
            errors.append(f"{name}: 'labels' must be a list")
        else:
            for label in labels:
                if label not in expected_labels:
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
            if not isinstance(item_id, str) or not ID_PATTERN.match(item_id):
                errors.append(f"{where}: id '{item_id}' may only contain letters, numbers, '-' and '_'")
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
                        texts.append(str(option.get("label", "")))
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
    errors.extend(form_rule_errors(name, data, expected_labels))
    return errors


def validate_config_document(name, data):
    """Validate the issue template chooser configuration. Returns error strings."""
    errors = schema_errors(name, data, ISSUE_CONFIG_SCHEMA)
    if isinstance(data, dict):
        links = data.get("contact_links")
        if isinstance(links, list):
            for index, link in enumerate(links):
                if not isinstance(link, dict):
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


def walk_forbidden_keys(node, trail, found):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN_KEYS:
                found.append(f"{trail}.{key}")
            walk_forbidden_keys(value, f"{trail}.{key}", found)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            walk_forbidden_keys(value, f"{trail}[{index}]", found)


# --------------------------------------------------------------------------
# Repository-wide checks
# --------------------------------------------------------------------------


def headings(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    anchors = set()
    for line in text.split("\n"):
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            anchor = match.group(2).strip().lower()
            anchor = re.sub(r"[^\w\s-]", "", anchor)
            anchors.add(re.sub(r"\s+", "-", anchor))
    return anchors


def repo_files(root, suffixes):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
        for name in filenames:
            if name.endswith(suffixes):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def run_checks(root):
    """Run every check. Returns a list of error strings."""
    errors = []

    for name, purpose in REQUIRED_FILES.items():
        if not os.path.exists(os.path.join(root, name.replace("/", os.sep))):
            errors.append(f"missing required file: {name} ({purpose})")

    parsed = {}
    for path in repo_files(root, (".yml", ".yaml")):
        name = os.path.relpath(path, root).replace(os.sep, "/")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        data, error = parse_yaml_text(text)
        if error:
            errors.append(f"{name}: {error}")
            continue
        parsed[name] = data
        found = []
        walk_forbidden_keys(data, name, found)
        for item in found:
            errors.append(f"{item}: key is parsed as a boolean by YAML and is rejected by GitHub")

    issue_template_dir = os.path.join(root, ".github", "ISSUE_TEMPLATE")
    if os.path.isdir(issue_template_dir):
        form_names = sorted(
            name for name in os.listdir(issue_template_dir)
            if name.endswith((".yml", ".yaml")) and name != "config.yml"
        )
        for filename in form_names:
            name = f".github/ISSUE_TEMPLATE/{filename}"
            if name not in parsed:
                errors.append(f"{name}: could not be parsed, so it was not validated")
                continue
            errors.extend(validate_form_document(name, parsed[name], ISSUE_FORM_SCHEMA, EXPECTED_LABELS))

    vuln_name = ".github/VULNERABILITY_REPORT.yml"
    if vuln_name in parsed:
        errors.extend(validate_form_document(vuln_name, parsed[vuln_name], VULNERABILITY_FORM_SCHEMA))

    config_name = ".github/ISSUE_TEMPLATE/config.yml"
    if config_name in parsed:
        errors.extend(validate_config_document(config_name, parsed[config_name]))

    markdown_files = {
        os.path.relpath(path, root).replace(os.sep, "/"): path
        for path in repo_files(root, (".md",))
    }
    for name, path in markdown_files.items():
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for _, url in LINK_PATTERN.findall(text):
            if url.startswith(("http://", "https://", "mailto:")):
                continue
            if url.startswith("#"):
                target, anchor = name, url[1:]
            else:
                target = os.path.normpath(
                    os.path.join(os.path.dirname(name), url.split("#")[0])
                ).replace(os.sep, "/")
                anchor = url.split("#")[1] if "#" in url else None
            if not os.path.exists(os.path.join(root, target.replace("/", os.sep))):
                errors.append(f"{name}: link '{url}' points to '{target}', which does not exist")
                continue
            if anchor:
                if target not in markdown_files:
                    errors.append(f"{name}: link '{url}' has an anchor but '{target}' is not a Markdown file")
                elif anchor not in headings(markdown_files[target]):
                    errors.append(f"{name}: link '{url}' points to an anchor that does not exist in '{target}'")

    return errors


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ROOT)
    errors = run_checks(root)
    print(f"validate_docs: {root}")
    if errors:
        for message in errors:
            print(f"  error: {message}")
        print(f"\n{len(errors)} error(s)")
        return 1
    print("  all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
