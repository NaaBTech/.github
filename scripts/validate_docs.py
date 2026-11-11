#!/usr/bin/env python3
"""Validate the NaaB Tech organization default files.

All checks are offline. Nothing here depends on a third-party service being
reachable, so a temporary outage elsewhere cannot fail a documentation change.

Usage:
    python scripts/validate_docs.py [repository_root]

Exit code is 0 when every check passes, 1 otherwise.
"""

import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required: pip install -r requirements-docs.txt\n")
    raise SystemExit(2)

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")

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

# Top-level keys GitHub accepts in an issue form.
FORM_TOP_LEVEL_KEYS = {
    "name", "description", "title", "labels", "projects", "assignees", "type", "body",
}

# Element types GitHub supports in an issue form.
ISSUE_FORM_TYPES = {"markdown", "textarea", "input", "dropdown", "checkboxes", "upload"}

# Element types GitHub supports in a private vulnerability reporting form.
# https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository
VULNERABILITY_FORM_TYPES = {"markdown", "textarea", "input", "dropdown", "checkboxes"}

# Top-level keys GitHub accepts in a vulnerability reporting form.
VULNERABILITY_TOP_LEVEL_KEYS = {"name", "description", "body"}

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

errors = []
warnings = []


def fail(message):
    errors.append(message)


def warn(message):
    warnings.append(message)


def repo_files(suffixes):
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
        for name in filenames:
            if name.endswith(suffixes):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


# --------------------------------------------------------------------------
# 1. Required files
# --------------------------------------------------------------------------

for name, purpose in REQUIRED_FILES.items():
    if not os.path.exists(os.path.join(ROOT, name.replace("/", os.sep))):
        fail(f"missing required file: {name} ({purpose})")

# --------------------------------------------------------------------------
# 2. YAML parses
# --------------------------------------------------------------------------

parsed = {}
for path in repo_files((".yml", ".yaml")):
    name = rel(path)
    try:
        with open(path, encoding="utf-8") as handle:
            parsed[name] = yaml.safe_load(handle)
    except Exception as exc:  # noqa: BLE001
        fail(f"{name}: YAML parse error: {exc}")

# Reserved boolean keys anywhere in the YAML.
def walk_keys(node, trail, found):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN_KEYS:
                found.append(f"{trail}.{key}")
            walk_keys(value, f"{trail}.{key}", found)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            walk_keys(value, f"{trail}[{index}]", found)


for name, data in parsed.items():
    found = []
    walk_keys(data, name, found)
    for item in found:
        fail(f"{item}: key is parsed as a boolean by YAML and is rejected by GitHub")

# --------------------------------------------------------------------------
# 3. Forms
# --------------------------------------------------------------------------

def check_form(name, data, allowed_types, allowed_top_level, label_set=None):
    if not isinstance(data, dict):
        fail(f"{name}: top level must be a mapping")
        return

    for key in data:
        if key not in allowed_top_level:
            fail(f"{name}: '{key}' is not a permitted top-level key")

    for key in ("name", "description"):
        if key not in data:
            fail(f"{name}: missing required top-level key '{key}'")
        elif not isinstance(data[key], str) or not data[key].strip():
            fail(f"{name}: '{key}' must be a non-empty string")

    if "body" not in data:
        fail(f"{name}: missing required top-level key 'body'")
        return
    body = data["body"]
    if not isinstance(body, list) or not body:
        fail(f"{name}: 'body' must be a non-empty list")
        return

    labels = data.get("labels")
    if labels is not None:
        if not isinstance(labels, list) or not all(isinstance(x, str) for x in labels):
            fail(f"{name}: 'labels' must be a list of strings")
        else:
            if label_set is not None:
                for label in labels:
                    if label not in label_set:
                        fail(
                            f"{name}: label '{label}' is not one of the labels declared for the "
                            f"organization forms ({sorted(label_set)}). It must exist in every "
                            "repository that uses the form."
                        )

    ids = []
    field_labels = []
    inputs = 0

    for index, item in enumerate(body):
        where = f"{name}: body[{index}]"
        if not isinstance(item, dict):
            fail(f"{where}: must be a mapping")
            continue

        item_type = item.get("type")
        if item_type not in allowed_types:
            fail(f"{where}: '{item_type}' is not a supported element type for this form")
            continue

        for key in item:
            if key not in ("type", "id", "attributes", "validations"):
                fail(f"{where}: '{key}' is not a permitted key")

        attributes = item.get("attributes")
        if not isinstance(attributes, dict):
            fail(f"{where}: 'attributes' must be a mapping")
            continue

        if item_type != "markdown":
            inputs += 1
            label = attributes.get("label")
            if not isinstance(label, str) or not label.strip():
                fail(f"{where}: 'label' is required for a '{item_type}' element")
            else:
                field_labels.append(label.strip())
        elif "value" not in attributes:
            fail(f"{where}: a markdown element requires a 'value'")

        if item_type == "markdown":
            if "id" in item:
                fail(f"{where}: a markdown element must not declare an id")
        else:
            if "id" in item:
                item_id = item["id"]
                if not isinstance(item_id, str) or not ID_PATTERN.match(item_id):
                    fail(f"{where}: id '{item_id}' may only contain letters, numbers, '-' and '_'")
                ids.append(item_id)

        if item_type == "checkboxes" and "validations" in item:
            fail(f"{where}: a checkboxes element does not accept a 'validations' block")

        if item_type in ("dropdown", "checkboxes"):
            options = attributes.get("options")
            if not isinstance(options, list) or not options:
                fail(f"{where}: a '{item_type}' element requires a non-empty 'options' list")
                continue
            texts = [o if isinstance(o, str) else o.get("label", "") for o in options]
            if len(set(texts)) != len(texts):
                fail(f"{where}: option labels are not unique")
            for text in texts:
                lowered = str(text).strip().lower()
                if lowered == "none":
                    fail(f"{where}: options must not include the reserved word 'none'")
                if lowered in FORBIDDEN_KEYS:
                    fail(f"{where}: option '{text}' is parsed as a boolean; quote it")

        validations = item.get("validations")
        if validations is not None:
            if not isinstance(validations, dict):
                fail(f"{where}: 'validations' must be a mapping")
            else:
                for key in validations:
                    if key not in ("required", "min_length", "accept"):
                        fail(f"{where}: '{key}' is not a permitted validation key")
                if "required" in validations and not isinstance(validations["required"], bool):
                    fail(f"{where}: 'required' must be a boolean")
                if "min_length" in validations and not isinstance(validations["min_length"], int):
                    fail(f"{where}: 'min_length' must be an integer")

    if len(set(ids)) != len(ids):
        fail(f"{name}: body ids are not unique: {ids}")
    if len(set(field_labels)) != len(field_labels):
        fail(f"{name}: body labels are not unique: {field_labels}")
    if inputs == 0:
        fail(f"{name}: body must contain at least one field that accepts input")


issue_form_dir = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE")
form_files = sorted(
    os.path.join(issue_form_dir, name)
    for name in os.listdir(issue_form_dir)
    if name.endswith((".yml", ".yaml")) and name != "config.yml"
) if os.path.isdir(issue_form_dir) else []

for path in form_files:
    name = rel(path)
    check_form(name, parsed.get(name), ISSUE_FORM_TYPES, FORM_TOP_LEVEL_KEYS, EXPECTED_LABELS)

vuln_path = ".github/VULNERABILITY_REPORT.yml"
if vuln_path in parsed:
    check_form(vuln_path, parsed[vuln_path], VULNERABILITY_FORM_TYPES, VULNERABILITY_TOP_LEVEL_KEYS)

# --------------------------------------------------------------------------
# 4. Issue template chooser configuration
# --------------------------------------------------------------------------

config_name = ".github/ISSUE_TEMPLATE/config.yml"
config = parsed.get(config_name)
if isinstance(config, dict):
    for key in config:
        if key not in ("blank_issues_enabled", "contact_links"):
            fail(f"{config_name}: '{key}' is not a permitted key")
    if "blank_issues_enabled" in config and not isinstance(config["blank_issues_enabled"], bool):
        fail(f"{config_name}: 'blank_issues_enabled' must be a boolean")
    links = config.get("contact_links")
    if links is not None:
        if not isinstance(links, list) or not links:
            fail(f"{config_name}: 'contact_links' must be a non-empty list")
        else:
            for index, link in enumerate(links):
                where = f"{config_name}: contact_links[{index}]"
                if not isinstance(link, dict):
                    fail(f"{where}: must be a mapping")
                    continue
                for key in ("name", "url", "about"):
                    if key not in link:
                        fail(f"{where}: missing required key '{key}'")
                    elif not isinstance(link[key], str) or not link[key].strip():
                        fail(f"{where}: '{key}' must be a non-empty string")
                url = link.get("url", "")
                if isinstance(url, str) and not re.match(r"^https?://", url):
                    fail(f"{where}: url must start with http:// or https:// (got '{url}')")

# --------------------------------------------------------------------------
# 5. Internal links and anchors
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


markdown_files = {rel(p): p for p in repo_files((".md",))}

for name, path in markdown_files.items():
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    for label, url in LINK_PATTERN.findall(text):
        if url.startswith(("http://", "https://", "mailto:")):
            continue
        if url.startswith("#"):
            target, anchor = name, url[1:]
        else:
            target = os.path.normpath(
                os.path.join(os.path.dirname(name), url.split("#")[0])
            ).replace(os.sep, "/")
            anchor = url.split("#")[1] if "#" in url else None
        if not os.path.exists(os.path.join(ROOT, target.replace("/", os.sep))):
            fail(f"{name}: link '{url}' points to '{target}', which does not exist")
            continue
        if anchor:
            if target not in markdown_files:
                fail(f"{name}: link '{url}' has an anchor but '{target}' is not a Markdown file")
            elif anchor not in headings(markdown_files[target]):
                fail(f"{name}: link '{url}' points to an anchor that does not exist in '{target}'")

# --------------------------------------------------------------------------
# 6. Report
# --------------------------------------------------------------------------

print(f"validate_docs: {ROOT}")
if warnings:
    for message in warnings:
        print(f"  warning: {message}")
if errors:
    for message in errors:
        print(f"  error: {message}")
    print(f"\n{len(errors)} error(s)")
    raise SystemExit(1)

print("  all checks passed")
raise SystemExit(0)
