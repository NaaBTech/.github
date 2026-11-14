#!/usr/bin/env python3
"""Negative and positive tests for the documentation validator.

The suite contains three kinds of case:

- **Negative cases** - intentionally invalid documents. The validator must
  report an error for each one, so that a regression which silently accepts a
  malformed form is caught.
- **Positive control cases** - valid documents. The validator must report no
  errors at all for these, so that the checks cannot become so strict that
  they reject a good form.
- **Behavior cases** - specific behaviors that were implemented in response
  to a confirmed defect: schema injection, path containment, and the Markdown
  link edge cases.

The expected error text is pinned for each negative case, so a change in the
validator that stops detecting a problem is visible.

Usage:
    python scripts/test_validate_docs.py
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCHEMA_SOURCE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas")
)

from validate_docs import (  # noqa: E402
    EXPECTED_LABELS,
    ISSUE_FORM_SCHEMA,
    ISSUE_CONFIG_SCHEMA,
    VULNERABILITY_FORM_SCHEMA,
    extract_link_targets,
    headings,
    load_schemas,
    parse_yaml_text,
    repo_files,
    required_file_status,
    resolve_within,
    run_checks,
    split_link_target,
    validate_config_document,
    validate_form_document,
)
import update_schemas  # noqa: E402

VALID_ISSUE_FORM = """
name: Valid form
description: A form that should pass every check.
title: "[Test]: "
labels:
  - bug
body:
  - type: markdown
    attributes:
      value: |
        Some introductory text.
  - type: input
    id: subject
    attributes:
      label: Subject
    validations:
      required: true
  - type: checkboxes
    id: confirm
    attributes:
      label: Confirm
      options:
        - label: I agree
          required: true
"""

VALID_VULNERABILITY_FORM = """
name: Valid report
description: A vulnerability report form that should pass every check.
body:
  - type: markdown
    attributes:
      value: |
        Thank you for reporting a vulnerability.
  - type: textarea
    id: summary
    attributes:
      label: Summary
    validations:
      required: true
  - type: input
    id: contact
    attributes:
      label: Contact details
"""

# A workflow's `on:` key is parsed as a boolean by YAML 1.1 readers and is
# perfectly legal there. The boolean-key rule must therefore not be applied to
# workflow files. This is the control for that scoping.
WORKFLOW_WITH_ON_KEY = """
name: Workflow
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""

# (case name, document kind, YAML text, expected substring in the error output)
FORM_CASES = [
    (
        "unsupported element type",
        "issue",
        """
name: Bad element type
description: Uses an element type GitHub does not support.
body:
  - type: slider
    id: volume
    attributes:
      label: Volume
""",
        "slider",
    ),
    (
        "unsupported attribute",
        "issue",
        """
name: Bad attribute
description: Uses an attribute GitHub does not support.
body:
  - type: input
    id: subject
    attributes:
      label: Subject
      bogus: value
""",
        "bogus",
    ),
    (
        "missing top-level body",
        "issue",
        """
name: Missing body
description: Has no body at all.
""",
        "body",
    ),
    (
        "missing required attributes",
        "issue",
        """
name: Missing attributes
description: An element without an attributes block.
body:
  - type: input
    id: subject
""",
        "attributes",
    ),
    (
        "duplicate field ids",
        "issue",
        """
name: Duplicate ids
description: Two fields share an id.
body:
  - type: input
    id: subject
    attributes:
      label: Subject
  - type: input
    id: subject
    attributes:
      label: Subject again
""",
        "body ids are not unique",
    ),
    (
        "duplicate field labels",
        "issue",
        """
name: Duplicate labels
description: Two fields share a label.
body:
  - type: input
    id: first
    attributes:
      label: Same label
  - type: input
    id: second
    attributes:
      label: Same label
""",
        "body labels are not unique",
    ),
    (
        "duplicate dropdown options",
        "issue",
        """
name: Duplicate options
description: A dropdown with the same option twice.
body:
  - type: dropdown
    id: choice
    attributes:
      label: Choice
      options:
        - One
        - One
""",
        "option labels are not unique",
    ),
    (
        "reserved option word",
        "issue",
        """
name: Reserved option
description: A dropdown that offers the reserved word none.
body:
  - type: dropdown
    id: choice
    attributes:
      label: Choice
      options:
        - One
        - none
""",
        "reserved word 'none'",
    ),
    (
        "boolean-like option",
        "issue",
        """
name: Boolean option
description: A dropdown option that YAML reads as a boolean.
body:
  - type: dropdown
    id: choice
    attributes:
      label: Choice
      options:
        - yes
""",
        "parsed as a boolean",
    ),
    (
        "checkboxes with validations",
        "issue",
        """
name: Checkbox validations
description: A checkboxes element with a validations block.
body:
  - type: checkboxes
    id: confirm
    attributes:
      label: Confirm
      options:
        - label: I agree
    validations:
      required: true
""",
        "does not accept a 'validations' block",
    ),
    (
        "markdown with an id",
        "issue",
        """
name: Markdown id
description: A markdown element that declares an id.
body:
  - type: markdown
    id: intro
    attributes:
      value: |
        Some text.
""",
        "must not declare an id",
    ),
    (
        "label outside the declared set",
        "issue",
        """
name: Unknown label
description: Applies a label that is not one of the organization labels.
labels:
  - triage
body:
  - type: input
    id: subject
    attributes:
      label: Subject
""",
        "is not one of the labels declared",
    ),
    (
        "body with no input field",
        "issue",
        """
name: No input
description: A body that only contains markdown.
body:
  - type: markdown
    attributes:
      value: |
        Nothing to fill in.
""",
        "at least one field that accepts input",
    ),
    (
        "vulnerability form with an upload element",
        "vulnerability",
        """
name: Bad report form
description: Uses an upload element, which GitHub does not support here.
body:
  - type: upload
    id: evidence
    attributes:
      label: Evidence
""",
        "upload",
    ),
    (
        "vulnerability form with a top-level label",
        "vulnerability",
        """
name: Bad report form
description: Applies a label, which vulnerability report forms do not support.
labels:
  - bug
body:
  - type: textarea
    id: summary
    attributes:
      label: Summary
""",
        "labels",
    ),
    (
        "vulnerability form missing a body",
        "vulnerability",
        """
name: Bad report form
description: Has no body at all.
""",
        "body",
    ),
    (
        "form document that is not a mapping",
        "issue",
        """
- one
- two
""",
        "mapping",
    ),
    (
        "key that YAML parses as a boolean",
        "issue",
        """
name: Boolean key
description: Has a key that YAML 1.1 readers parse as a boolean.
body:
  - type: input
    id: subject
    attributes:
      label: Subject
    yes: 1
""",
        "parsed as a boolean by YAML",
    ),
    (
        "quoted key that YAML would parse as a boolean",
        "issue",
        """
name: Quoted boolean key
description: Has a quoted key that YAML 1.1 readers parse as a boolean.
body:
  - type: input
    id: subject
    attributes:
      label: Subject
    "on": 1
""",
        "parsed as a boolean by YAML",
    ),
    (
        "id is a list",
        "issue",
        """
name: List id
description: Has an id that is a list.
body:
  - type: input
    id:
      - one
      - two
    attributes:
      label: Subject
""",
        "id must be a string",
    ),
    (
        "id is a mapping",
        "issue",
        """
name: Mapping id
description: Has an id that is a mapping.
body:
  - type: input
    id:
      key: value
    attributes:
      label: Subject
""",
        "id must be a string",
    ),
    (
        "labels contains a list",
        "issue",
        """
name: List label
description: Has a label entry that is a list.
labels:
  - - one
    - two
body:
  - type: input
    id: subject
    attributes:
      label: Subject
""",
        "must be a string",
    ),
    (
        "labels contains a mapping",
        "issue",
        """
name: Mapping label
description: Has a label entry that is a mapping.
labels:
  - key: value
body:
  - type: input
    id: subject
    attributes:
      label: Subject
""",
        "must be a string",
    ),
    (
        "body element has a null key",
        "issue",
        """
name: Null key
description: Has an element with an explicit null key.
body:
  - type: input
    ? null
    attributes:
      label: Subject
""",
        "schema",
    ),
    (
        "body is not a list",
        "issue",
        """
name: Bad body
description: The body is a string rather than a list.
body: not a list
""",
        "body",
    ),
    (
        "attributes is not a mapping",
        "issue",
        """
name: Bad attributes
description: An element whose attributes are a string.
body:
  - type: input
    id: subject
    attributes: not a mapping
""",
        "schema",
    ),
]

# (case name, YAML text, expected substring)
YAML_CASES = [
    (
        "malformed YAML",
        """
name: Broken
description: "an unterminated string
body:
  - type: input
""",
        "YAML parse error",
    ),
    (
        "duplicate YAML keys",
        """
name: First name
description: Has the same key twice.
name: Second name
body:
  - type: input
    id: subject
    attributes:
      label: Subject
""",
        "duplicate key",
    ),
    (
        "unhashable mapping key",
        """
name: Unhashable
description: Has a list as a mapping key.
? [a, b]
: value
""",
        "YAML parse error",
    ),
]

# (case name, YAML text, expected substring)
CONFIG_CASES = [
    (
        "contact link with a non-http url",
        """
blank_issues_enabled: false
contact_links:
  - name: Email us
    url: mailto:info@example.invalid
    about: Email.
""",
        "url",
    ),
    (
        "unknown top-level key",
        """
blank_issues_enabled: false
unknown_key: true
""",
        "unknown_key",
    ),
    (
        "contact link that is not a mapping",
        """
blank_issues_enabled: false
contact_links:
  - just a string
""",
        "must be a mapping",
    ),
]


def make_temp_repo(files=None, alternate_config_schema=None):
    """Create a temporary repository that the validator can run against."""
    temp_root = tempfile.mkdtemp()
    os.makedirs(os.path.join(temp_root, "schemas"))
    for schema_name in (
        "github-issue-forms.json",
        "github-vulnerability-report-form.json",
        "github-issue-config.json",
    ):
        shutil.copy(
            os.path.join(SCHEMA_SOURCE_DIR, schema_name),
            os.path.join(temp_root, "schemas", schema_name),
        )
    if alternate_config_schema is not None:
        with open(os.path.join(temp_root, "schemas", "github-issue-config.json"), "w", encoding="utf-8") as handle:
            json.dump(alternate_config_schema, handle)
    for relative, content in (files or {}).items():
        path = os.path.join(temp_root, relative.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
    return temp_root




def run():
    failures = []
    positive = 0
    negative = 0
    behavior = 0
    skipped = 0

    # ------------------------------------------------------------------
    # Positive control cases: valid documents must produce no errors.
    # ------------------------------------------------------------------
    for name, kind, text in (
        ("valid issue form", "issue", VALID_ISSUE_FORM),
        ("valid vulnerability form", "vulnerability", VALID_VULNERABILITY_FORM),
    ):
        positive += 1
        data, error = parse_yaml_text(text)
        if error:
            failures.append(f"{name}: the fixture itself did not parse: {error}")
            continue
        schema = ISSUE_FORM_SCHEMA if kind == "issue" else VULNERABILITY_FORM_SCHEMA
        errors = validate_form_document(name, data, schema, EXPECTED_LABELS)
        if errors:
            failures.append(f"{name}: expected no errors, got {errors}")

    # A workflow's `on:` key must never be reported as a boolean key. The rule
    # is scoped to the files listed in FORM_FILES, so a workflow is checked
    # through run_checks rather than through the rule in isolation.
    positive += 1
    data, error = parse_yaml_text(WORKFLOW_WITH_ON_KEY)
    if error:
        failures.append(f"workflow with an 'on:' key: the fixture itself did not parse: {error}")
    elif True not in data:
        failures.append("workflow with an 'on:' key: the fixture no longer exercises a boolean key")

    # ------------------------------------------------------------------
    # Negative cases.
    # ------------------------------------------------------------------
    for name, kind, text, expected in FORM_CASES:
        negative += 1
        data, error = parse_yaml_text(text)
        if error:
            failures.append(f"{name}: the fixture itself did not parse: {error}")
            continue
        schema = ISSUE_FORM_SCHEMA if kind == "issue" else VULNERABILITY_FORM_SCHEMA
        errors = validate_form_document(name, data, schema, EXPECTED_LABELS)
        if not errors:
            failures.append(f"{name}: expected an error, but the validator reported none")
        elif not any(expected.lower() in message.lower() for message in errors):
            failures.append(f"{name}: expected an error containing '{expected}', got {errors}")

    for name, text, expected in YAML_CASES:
        negative += 1
        data, error = parse_yaml_text(text)
        if error is None:
            failures.append(f"{name}: expected a YAML parse error, but the text parsed successfully")
        elif expected.lower() not in error.lower():
            failures.append(f"{name}: expected the error to mention '{expected}', got '{error}'")

    for name, text, expected in CONFIG_CASES:
        negative += 1
        data, error = parse_yaml_text(text)
        if error:
            failures.append(f"{name}: the fixture itself did not parse: {error}")
            continue
        errors = validate_config_document(name, data, ISSUE_CONFIG_SCHEMA)
        if not errors:
            failures.append(f"{name}: expected an error, but the validator reported none")
        elif not any(expected.lower() in message.lower() for message in errors):
            failures.append(f"{name}: expected an error containing '{expected}', got {errors}")

    # ------------------------------------------------------------------
    # Behavior case: the issue configuration schema is taken from the
    # repository being validated, not from a global constant.
    # ------------------------------------------------------------------
    behavior += 1
    alternate_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://example.invalid/alternate-issue-config.json",
        "title": "Alternate issue configuration schema used only by the test suite",
        "type": "object",
        "required": ["alternate_marker"],
        "properties": {"alternate_marker": {"type": "string"}},
    }
    temp_root = make_temp_repo(
        files={
            ".github/ISSUE_TEMPLATE/config.yml": "blank_issues_enabled: false\n",
        },
        alternate_config_schema=alternate_schema,
    )
    try:
        errors, _warnings = run_checks(temp_root)
        if not any("alternate_marker" in message for message in errors):
            failures.append(
                "issue configuration schema injection: expected the alternate schema to be "
                f"used, but no error mentioned 'alternate_marker'. Errors were {errors}"
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    errors, _warnings = run_checks(os.path.abspath(os.path.join(os.path.dirname(SCHEMA_SOURCE_DIR))))
    if any("alternate_marker" in message for message in errors):
        failures.append(
            "issue configuration schema injection: the real repository must not report the "
            "alternate schema's requirement"
        )

    # ------------------------------------------------------------------
    # Behavior cases: path containment.
    # ------------------------------------------------------------------
    repo_root = os.path.abspath(os.path.join(os.path.dirname(SCHEMA_SOURCE_DIR)))
    behavior += 1
    if resolve_within(repo_root, "CONTRIBUTING.md") is None:
        failures.append("path containment: a normal internal file was rejected")

    behavior += 1
    if resolve_within(repo_root, "../../../../Windows/win.ini") is not None:
        failures.append("path containment: a relative path escaping the root was accepted")

    behavior += 1
    outside = os.path.abspath(os.path.join(repo_root, "..", "..", "outside.txt"))
    if resolve_within(repo_root, outside) is not None:
        failures.append("path containment: an absolute path outside the root was accepted")

    behavior += 1
    if resolve_within(repo_root, "does-not-exist.md") is None:
        failures.append("path containment: a nonexistent internal target was rejected")

    symlink_supported = True
    symlink_reason = ""
    link_dir = None
    outside_dir = None
    try:
        link_dir = tempfile.mkdtemp()
        # The escaping target has to live outside the directory that is
        # treated as the repository root, otherwise the link is legitimate.
        outside_dir = tempfile.mkdtemp()
        outside_target = os.path.join(outside_dir, "outside.md")
        with open(outside_target, "w", encoding="utf-8") as handle:
            handle.write("# Outside\n")
        internal_target = os.path.join(link_dir, "internal.md")
        with open(internal_target, "w", encoding="utf-8") as handle:
            handle.write("# Internal\n")

        escaping_link = os.path.join(link_dir, "escape.md")
        os.symlink(outside_target, escaping_link)
        internal_link = os.path.join(link_dir, "inside.md")
        os.symlink(internal_target, internal_link)
    except (OSError, NotImplementedError, AttributeError) as exc:
        symlink_supported = False
        symlink_reason = f"{type(exc).__name__}: {exc}"
        if link_dir:
            shutil.rmtree(link_dir, ignore_errors=True)
            link_dir = None
        if outside_dir:
            shutil.rmtree(outside_dir, ignore_errors=True)
            outside_dir = None

    if symlink_supported:
        behavior += 1
        if resolve_within(link_dir, "escape.md") is not None:
            failures.append("path containment: a symlink pointing outside the root was accepted")
        behavior += 1
        if resolve_within(link_dir, "inside.md") is None:
            failures.append("path containment: a symlink pointing to an internal file was rejected")
    else:
        skipped += 2
        print(f"  skipped 2 symlink case(s): symbolic links are not available here ({symlink_reason})")

    for directory in (link_dir, outside_dir):
        if directory:
            shutil.rmtree(directory, ignore_errors=True)

    # The same rule is exercised on every platform by simulating what a
    # symbolic link resolves to, so the containment decision is covered even
    # where the account cannot create a link.
    behavior += 1
    original_realpath = os.path.realpath
    simulated_outside = os.path.abspath(os.path.join(tempfile.gettempdir(), "simulated-outside.md"))

    def simulated_realpath(path, *args, **kwargs):
        real = original_realpath(path, *args, **kwargs)
        if os.path.basename(real) == "escape.md":
            return simulated_outside
        return real

    os.path.realpath = simulated_realpath
    try:
        accepted = resolve_within(repo_root, "escape.md") is not None
    finally:
        os.path.realpath = original_realpath
    if accepted:
        failures.append("path containment: a simulated symlink escape was accepted")

    behavior += 1
    original_realpath = os.path.realpath
    simulated_inside = os.path.join(original_realpath(repo_root), "CONTRIBUTING.md")

    def simulated_internal_realpath(path, *args, **kwargs):
        real = original_realpath(path, *args, **kwargs)
        if os.path.basename(real) == "inside.md":
            return simulated_inside
        return real

    os.path.realpath = simulated_internal_realpath
    try:
        accepted = resolve_within(repo_root, "inside.md") is not None
    finally:
        os.path.realpath = original_realpath
    if not accepted:
        failures.append("path containment: a simulated symlink to an internal file was rejected")

    # ------------------------------------------------------------------
    # Behavior cases: Markdown link handling.
    # ------------------------------------------------------------------
    behavior += 1
    targets = extract_link_targets("[x](CONTRIBUTING.md?plain=1)\n")
    if len(targets) != 1:
        failures.append("markdown links: a query string link was not extracted")
    else:
        relative, anchor, query = split_link_target(targets[0])
        if relative != "CONTRIBUTING.md" or query != "plain=1" or anchor is not None:
            failures.append(
                f"markdown links: query string was split incorrectly: {relative!r} {anchor!r} {query!r}"
            )

    behavior += 1
    relative, _anchor, _query = split_link_target("my%20file.md")
    if relative != "my file.md":
        failures.append(f"markdown links: a percent-encoded target was not decoded: {relative!r}")

    behavior += 1
    relative, anchor, _query = split_link_target("<my file.md>")
    if relative != "my file.md" or anchor is not None:
        failures.append(f"markdown links: an angle-bracketed target was not handled: {relative!r}")

    behavior += 1
    targets = extract_link_targets("[x][ref]\n\n[ref]: MISSING.md\n")
    if "MISSING.md" not in targets:
        failures.append("markdown links: a reference-style link definition was not extracted")

    behavior += 1
    temp_root = make_temp_repo(files={
        "README.md": "# Root\n\n[see other](other.md#section)\n",
        "other.md": "# Other\n\n## Section\n",
    })
    try:
        _errors, warnings = run_checks(temp_root)
        if any("other.md" in message for message in warnings):
            failures.append(
                "markdown links: a document referenced only through an anchor was reported as an orphan"
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    temp_root = make_temp_repo(files={
        "README.md": "# Root\n\n[x](other.md#usage-1)\n",
        "other.md": "# Other\n\n## Usage\n\n## Usage\n",
    })
    try:
        errors, _warnings = run_checks(temp_root)
        if any("anchor" in message for message in errors):
            failures.append(
                "markdown links: a link to a repeated heading was reported as a broken anchor: "
                f"{errors}"
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    temp_root = make_temp_repo(files={
        "README.md": "# Root\n\n```text\n[x](MISSING.md)\n```\n\n[x](MISSING.md)\n",
    })
    try:
        errors, _warnings = run_checks(temp_root)
        inside = [message for message in errors if "MISSING.md" in message]
        if len(inside) != 1:
            failures.append(
                "markdown links: a link inside a fenced code block was counted: "
                f"expected 1 error, got {inside}"
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    temp_root = make_temp_repo(files={
        "doc.md": "# Title Here\n\n## A Heading With Punctuation!\n\n### Usage\n\n### Usage\n",
    })
    try:
        anchors = headings(os.path.join(temp_root, "doc.md"))
        expected = {"title-here", "a-heading-with-punctuation", "usage", "usage-1"}
        missing = expected - anchors
        if missing:
            failures.append(
                f"markdown anchors: the heading slugs {sorted(missing)} were not produced, "
                f"got {sorted(anchors)}"
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    # ------------------------------------------------------------------
    # Behavior cases: file discovery rejects links that leave the repository.
    # ------------------------------------------------------------------
    discovery_root = make_temp_repo(files={
        "README.md": "# Root\n",
        "docs/normal.md": "# Normal\n",
        ".github/ISSUE_TEMPLATE/forms.yml": (
            "name: Form\ndescription: A form.\nbody:\n  - type: input\n    id: x\n"
            "    attributes:\n      label: X\n"
        ),
    })
    outside_root = tempfile.mkdtemp()
    with open(os.path.join(outside_root, "external.md"), "w", encoding="utf-8") as handle:
        handle.write("# External\n")
    with open(os.path.join(outside_root, "external.yml"), "w", encoding="utf-8") as handle:
        handle.write("name: External\n")

    symlink_cases = []
    try:
        os.symlink(os.path.join(outside_root, "external.md"),
                    os.path.join(discovery_root, "external.md"))
        os.symlink(os.path.join(outside_root, "external.yml"),
                    os.path.join(discovery_root, "external.yml"))
        os.symlink(os.path.join(discovery_root, "docs", "normal.md"),
                    os.path.join(discovery_root, "internal.md"))
        os.symlink(os.path.join(discovery_root, "docs", "normal.md"),
                    os.path.join(discovery_root, "alias.md"))
        os.symlink(os.path.join(outside_root, "missing.md"),
                    os.path.join(discovery_root, "broken.md"))
        os.makedirs(os.path.join(discovery_root, "linkdir"))
        os.symlink(os.path.join(discovery_root, "docs"),
                    os.path.join(discovery_root, "linkdir", "docs"))
        symlink_cases = ["external_md", "external_yml", "internal_md", "alias_md",
                          "broken_md", "linkdir", "required_symlink"]
    except (OSError, NotImplementedError, AttributeError) as exc:
        skipped += 6
        print(f"  skipped 6 discovery symlink case(s): symbolic links are not available here "
              f"({type(exc).__name__}: {exc})")

    behavior += 1
    files, rejected = repo_files(discovery_root, (".md",))
    names = {display for _path, display in files}
    if "docs/normal.md" not in names:
        failures.append(f"file discovery: a normal Markdown file was not found, got {sorted(names)}")

    behavior += 1
    files, rejected = repo_files(discovery_root, (".yml",))
    names = {display for _path, display in files}
    if ".github/ISSUE_TEMPLATE/forms.yml" not in names:
        failures.append(f"file discovery: a normal YAML file was not found, got {sorted(names)}")

    if symlink_cases:
        behavior += 1
        files, rejected = repo_files(discovery_root, (".md",))
        names = {display for _path, display in files}
        rejected_names = {name for name, _reason in rejected}
        if "external.md" in names:
            failures.append("file discovery: an external Markdown symlink entered the inventory")
        if "external.md" not in rejected_names:
            failures.append(
                f"file discovery: the external Markdown symlink was not reported, got {rejected}"
            )

        behavior += 1
        files, rejected = repo_files(discovery_root, (".yml",))
        names = {display for _path, display in files}
        rejected_names = {name for name, _reason in rejected}
        if "external.yml" in names:
            failures.append("file discovery: an external YAML symlink entered the inventory")
        if "external.yml" not in rejected_names:
            failures.append(
                f"file discovery: the external YAML symlink was not reported, got {rejected}"
            )

        behavior += 1
        files, rejected = repo_files(discovery_root, (".md",))
        names = {display for _path, display in files}
        if "internal.md" not in names:
            failures.append("file discovery: an internal Markdown symlink was not accepted")
        if "alias.md" not in names:
            failures.append("file discovery: a second internal symlink was not accepted")

        behavior += 1
        files, rejected = repo_files(discovery_root, (".md",))
        rejected_names = {name for name, _reason in rejected}
        if "broken.md" not in rejected_names:
            failures.append(
                f"file discovery: a symlink with a missing target was not reported, got {rejected}"
            )

        behavior += 1
        files, rejected = repo_files(discovery_root, (".md",))
        names = {display for _path, display in files}
        if "linkdir/docs/normal.md" not in names:
            failures.append(
                "file discovery: a symlinked directory inside the repository was not followed, "
                f"got {sorted(names)}"
            )

        behavior += 1
        # A required file that is a symlink outside the repository must be
        # reported as unusable rather than accepted.
        os.symlink(os.path.join(outside_root, "external.md"),
                    os.path.join(discovery_root, "REQUIRED.md"))
        ok, reason = required_file_status(discovery_root, "REQUIRED.md")
        if ok or "outside" not in reason:
            failures.append(
                f"required file: an external symlink was accepted, got {(ok, reason)}"
            )

    shutil.rmtree(discovery_root, ignore_errors=True)
    shutil.rmtree(outside_root, ignore_errors=True)

    # The content behind an external symlink must never be read by the
    # validator. A file whose content would break YAML parsing proves it.
    outside_root = tempfile.mkdtemp()
    with open(os.path.join(outside_root, "poison.yml"), "w", encoding="utf-8") as handle:
        handle.write("name: POISON-MARKER\ndescription: [unclosed\n")
    discovery_root = make_temp_repo(files={"README.md": "# Root\n"})
    try:
        os.symlink(os.path.join(outside_root, "poison.yml"),
                    os.path.join(discovery_root, "poison.yml"))
        behavior += 1
        _files, rejected = repo_files(discovery_root, (".yml",))
        rejected_names = {name for name, _reason in rejected}
        if "poison.yml" not in rejected_names:
            failures.append(
                f"file discovery: an external symlink was not rejected, got {rejected}"
            )
        errors, _warnings = run_checks(discovery_root)
        if any("POISON-MARKER" in message for message in errors):
            failures.append("file discovery: the content behind an external symlink was read")
    except (OSError, NotImplementedError, AttributeError):
        skipped += 1
        print("  skipped 1 external-content case(s): symbolic links are not available here")
    shutil.rmtree(discovery_root, ignore_errors=True)
    shutil.rmtree(outside_root, ignore_errors=True)

    # ------------------------------------------------------------------
    # Behavior cases: nothing outside the repository is read or listed.
    # ------------------------------------------------------------------
    marker = "EXTERNAL-SCHEMA-MARKER"
    external_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://example.invalid/external.json",
        "title": marker,
        "type": "object",
    }
    outside_root = tempfile.mkdtemp()
    with open(os.path.join(outside_root, "external.json"), "w", encoding="utf-8") as handle:
        json.dump(external_schema, handle)
    with open(os.path.join(outside_root, "external-only.yml"), "w", encoding="utf-8") as handle:
        handle.write("name: External only\ndescription: External.\nbody: []\n")

    def repo_with_schemas():
        """Build a repository whose schemas directory holds the real schemas."""
        root = make_temp_repo()
        for name in (
            "github-issue-forms.json",
            "github-vulnerability-report-form.json",
            "github-issue-config.json",
        ):
            shutil.copy(
                os.path.join(SCHEMA_SOURCE_DIR, name),
                os.path.join(root, "schemas", name),
            )
        return root

    def schema_mentions_marker(root):
        """True when the schema the validator would use carries the marker."""
        try:
            schemas = load_schemas(root)
        except SystemExit:
            return False
        return any(
            marker in json.dumps(schema) for schema in schemas.values()
        )

    symlinks_available = True
    symlink_reason = ""
    try:
        probe = tempfile.mkdtemp()
        os.symlink(os.path.join(outside_root, "external.json"),
                    os.path.join(probe, "probe.json"))
        shutil.rmtree(probe, ignore_errors=True)
    except (OSError, NotImplementedError, AttributeError) as exc:
        symlinks_available = False
        symlink_reason = f"{type(exc).__name__}: {exc}"

    behavior += 1
    # Normal repository paths: everything resolves and is read.
    plain_root = repo_with_schemas()
    try:
        schemas = load_schemas(plain_root)
        if set(schemas) != {"issue_form", "vulnerability_form", "issue_config"}:
            failures.append(
                f"path containment: a normal repository did not yield the three schemas, got {sorted(schemas)}"
            )
    except SystemExit as exc:
        failures.append(f"path containment: a normal repository was rejected: {exc}")
    finally:
        shutil.rmtree(plain_root, ignore_errors=True)

    if symlinks_available:
        behavior += 1
        # An external schemas directory symlink must never be read.
        root = make_temp_repo()
        shutil.rmtree(os.path.join(root, "schemas"))
        os.symlink(outside_root, os.path.join(root, "schemas"))
        try:
            load_schemas(root)
        except SystemExit:
            pass
        else:
            failures.append("path containment: an external schemas directory symlink was read")
        if schema_mentions_marker(root):
            failures.append("path containment: the external schema content was read")
        shutil.rmtree(root, ignore_errors=True)

        behavior += 1
        # An external individual schema symlink must never be read.
        root = repo_with_schemas()
        os.remove(os.path.join(root, "schemas", "github-issue-forms.json"))
        os.symlink(os.path.join(outside_root, "external.json"),
                   os.path.join(root, "schemas", "github-issue-forms.json"))
        try:
            load_schemas(root)
        except SystemExit:
            pass
        else:
            failures.append("path containment: an external schema symlink was read")
        if schema_mentions_marker(root):
            failures.append("path containment: the external schema content was read")
        shutil.rmtree(root, ignore_errors=True)

        behavior += 1
        # A nested parent symlink must not smuggle an external directory in.
        root = make_temp_repo()
        shutil.rmtree(os.path.join(root, "schemas"))
        os.makedirs(os.path.join(root, "internal"))
        os.symlink(outside_root, os.path.join(root, "internal", "schemas"))
        os.symlink(os.path.join(root, "internal", "schemas"), os.path.join(root, "schemas"))
        try:
            load_schemas(root)
        except SystemExit:
            pass
        else:
            failures.append("path containment: a nested parent symlink was read")
        if schema_mentions_marker(root):
            failures.append("path containment: the external schema content was read")
        shutil.rmtree(root, ignore_errors=True)

        behavior += 1
        # An internal schemas directory symlink is legitimate.
        root = make_temp_repo()
        internal = os.path.join(root, "real-schemas")
        shutil.copytree(os.path.join(root, "schemas"), internal)
        shutil.rmtree(os.path.join(root, "schemas"))
        os.symlink(internal, os.path.join(root, "schemas"))
        try:
            schemas = load_schemas(root)
            if set(schemas) != {"issue_form", "vulnerability_form", "issue_config"}:
                failures.append("path containment: an internal schemas symlink did not resolve")
        except SystemExit as exc:
            failures.append(f"path containment: an internal schemas symlink was rejected: {exc}")
        shutil.rmtree(root, ignore_errors=True)

        behavior += 1
        # An internal file symlink is legitimate.
        root = repo_with_schemas()
        os.remove(os.path.join(root, "schemas", "github-issue-forms.json"))
        os.symlink(os.path.join(root, "schemas", "github-issue-config.json"),
                   os.path.join(root, "schemas", "github-issue-forms.json"))
        try:
            load_schemas(root)
        except SystemExit as exc:
            failures.append(f"path containment: an internal file symlink was rejected: {exc}")
        shutil.rmtree(root, ignore_errors=True)

        behavior += 1
        # A symlink whose target does not exist is reported, not followed.
        root = repo_with_schemas()
        os.remove(os.path.join(root, "schemas", "github-issue-forms.json"))
        os.symlink(os.path.join(root, "schemas", "absent.json"),
                   os.path.join(root, "schemas", "github-issue-forms.json"))
        try:
            load_schemas(root)
        except SystemExit as exc:
            if "broken link" not in str(exc):
                failures.append(
                    f"path containment: a missing symlink target was not reported as such: {exc}"
                )
        else:
            failures.append("path containment: a symlink with a missing target was accepted")
        shutil.rmtree(root, ignore_errors=True)

        behavior += 1
        # An external issue template directory must never be listed.
        root = make_temp_repo()
        template_dir = os.path.join(root, ".github", "ISSUE_TEMPLATE")
        os.makedirs(template_dir, exist_ok=True)
        shutil.rmtree(template_dir)
        os.symlink(outside_root, template_dir)
        errors, _warnings = run_checks(root)
        if not any("ISSUE_TEMPLATE" in message for message in errors):
            failures.append(
                "path containment: an external issue template directory was not reported"
            )
        if any("external-only.yml" in message for message in errors):
            failures.append(
                "path containment: an external issue template file was enumerated"
            )
        shutil.rmtree(root, ignore_errors=True)
    else:
        skipped += 7
        print(f"  skipped 7 containment symlink case(s): symbolic links are not available here "
              f"({symlink_reason})")

    behavior += 1
    # The same decisions, reached without a real symbolic link, so they are
    # covered on every platform.
    original_realpath = os.path.realpath
    original_islink = os.path.islink
    simulated_root = make_temp_repo()
    simulated_outside = os.path.join(outside_root, "external.json")
    simulated_link = os.path.join(simulated_root, "schemas", "github-issue-forms.json")

    def simulated_realpath(path, *args, **kwargs):
        real = original_realpath(path, *args, **kwargs)
        if os.path.abspath(real) == os.path.abspath(simulated_link):
            return simulated_outside
        return real

    def simulated_islink(path):
        if os.path.abspath(path) == os.path.abspath(simulated_link):
            return True
        return original_islink(path)

    os.path.realpath = simulated_realpath
    os.path.islink = simulated_islink
    try:
        try:
            load_schemas(simulated_root)
        except SystemExit:
            rejected = True
        else:
            rejected = False
    finally:
        os.path.realpath = original_realpath
        os.path.islink = original_islink
    if not rejected:
        failures.append(
            "path containment: a simulated external schema symlink was not rejected"
        )
    shutil.rmtree(simulated_root, ignore_errors=True)
    shutil.rmtree(outside_root, ignore_errors=True)

    # ------------------------------------------------------------------
    # Behavior cases: the schema refresh is transactional.
    # ------------------------------------------------------------------
    good_downloads = {
        name: open(os.path.join(SCHEMA_SOURCE_DIR, name), "rb").read()
        for name in ("github-issue-forms.json", "github-issue-config.json")
    }
    for name in update_schemas.UPSTREAM_THIRD_PARTY:
        good_downloads[name] = b"placeholder"

    behavior += 1
    broken = dict(good_downloads)
    broken["github-issue-forms.json"] = b"{ this is not json"
    try:
        update_schemas.build_artifacts(broken)
    except update_schemas.UpdateError:
        pass
    else:
        failures.append("schema refresh: invalid upstream JSON was accepted")

    behavior += 1
    not_a_schema = dict(good_downloads)
    not_a_schema["github-issue-config.json"] = b'{"type": 12}'
    try:
        update_schemas.build_artifacts(not_a_schema)
    except update_schemas.UpdateError:
        pass
    else:
        failures.append("schema refresh: a document that is not a JSON Schema was accepted")

    behavior += 1
    try:
        update_schemas.build_artifacts({"github-issue-forms.json": b"{}"})
    except update_schemas.UpdateError:
        pass
    else:
        failures.append("schema refresh: a missing download was accepted")

    behavior += 1
    temp_root = make_temp_repo()
    try:
        artifacts = {"a.json": b'{"a": 1}\n', "b.json": b'{"b": 2}\n'}
        staging = os.path.join(temp_root, "staging")
        os.makedirs(staging)
        update_schemas.stage_artifacts(artifacts, staging)
        with open(os.path.join(staging, "b.json"), "wb") as handle:
            handle.write(b'{"tampered": true}\n')
        try:
            update_schemas.verify_staged(artifacts, staging)
        except update_schemas.UpdateError:
            pass
        else:
            failures.append("schema refresh: a tampered staged file was not detected")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    downloads = {
        name: open(os.path.join(SCHEMA_SOURCE_DIR, name), "rb").read()
        for name in ("github-issue-forms.json", "github-issue-config.json")
    }
    for name in update_schemas.UPSTREAM_THIRD_PARTY:
        downloads[name] = open(
            os.path.join(SCHEMA_SOURCE_DIR, name.replace("/", os.sep)), "rb"
        ).read()
    rebuilt = update_schemas.build_artifacts(downloads)
    for name in (
        "github-issue-forms.json",
        "github-issue-config.json",
        "github-vulnerability-report-form.json",
    ):
        with open(os.path.join(SCHEMA_SOURCE_DIR, name), "rb") as handle:
            current = handle.read()
        if rebuilt[name] != current:
            failures.append(
                f"schema refresh: rebuilding {name} did not reproduce the vendored file"
            )

    def stage_for(temp_root, artifacts):
        staging = os.path.join(temp_root, "staging")
        os.makedirs(staging, exist_ok=True)
        update_schemas.stage_artifacts(artifacts, staging)
        return staging

    def seed_target(temp_root, artifacts, original=b'{"original": true}\n'):
        target_dir = os.path.join(temp_root, "target")
        os.makedirs(target_dir, exist_ok=True)
        for name in artifacts:
            path = os.path.join(target_dir, name.replace("/", os.sep))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(original)
        return target_dir

    def inject_promotion_failure(fail_at):
        original_replace = os.replace
        state = {"count": 0, "failed": False}

        def failing_replace(source, destination, *args, **kwargs):
            state["count"] += 1
            if state["count"] == fail_at and not state["failed"]:
                state["failed"] = True
                raise OSError("injected promotion failure")
            return original_replace(source, destination, *args, **kwargs)

        return original_replace, failing_replace

    # Failure on the second promotion, and on a later one.
    for fail_at, label in ((2, "the second promotion"), (4, "a subsequent promotion")):
        behavior += 1
        temp_root = make_temp_repo()
        try:
            artifacts = {f"f{i}.json": f'{{"v": {i}}}\n'.encode() for i in range(5)}
            target_dir = seed_target(temp_root, artifacts)
            staging = stage_for(temp_root, artifacts)
            original_replace, failing_replace = inject_promotion_failure(fail_at)
            os.replace = failing_replace
            try:
                update_schemas.promote(artifacts, staging, target_dir, temp_root)
            except OSError:
                pass
            else:
                failures.append(f"schema refresh: the injected failure at {label} did not raise")
            finally:
                os.replace = original_replace
            for name in artifacts:
                with open(os.path.join(target_dir, name), "rb") as handle:
                    content = handle.read()
                if content != b'{"original": true}\n':
                    failures.append(
                        f"schema refresh: rollback after a failure at {label} did not restore {name}"
                    )
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    # Failure while restoring one backup, and while restoring several.
    for promote_count, label in ((2, "one backup"), (4, "multiple backups")):
        behavior += 1
        temp_root = make_temp_repo()
        try:
            artifacts = {f"f{i}.json": f'{{"v": {i}}}\n'.encode() for i in range(5)}
            target_dir = seed_target(temp_root, artifacts)
            staging = stage_for(temp_root, artifacts)
            backup_root = os.path.join(target_dir, update_schemas.BACKUP_DIR_NAME)

            original_replace, failing_replace = inject_promotion_failure(promote_count + 1)
            original_copy2 = shutil.copy2

            def failing_copy2(source, destination, *args, **kwargs):
                if update_schemas.BACKUP_DIR_NAME in str(source):
                    raise OSError("injected restore failure")
                return original_copy2(source, destination, *args, **kwargs)

            os.replace = failing_replace
            shutil.copy2 = failing_copy2
            raised = None
            try:
                update_schemas.promote(artifacts, staging, target_dir, temp_root)
            except Exception as exc:
                raised = exc
            finally:
                os.replace = original_replace
                shutil.copy2 = original_copy2

            if not isinstance(raised, update_schemas.RollbackError):
                failures.append(
                    f"schema refresh: a failure while restoring {label} did not raise "
                    f"RollbackError, got {raised!r}"
                )
            elif update_schemas.BACKUP_DIR_NAME not in str(raised):
                failures.append(
                    f"schema refresh: the recovery location was not reported for {label}: {raised}"
                )
            # The critical assertion: a backup that could not be restored is
            # never deleted, because it is the only recoverable copy.
            survivors = []
            for name in artifacts:
                for dirpath, _dirnames, filenames in os.walk(backup_root):
                    if name in filenames:
                        survivors.append((name, os.path.join(dirpath, name)))
                        break
            if not survivors:
                failures.append(
                    "schema refresh: the recoverable copies were destroyed after a failed "
                    f"rollback of {label}"
                )
            for name, backup in survivors:
                with open(backup, "rb") as handle:
                    content = handle.read()
                if content != b'{"original": true}\n':
                    failures.append(
                        f"schema refresh: the surviving backup for {name} is not the original file"
                    )
            # Recovery after a failed rollback: the surviving backup restores
            # the original file.
            if survivors:
                name, backup = survivors[0]
                target = os.path.join(target_dir, name)
                with open(backup, "rb") as handle:
                    original_bytes = handle.read()
                with open(target, "wb") as handle:
                    handle.write(original_bytes)
                with open(target, "rb") as handle:
                    if handle.read() != b'{"original": true}\n':
                        failures.append(
                            f"schema refresh: recovery after a failed rollback did not restore {name}"
                        )
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    # A rollback failure for an artifact that had no original backup.
    #
    # The artifact that the update created has no original copy, so there is
    # no backup for it and nothing to restore. The failure must be reported
    # as a residual file that is left in place, and never as a recoverable
    # copy, and no reported path may end in "None".
    behavior += 1
    import contextlib
    import io as _io

    temp_root = make_temp_repo()
    try:
        artifacts = {
            "new.json": b'{"v": 0}\n',
            "backed-up.json": b'{"v": 1}\n',
            "failing.json": b'{"v": 2}\n',
        }
        target_dir = os.path.join(temp_root, "target")
        os.makedirs(target_dir, exist_ok=True)
        # "new.json" is deliberately absent from the target directory.
        for name in ("backed-up.json", "failing.json"):
            with open(os.path.join(target_dir, name), "wb") as handle:
                handle.write(b'{"original": true}\n')
        staging = stage_for(temp_root, artifacts)
        backup_root = os.path.join(target_dir, update_schemas.BACKUP_DIR_NAME)

        original_replace = os.replace
        original_copy2 = shutil.copy2
        original_remove = os.remove
        state = {"promotions": 0}

        def failing_replace(source, destination, *args, **kwargs):
            state["promotions"] += 1
            # The third promotion fails, after the new file and the file that
            # has an original copy have both been promoted.
            if state["promotions"] == 3:
                raise OSError("injected promotion failure")
            return original_replace(source, destination, *args, **kwargs)

        def failing_copy2(source, destination, *args, **kwargs):
            # The restore of the original copy fails.
            if update_schemas.BACKUP_DIR_NAME in str(source):
                raise OSError("injected restore failure")
            return original_copy2(source, destination, *args, **kwargs)

        def failing_remove(path, *args, **kwargs):
            # The removal of the newly created file fails.
            if os.path.basename(str(path)) == "new.json":
                raise OSError("injected removal failure")
            return original_remove(path, *args, **kwargs)

        os.replace = failing_replace
        shutil.copy2 = failing_copy2
        os.remove = failing_remove
        raised = None
        stderr_buffer = _io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr_buffer):
                update_schemas.promote(artifacts, staging, target_dir, temp_root)
        except Exception as exc:
            raised = exc
        finally:
            os.replace = original_replace
            shutil.copy2 = original_copy2
            os.remove = original_remove

        stderr_text = stderr_buffer.getvalue()
        new_target = os.path.join(target_dir, "new.json")

        if not isinstance(raised, update_schemas.RollbackError):
            failures.append(
                "schema refresh: a rollback failure without an original backup did not "
                f"raise RollbackError, got {raised!r}"
            )
        else:
            message = str(raised)
            # No recovery path may be reported as "None".
            if "None" in message or "None" in stderr_text:
                failures.append(
                    "schema refresh: the rollback report named a recovery path of None: "
                    f"{message!r} / {stderr_text!r}"
                )
            # The newly created artifact is a residual file, not a backed-up
            # one, and that has to be said explicitly.
            if "did not exist before the update" not in message:
                failures.append(
                    "schema refresh: the rollback report did not say that the newly created "
                    f"file had no original backup: {message!r}"
                )
            if "no original backup for them" not in message:
                failures.append(
                    "schema refresh: the rollback report did not separate the residual files "
                    f"from the recoverable ones: {message!r}"
                )
            # The residual file is named with its exact path.
            if f"new.json at {new_target}" not in message:
                failures.append(
                    "schema refresh: the rollback report did not name the newly created file "
                    f"that was left behind: {message!r}"
                )
            # No backup path may be reported for an artifact that had none.
            if f"new.json at {backup_root}" in message:
                failures.append(
                    "schema refresh: the rollback report named a backup for an artifact that "
                    f"had no original copy: {message!r}"
                )
            # The line that reports the new artifact must not call it a
            # recoverable copy.
            for line in stderr_text.splitlines():
                if "new.json" in line and "recoverable copy" in line:
                    failures.append(
                        "schema refresh: the newly created artifact was reported as a "
                        f"recoverable copy: {line!r}"
                    )
            if "no original backup for it" not in stderr_text:
                failures.append(
                    "schema refresh: the report did not say that the newly created artifact "
                    f"has no original backup: {stderr_text!r}"
                )
            # The genuine recoverable backup is reported with its exact path.
            surviving = []
            for dirpath, _dirnames, filenames in os.walk(backup_root):
                for name in filenames:
                    if name == "backed-up.json":
                        surviving.append(os.path.join(dirpath, name))
            if not surviving:
                failures.append(
                    "schema refresh: the original backup of an existing artifact was "
                    "destroyed after a failed rollback"
                )
            else:
                backup_path = surviving[0]
                with open(backup_path, "rb") as handle:
                    if handle.read() != b'{"original": true}\n':
                        failures.append(
                            "schema refresh: the surviving backup is not the original file"
                        )
                if backup_path not in message:
                    failures.append(
                        "schema refresh: the exact path of the recoverable backup was not "
                        f"reported: {message!r}"
                    )
                if backup_path not in stderr_text:
                    failures.append(
                        "schema refresh: the exact path of the recoverable backup was not "
                        f"reported: {stderr_text!r}"
                    )
            # The residual file is still there, so that it can be found and
            # removed by hand.
            if not os.path.exists(new_target):
                failures.append(
                    "schema refresh: the newly created artifact was reported as a residual "
                    "file, but it is no longer there"
                )

            # The command line has to describe the same mixed situation.
            original_refresh = update_schemas.refresh

            def failing_refresh():
                raise raised

            cli_buffer = _io.StringIO()
            try:
                update_schemas.refresh = failing_refresh
                with contextlib.redirect_stderr(cli_buffer):
                    exit_code = update_schemas.main()
            finally:
                update_schemas.refresh = original_refresh
            cli_text = cli_buffer.getvalue()
            if exit_code == 0:
                failures.append(
                    "schema refresh: an incomplete rollback did not fail the command"
                )
            if "INCOMPLETE" not in cli_text:
                failures.append(
                    f"schema refresh: an incomplete rollback was not reported as such: {cli_text!r}"
                )
            if "nothing was changed" in cli_text:
                failures.append(
                    f"schema refresh: an incomplete rollback claimed that nothing changed: {cli_text!r}"
                )
            # The command line must not claim that every affected file can be
            # restored from the recovery directory.
            if "Restore the" in cli_text:
                failures.append(
                    "schema refresh: the command line still claims that every affected file "
                    f"can be restored from the recovery directory: {cli_text!r}"
                )
            if "inspected and removed by hand" not in cli_text:
                failures.append(
                    "schema refresh: the command line does not mention the files that were "
                    f"left behind: {cli_text!r}"
                )
            if "no original backup" not in cli_text:
                failures.append(
                    "schema refresh: the command line does not report that an affected file "
                    f"has no original backup: {cli_text!r}"
                )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    # A rollback failure for an artifact whose original backup has
    # disappeared.
    #
    # The artifact existed before the promotion and its backup was created,
    # but the backup is gone by the time the rollback starts. The original
    # content cannot be restored, and removing the promoted file would not
    # restore it either, so the promoted file must be left in place.
    behavior += 1
    import contextlib
    import io as _io

    temp_root = make_temp_repo()
    try:
        artifacts = {
            "missing-backup.json": b'{"v": 0}\n',
            "kept-backup.json": b'{"v": 1}\n',
            "failing.json": b'{"v": 2}\n',
        }
        target_dir = os.path.join(temp_root, "target")
        os.makedirs(target_dir, exist_ok=True)
        for name in artifacts:
            with open(os.path.join(target_dir, name), "wb") as handle:
                handle.write(b'{"original": true}\n')
        staging = stage_for(temp_root, artifacts)
        backup_root = os.path.join(target_dir, update_schemas.BACKUP_DIR_NAME)

        original_replace = os.replace
        original_copy2 = shutil.copy2
        state = {"promotions": 0, "backup_existed": False, "backup_bytes": b""}
        recorded_backups = {}

        def patched_copy2(source, destination, *args, **kwargs):
            source_text = str(source)
            destination_text = str(destination)
            if update_schemas.BACKUP_DIR_NAME in source_text:
                # A restore: the original copy cannot be put back in place.
                raise OSError("injected restore failure")
            if update_schemas.BACKUP_DIR_NAME in destination_text:
                # A backup: the original content is being copied aside.
                recorded_backups[os.path.basename(destination_text)] = destination_text
            return original_copy2(source, destination, *args, **kwargs)

        def patched_replace(source, destination, *args, **kwargs):
            state["promotions"] += 1
            if state["promotions"] == 3:
                # The third promotion fails, after the first two succeeded.
                raise OSError("injected promotion failure")
            result = original_replace(source, destination, *args, **kwargs)
            if state["promotions"] == 1:
                # The first artifact has been promoted and its backup has
                # been created. The backup then disappears, before the
                # rollback begins.
                backup_path = recorded_backups.get("missing-backup.json")
                if backup_path and os.path.exists(backup_path):
                    with open(backup_path, "rb") as handle:
                        state["backup_bytes"] = handle.read()
                    state["backup_existed"] = True
                    os.remove(backup_path)
            return result

        os.replace = patched_replace
        shutil.copy2 = patched_copy2
        raised = None
        stderr_buffer = _io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr_buffer):
                update_schemas.promote(artifacts, staging, target_dir, temp_root)
        except Exception as exc:
            raised = exc
        finally:
            os.replace = original_replace
            shutil.copy2 = original_copy2

        stderr_text = stderr_buffer.getvalue()
        missing_target = os.path.join(target_dir, "missing-backup.json")

        # The test has to prove that the backup existed before it vanished.
        if not state["backup_existed"]:
            failures.append(
                "schema refresh: the backup of the missing-backup artifact did not exist "
                "before it disappeared"
            )
        if state["backup_bytes"] != b'{"original": true}\n':
            failures.append(
                "schema refresh: the backup that disappeared was not the original file"
            )

        if not isinstance(raised, update_schemas.RollbackError):
            failures.append(
                "schema refresh: a rollback with a missing original backup did not raise "
                f"RollbackError, got {raised!r}"
            )
        else:
            message = str(raised)
            recoverable_sentence = ""
            missing_sentence = ""
            new_sentence = ""
            for sentence in message.split(". "):
                if "the original copies are recoverable" in sentence:
                    recoverable_sentence = sentence
                elif "the original backup of these files is missing" in sentence:
                    missing_sentence = sentence
                elif "did not exist before the update" in sentence:
                    new_sentence = sentence
            # The artifact is classified as missing, not as recoverable and
            # not as a newly created file.
            if "missing-backup.json" not in missing_sentence:
                failures.append(
                    "schema refresh: the artifact whose original backup disappeared was not "
                    f"reported as missing: {message!r}"
                )
            if "missing-backup.json" in recoverable_sentence:
                failures.append(
                    "schema refresh: the artifact whose original backup disappeared was "
                    f"reported as recoverable: {message!r}"
                )
            if "missing-backup.json" in new_sentence:
                failures.append(
                    "schema refresh: the artifact whose original backup disappeared was "
                    f"reported as a newly created file: {message!r}"
                )
            # The original content must not be claimed to be recoverable.
            if "cannot be restored" not in missing_sentence:
                failures.append(
                    "schema refresh: the report does not say that the original content "
                    f"cannot be restored: {message!r}"
                )
            # No recovery path may be reported as "None".
            if "None" in message or "None" in stderr_text:
                failures.append(
                    "schema refresh: the rollback report named a recovery path of None: "
                    f"{message!r} / {stderr_text!r}"
                )
            # The promoted file is left in place, because deleting it would
            # not restore the original.
            if not os.path.exists(missing_target):
                failures.append(
                    "schema refresh: the promoted file was deleted although its original "
                    "backup was missing"
                )
            else:
                with open(missing_target, "rb") as handle:
                    if handle.read() != b'{"v": 0}\n':
                        failures.append(
                            "schema refresh: the promoted file was changed although its "
                            "original backup was missing"
                        )
            # The exact target path is reported.
            if f"missing-backup.json at {missing_target}" not in message:
                failures.append(
                    "schema refresh: the exact target path of the artifact whose original "
                    f"backup disappeared was not reported: {message!r}"
                )
            # The report says that the original backup is missing.
            if "the original backup of missing-backup.json is missing" not in stderr_text:
                failures.append(
                    "schema refresh: the report did not say that the original backup is "
                    f"missing: {stderr_text!r}"
                )
            if "cannot be restored" not in stderr_text:
                failures.append(
                    "schema refresh: the report did not say that the original content "
                    f"cannot be restored: {stderr_text!r}"
                )
            # The other original backup survives, unchanged, and is reported.
            surviving = []
            for dirpath, _dirnames, filenames in os.walk(backup_root):
                for name in filenames:
                    if name == "kept-backup.json":
                        surviving.append(os.path.join(dirpath, name))
            if not surviving:
                failures.append(
                    "schema refresh: the original backup of the other artifact was destroyed "
                    "after a failed rollback"
                )
            else:
                backup_path = surviving[0]
                with open(backup_path, "rb") as handle:
                    if handle.read() != b'{"original": true}\n':
                        failures.append(
                            "schema refresh: the surviving backup is not the original file"
                        )
                if backup_path not in message:
                    failures.append(
                        "schema refresh: the exact path of the recoverable backup was not "
                        f"reported: {message!r}"
                    )
            # The transaction directory must not be cleaned up while the
            # rollback is incomplete.
            transaction_dirs = [
                os.path.join(dirpath, name)
                for dirpath, dirnames, _files in os.walk(backup_root)
                for name in dirnames
            ]
            if not transaction_dirs:
                failures.append(
                    "schema refresh: the transaction recovery directory was cleaned up "
                    "although the rollback was incomplete"
                )

            # The command line has to describe the missing backup as well.
            original_refresh = update_schemas.refresh

            def failing_refresh():
                raise raised

            cli_buffer = _io.StringIO()
            try:
                update_schemas.refresh = failing_refresh
                with contextlib.redirect_stderr(cli_buffer):
                    exit_code = update_schemas.main()
            finally:
                update_schemas.refresh = original_refresh
            cli_text = cli_buffer.getvalue()
            if exit_code == 0:
                failures.append(
                    "schema refresh: an incomplete rollback did not fail the command"
                )
            if "INCOMPLETE" not in cli_text:
                failures.append(
                    f"schema refresh: an incomplete rollback was not reported as such: {cli_text!r}"
                )
            if "nothing was changed" in cli_text:
                failures.append(
                    f"schema refresh: an incomplete rollback claimed that nothing changed: {cli_text!r}"
                )
            if "original backup is missing" not in cli_text:
                failures.append(
                    "schema refresh: the command line does not describe the missing original "
                    f"backup: {cli_text!r}"
                )
            if "cannot be restored" not in cli_text:
                failures.append(
                    "schema refresh: the command line does not say that the original content "
                    f"cannot be restored: {cli_text!r}"
                )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    # A failure while removing the backups after a successful promotion is
    # reported but does not fail the promotion.
    behavior += 1
    temp_root = make_temp_repo()
    try:
        artifacts = {f"f{i}.json": f'{{"v": {i}}}\n'.encode() for i in range(3)}
        target_dir = seed_target(temp_root, artifacts)
        staging = stage_for(temp_root, artifacts)
        original_remove = os.remove

        def failing_remove(path, *args, **kwargs):
            if update_schemas.BACKUP_DIR_NAME in str(path):
                raise OSError("injected cleanup failure")
            return original_remove(path, *args, **kwargs)

        os.remove = failing_remove
        try:
            update_schemas.promote(artifacts, staging, target_dir, temp_root)
        except Exception as exc:
            failures.append(f"schema refresh: a backup cleanup failure failed the promotion: {exc}")
        finally:
            os.remove = original_remove
        for index, name in enumerate(sorted(artifacts)):
            with open(os.path.join(target_dir, name), "rb") as handle:
                content = handle.read()
            if content != f'{{"v": {index}}}\n'.encode():
                failures.append(f"schema refresh: the promotion did not write {name}")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    # A completely successful refresh leaves no temporary or backup files.
    behavior += 1
    temp_root = make_temp_repo()
    try:
        artifacts = {f"f{i}.json": f'{{"v": {i}}}\n'.encode() for i in range(3)}
        target_dir = seed_target(temp_root, artifacts)
        staging = stage_for(temp_root, artifacts)
        update_schemas.promote(artifacts, staging, target_dir, temp_root)
        leftovers = []
        for dirpath, dirnames, filenames in os.walk(target_dir):
            for name in filenames:
                if update_schemas.BACKUP_DIR_NAME in dirpath or name.endswith(".naabtech-restore"):
                    leftovers.append(os.path.join(dirpath, name))
        if leftovers:
            failures.append(
                f"schema refresh: a successful refresh left files behind: {leftovers}"
            )
        if os.path.exists(os.path.join(target_dir, update_schemas.BACKUP_DIR_NAME)):
            failures.append(
                "schema refresh: the backup directory survived a completely successful refresh"
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    # ------------------------------------------------------------------
    # Behavior cases: a preserved recovery copy survives a later update.
    # ------------------------------------------------------------------
    def transaction_dirs(target_dir):
        root = os.path.join(target_dir, update_schemas.BACKUP_DIR_NAME)
        if not os.path.isdir(root):
            return []
        return sorted(
            os.path.join(root, name)
            for name in os.listdir(root)
            if name.startswith(update_schemas.TRANSACTION_PREFIX)
        )

    def failed_transaction(temp_root, artifacts, target_dir, original):
        """Run a promotion whose rollback also fails, and return the backups."""
        staging = stage_for(temp_root, artifacts)
        original_replace, failing_replace = inject_promotion_failure(2)
        original_copy2 = shutil.copy2

        def failing_copy2(source, destination, *args, **kwargs):
            if update_schemas.BACKUP_DIR_NAME in str(source):
                raise OSError("injected restore failure")
            return original_copy2(source, destination, *args, **kwargs)

        os.replace = failing_replace
        shutil.copy2 = failing_copy2
        try:
            update_schemas.promote(artifacts, staging, target_dir, temp_root)
        except Exception:
            pass
        finally:
            os.replace = original_replace
            shutil.copy2 = original_copy2
        preserved = {}
        for directory in transaction_dirs(target_dir):
            for name in artifacts:
                candidate = os.path.join(directory, name)
                if os.path.exists(candidate):
                    preserved[candidate] = open(candidate, "rb").read()
        return preserved

    behavior += 1
    # A failed rollback leaves a recovery copy, and a later transaction must not
    # overwrite it.
    temp_root = make_temp_repo()
    try:
        artifacts = {"f0.json": b'{"v": 0}\n', "f1.json": b'{"v": 1}\n'}
        target_dir = seed_target(temp_root, artifacts, original=b"ORIGINAL-CONTENT\n")

        first_backups = failed_transaction(temp_root, artifacts, target_dir, b"ORIGINAL-CONTENT\n")
        if not first_backups:
            failures.append("schema refresh: the recovery copy was not preserved")
        first_dirs = transaction_dirs(target_dir)
        if len(first_dirs) != 1:
            failures.append(
                f"schema refresh: expected one transaction directory, got {first_dirs}"
            )

        # A second failed transaction gets its own directory and leaves the
        # earlier recovery copy alone.
        second_backups = failed_transaction(temp_root, artifacts, target_dir, b"ORIGINAL-CONTENT\n")
        second_dirs = transaction_dirs(target_dir)
        if len(second_dirs) < 2:
            failures.append(
                f"schema refresh: two failed transactions left {len(second_dirs)} directories"
            )
        if len(second_dirs) <= len(first_dirs):
            failures.append(
                "schema refresh: the second transaction did not create its own directory"
            )
        for path, content in first_backups.items():
            if not os.path.exists(path):
                failures.append(
                    f"schema refresh: the earlier recovery copy {path} was deleted"
                )
                continue
            with open(path, "rb") as handle:
                if handle.read() != content:
                    failures.append(
                        f"schema refresh: the earlier recovery copy {path} was overwritten"
                    )
        for path, content in second_backups.items():
            with open(path, "rb") as handle:
                if handle.read() != content:
                    failures.append(
                        f"schema refresh: the recovery copy {path} is not the original"
                    )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    # Two failed transactions keep two independent recovery copies.
    temp_root = make_temp_repo()
    try:
        artifacts = {"f0.json": b'{"v": 0}\n', "f1.json": b'{"v": 1}\n'}
        target_dir = seed_target(temp_root, artifacts, original=b"ORIGINAL-CONTENT\n")
        first_backups = failed_transaction(
            temp_root, artifacts, target_dir, b"ORIGINAL-CONTENT\n")
        second_backups = failed_transaction(
            temp_root, artifacts, target_dir, b"ORIGINAL-CONTENT\n")
        directories = transaction_dirs(target_dir)
        if len(directories) < 2:
            failures.append(
                f"schema refresh: two failed transactions left {len(directories)} directories"
            )
        for mapping in (first_backups, second_backups):
            for path, content in mapping.items():
                if not os.path.exists(path):
                    failures.append(
                        f"schema refresh: the recovery copy {path} was deleted"
                    )
                    continue
                with open(path, "rb") as handle:
                    if handle.read() != content:
                        failures.append(
                            f"schema refresh: the recovery copy {path} was overwritten"
                        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    # A successful transaction after an earlier failed one leaves the earlier
    # recovery copy alone.
    temp_root = make_temp_repo()
    try:
        artifacts = {"f0.json": b'{"v": 0}\n', "f1.json": b'{"v": 1}\n'}
        target_dir = seed_target(temp_root, artifacts, original=b"ORIGINAL-CONTENT\n")
        failed_transaction(temp_root, artifacts, target_dir, b"ORIGINAL-CONTENT\n")

        earlier = transaction_dirs(target_dir)
        preserved = {}
        for directory in earlier:
            candidate = os.path.join(directory, "f0.json")
            if os.path.exists(candidate):
                preserved[candidate] = open(candidate, "rb").read()
        if not preserved:
            failures.append(
                "schema refresh: the earlier failed transaction left no recovery copy"
            )

        second_artifacts = {"f0.json": b'{"v": 7}\n'}
        second_staging = stage_for(temp_root, second_artifacts)
        update_schemas.promote(second_artifacts, second_staging, target_dir, temp_root)
        for path, content in preserved.items():
            if not os.path.exists(path):
                failures.append(
                    f"schema refresh: a successful transaction deleted the recovery copy {path}"
                )
                continue
            with open(path, "rb") as handle:
                if handle.read() != content:
                    failures.append(
                        f"schema refresh: a successful transaction overwrote the recovery copy {path}"
                    )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    # A concurrent refresh is refused while the lock is held.
    temp_root = make_temp_repo()
    try:
        lock_path = update_schemas.acquire_update_lock(temp_root, temp_root)
        try:
            update_schemas.acquire_update_lock(temp_root, temp_root)
        except update_schemas.UpdateError:
            pass
        else:
            failures.append("schema refresh: a concurrent refresh was not refused")
        finally:
            update_schemas.release_update_lock(lock_path)
        if os.path.exists(lock_path):
            failures.append("schema refresh: the lock file was not released")
        # The lock can be taken again once it has been released.
        again = update_schemas.acquire_update_lock(temp_root, temp_root)
        update_schemas.release_update_lock(again)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    behavior += 1
    # A successful promotion with the real nested artifact layout leaves no
    # staging file, restore file, backup file, or empty transaction directory.
    temp_root = make_temp_repo()
    try:
        artifacts = {
            "github-issue-forms.json": b'{"v": 1}\n',
            "third-party/LICENSE-Apache-2.0.txt": b"license\n",
            "third-party/NOTICE-SchemaStore.txt": b"notice\n",
        }
        target_dir = seed_target(temp_root, artifacts, original=b"ORIGINAL\n")
        staging = stage_for(temp_root, artifacts)
        update_schemas.promote(artifacts, staging, target_dir, temp_root)

        leftovers = []
        for dirpath, dirnames, filenames in os.walk(target_dir):
            for name in filenames:
                if (update_schemas.BACKUP_DIR_NAME in dirpath
                        or name.endswith(".naabtech-restore")
                        or name.endswith(".tmp")):
                    leftovers.append(os.path.join(dirpath, name))
            for name in dirnames:
                if name.startswith(update_schemas.TRANSACTION_PREFIX):
                    leftovers.append(os.path.join(dirpath, name))
        if leftovers:
            failures.append(
                f"schema refresh: a successful nested promotion left files behind: {leftovers}"
            )
        backup_root = os.path.join(target_dir, update_schemas.BACKUP_DIR_NAME)
        if os.path.exists(backup_root):
            failures.append(
                "schema refresh: the backup root survived a completely successful promotion"
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


    # ------------------------------------------------------------------
    # Behavior cases: the schema updater stays inside the repository.
    # ------------------------------------------------------------------
    updater_symlinks = True
    updater_symlink_reason = ""
    try:
        updater_probe = tempfile.mkdtemp()
        os.symlink(os.path.join(updater_probe, "target"), os.path.join(updater_probe, "link"))
        shutil.rmtree(updater_probe, ignore_errors=True)
    except (OSError, NotImplementedError, AttributeError) as exc:
        updater_symlinks = False
        updater_symlink_reason = f"{type(exc).__name__}: {exc}"

    if updater_symlinks:
        sentinel_bytes = b"EXTERNAL-SENTINEL-CONTENT\n"

        def sentinel_tree():
            """A directory outside the repository holding a sentinel file."""
            outside = tempfile.mkdtemp()
            with open(os.path.join(outside, "sentinel.bin"), "wb") as handle:
                handle.write(sentinel_bytes)
            return outside

        def outside_is_untouched(outside):
            """The sentinel must be byte-for-byte unchanged."""
            path = os.path.join(outside, "sentinel.bin")
            if not os.path.exists(path):
                return False, "sentinel.bin was removed"
            with open(path, "rb") as handle:
                if handle.read() != sentinel_bytes:
                    return False, "sentinel.bin was overwritten"
            return True, ""

        def schema_repo():
            """A repository-shaped tree with a real schemas directory."""
            root = make_temp_repo()
            for name in (
                "github-issue-forms.json",
                "github-vulnerability-report-form.json",
                "github-issue-config.json",
            ):
                shutil.copy(
                    os.path.join(SCHEMA_SOURCE_DIR, name),
                    os.path.join(root, "schemas", name),
                )
            os.makedirs(os.path.join(root, "schemas", "third-party"), exist_ok=True)
            return root

        def updater_artifacts():
            return {
                "github-issue-forms.json": b'{"v": 1}\n',
                "third-party/NOTICE-SchemaStore.txt": b"notice\n",
            }

        def no_external_content_copied(root):
            """No file inside the repository may hold the sentinel content.

            A symbolic link is not followed. A link still points at the
            external file; it is not a copy of it, and the file behind it is
            not part of the repository.
            """
            stray = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [
                    name
                    for name in dirnames
                    if not os.path.islink(os.path.join(dirpath, name))
                ]
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    if os.path.islink(path):
                        continue
                    try:
                        with open(path, "rb") as handle:
                            if handle.read() == sentinel_bytes:
                                stray.append(path)
                    except OSError:
                        continue
            return stray

        def outside_entries(outside):
            """The names that exist in the external directory."""
            return sorted(os.listdir(outside))

        # 1. A schemas directory that points outside the repository.
        behavior += 1
        outside = sentinel_tree()
        root = schema_repo()
        try:
            shutil.rmtree(os.path.join(root, "schemas"))
            os.symlink(outside, os.path.join(root, "schemas"))
            try:
                update_schemas.canonical_schema_dir(root)
            except update_schemas.UpdateError:
                pass
            else:
                failures.append(
                    "schema updater: a schemas directory pointing outside the repository was accepted"
                )
            # Even if the first check were bypassed, the lock must not be
            # created in the external directory either.
            try:
                update_schemas.acquire_update_lock(os.path.join(root, "schemas"), root)
            except update_schemas.UpdateError:
                pass
            else:
                failures.append(
                    "schema updater: an update lock was taken in a schemas directory "
                    "pointing outside the repository"
                )
            ok, detail = outside_is_untouched(outside)
            if not ok:
                failures.append(f"schema updater: the external sentinel was touched: {detail}")
            # No lock, staging, backup or restore file may appear outside.
            entries = outside_entries(outside)
            if entries != ["sentinel.bin"]:
                failures.append(
                    f"schema updater: files were written outside the repository: {entries}"
                )
            stray = no_external_content_copied(root)
            if stray:
                failures.append(
                    f"schema updater: external content was copied into the repository: {stray}"
                )
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(outside, ignore_errors=True)

        # 2. A schemas/third-party directory that points outside the repository.
        behavior += 1
        outside = sentinel_tree()
        root = schema_repo()
        try:
            shutil.rmtree(os.path.join(root, "schemas", "third-party"))
            os.symlink(outside, os.path.join(root, "schemas", "third-party"))
            target_dir = os.path.join(root, "schemas")
            staging = os.path.join(root, "staging")
            os.makedirs(staging, exist_ok=True)
            artifacts = updater_artifacts()
            update_schemas.stage_artifacts(artifacts, staging)
            try:
                update_schemas.promote(artifacts, staging, target_dir, root)
            except update_schemas.UpdateError:
                pass
            else:
                failures.append(
                    "schema updater: a third-party directory pointing outside the repository "
                    "was accepted"
                )
            ok, detail = outside_is_untouched(outside)
            if not ok:
                failures.append(f"schema updater: the external sentinel was touched: {detail}")
            stray = no_external_content_copied(root)
            if stray:
                failures.append(
                    f"schema updater: external content was copied into the repository: {stray}"
                )
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(outside, ignore_errors=True)

        # 3. A backup directory that points outside the repository.
        behavior += 1
        outside = sentinel_tree()
        root = schema_repo()
        try:
            target_dir = os.path.join(root, "schemas")
            staging = os.path.join(root, "staging")
            os.makedirs(staging, exist_ok=True)
            artifacts = updater_artifacts()
            update_schemas.stage_artifacts(artifacts, staging)
            os.symlink(outside, os.path.join(target_dir, update_schemas.BACKUP_DIR_NAME))
            try:
                update_schemas.promote(artifacts, staging, target_dir, root)
            except update_schemas.UpdateError:
                pass
            else:
                failures.append(
                    "schema updater: a backup directory pointing outside the repository was accepted"
                )
            ok, detail = outside_is_untouched(outside)
            if not ok:
                failures.append(f"schema updater: the external sentinel was touched: {detail}")
            stray = no_external_content_copied(root)
            if stray:
                failures.append(
                    f"schema updater: external content was copied into the repository: {stray}"
                )
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(outside, ignore_errors=True)

        # 4. An artifact target that is itself a symbolic link pointing outside.
        behavior += 1
        outside = sentinel_tree()
        root = schema_repo()
        try:
            target_dir = os.path.join(root, "schemas")
            staging = os.path.join(root, "staging")
            os.makedirs(staging, exist_ok=True)
            artifacts = updater_artifacts()
            update_schemas.stage_artifacts(artifacts, staging)
            os.remove(os.path.join(target_dir, "github-issue-forms.json"))
            os.symlink(
                os.path.join(outside, "sentinel.bin"),
                os.path.join(target_dir, "github-issue-forms.json"),
            )
            try:
                update_schemas.promote(artifacts, staging, target_dir, root)
            except update_schemas.UpdateError:
                pass
            else:
                failures.append(
                    "schema updater: an artifact target pointing outside the repository was accepted"
                )
            ok, detail = outside_is_untouched(outside)
            if not ok:
                failures.append(f"schema updater: the external sentinel was touched: {detail}")
            stray = no_external_content_copied(root)
            if stray:
                failures.append(
                    f"schema updater: external content was copied into the repository: {stray}"
                )
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(outside, ignore_errors=True)

        # 5. An internal symbolic link is still handled consistently.
        behavior += 1
        root = schema_repo()
        try:
            target_dir = os.path.join(root, "schemas")
            staging = os.path.join(root, "staging")
            os.makedirs(staging, exist_ok=True)
            artifacts = updater_artifacts()
            update_schemas.stage_artifacts(artifacts, staging)
            internal = os.path.join(target_dir, "internal-copy.json")
            shutil.copy(os.path.join(target_dir, "github-issue-config.json"), internal)
            os.remove(os.path.join(target_dir, "github-issue-forms.json"))
            os.symlink(internal, os.path.join(target_dir, "github-issue-forms.json"))
            update_schemas.promote(artifacts, staging, target_dir, root)
            with open(os.path.join(target_dir, "github-issue-forms.json"), "rb") as handle:
                if handle.read() != b'{"v": 1}\n':
                    failures.append(
                        "schema updater: an internal symbolic link target was not replaced"
                    )
        except update_schemas.UpdateError as exc:
            failures.append(f"schema updater: an internal symbolic link was rejected: {exc}")
        finally:
            shutil.rmtree(root, ignore_errors=True)
    else:
        skipped += 5
        print(f"  skipped 5 updater containment case(s): symbolic links are not available here "
              f"({updater_symlink_reason})")

    # ------------------------------------------------------------------
    # Behavior case: a failed rollback is reported as such.
    # ------------------------------------------------------------------
    import contextlib
    import io as _io

    behavior += 1
    original_refresh = update_schemas.refresh

    def failing_refresh():
        raise update_schemas.RollbackError(
            "promotion failed (injected) and 1 file(s) could not be restored: f0.json. "
            "Recoverable copies are kept in /tmp/transaction-abc123"
        )

    update_schemas.refresh = failing_refresh
    try:
        buffer = _io.StringIO()
        with contextlib.redirect_stderr(buffer):
            exit_code = update_schemas.main()
    finally:
        update_schemas.refresh = original_refresh
    stderr_text = buffer.getvalue()
    if exit_code == 0:
        failures.append("schema updater: an incomplete rollback did not fail the command")
    if "INCOMPLETE" not in stderr_text:
        failures.append(
            f"schema updater: an incomplete rollback was not reported as such: {stderr_text!r}"
        )
    if "transaction-abc123" not in stderr_text:
        failures.append(
            f"schema updater: the recovery directory was not reported: {stderr_text!r}"
        )
    if "f0.json" not in stderr_text:
        failures.append(
            f"schema updater: the affected artifact was not reported: {stderr_text!r}"
        )
    if "nothing was changed" in stderr_text:
        failures.append(
            f"schema updater: an incomplete rollback claimed that nothing changed: {stderr_text!r}"
        )

    # The generic failure handler must not claim anything about the state of
    # the filesystem either.
    def failing_refresh_generic():
        raise update_schemas.UpdateError("injected generic failure")

    update_schemas.refresh = failing_refresh_generic
    try:
        buffer = _io.StringIO()
        with contextlib.redirect_stderr(buffer):
            exit_code = update_schemas.main()
    finally:
        update_schemas.refresh = original_refresh
    stderr_text = buffer.getvalue()
    if exit_code == 0:
        failures.append("schema updater: a generic failure did not fail the command")
    if "nothing was changed" in stderr_text:
        failures.append(
            f"schema updater: the generic handler claimed that nothing changed: {stderr_text!r}"
        )

    checked = negative + positive + behavior
    applicable = checked + skipped
    total = checked
    print(
        f"validate_docs tests: {negative} negative case(s), {positive} positive control(s), "
        f"and {behavior} behavior case(s) checked ({checked} checked, {skipped} skipped, "
        f"{applicable} applicable)"
    )
    if failures:
        for failure in failures:
            print(f"  FAIL {failure}")
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("  all cases behaved as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
