#!/usr/bin/env python3
"""Negative and positive tests for the documentation validator.

The suite contains three kinds of case:

- **Negative cases** - intentionally invalid documents. The validator must
  report an error for each one, so that a regression which silently accepts a
  malformed form is caught.
- **Positive control cases** - valid documents. The validator must report no
  errors at all for these, so that the checks cannot become so strict that
  they reject a good form.
- **Behaviour cases** - specific behaviours that were implemented in response
  to a confirmed defect: schema injection, path containment, and the Markdown
  link edge cases.

The expected error text is pinned for each negative case, so a change in the
validator that stops detecting a problem is visible.

Usage:
    python scripts/test_validate_docs.py
"""

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


import json  # noqa: E402  (used by make_temp_repo)


def run():
    failures = []
    positive = 0
    negative = 0
    behaviour = 0

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
    # Behaviour case: the issue configuration schema is taken from the
    # repository being validated, not from a global constant.
    # ------------------------------------------------------------------
    behaviour += 1
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

    behaviour += 1
    errors, _warnings = run_checks(os.path.abspath(os.path.join(os.path.dirname(SCHEMA_SOURCE_DIR))))
    if any("alternate_marker" in message for message in errors):
        failures.append(
            "issue configuration schema injection: the real repository must not report the "
            "alternate schema's requirement"
        )

    # ------------------------------------------------------------------
    # Behaviour cases: path containment.
    # ------------------------------------------------------------------
    repo_root = os.path.abspath(os.path.join(os.path.dirname(SCHEMA_SOURCE_DIR)))
    behaviour += 1
    if resolve_within(repo_root, "CONTRIBUTING.md") is None:
        failures.append("path containment: a normal internal file was rejected")

    behaviour += 1
    if resolve_within(repo_root, "../../../../Windows/win.ini") is not None:
        failures.append("path containment: a relative path escaping the root was accepted")

    behaviour += 1
    outside = os.path.abspath(os.path.join(repo_root, "..", "..", "outside.txt"))
    if resolve_within(repo_root, outside) is not None:
        failures.append("path containment: an absolute path outside the root was accepted")

    behaviour += 1
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
        behaviour += 1
        if resolve_within(link_dir, "escape.md") is not None:
            failures.append("path containment: a symlink pointing outside the root was accepted")
        behaviour += 1
        if resolve_within(link_dir, "inside.md") is None:
            failures.append("path containment: a symlink pointing to an internal file was rejected")
    else:
        print(f"  skipped 2 symlink case(s): symbolic links are not available here ({symlink_reason})")

    for directory in (link_dir, outside_dir):
        if directory:
            shutil.rmtree(directory, ignore_errors=True)

    # The same rule is exercised on every platform by simulating what a
    # symbolic link resolves to, so the containment decision is covered even
    # where the account cannot create a link.
    behaviour += 1
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

    behaviour += 1
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
    # Behaviour cases: Markdown link handling.
    # ------------------------------------------------------------------
    behaviour += 1
    targets = extract_link_targets("[x](CONTRIBUTING.md?plain=1)\n")
    if len(targets) != 1:
        failures.append("markdown links: a query string link was not extracted")
    else:
        relative, anchor, query = split_link_target(targets[0])
        if relative != "CONTRIBUTING.md" or query != "plain=1" or anchor is not None:
            failures.append(
                f"markdown links: query string was split incorrectly: {relative!r} {anchor!r} {query!r}"
            )

    behaviour += 1
    relative, _anchor, _query = split_link_target("my%20file.md")
    if relative != "my file.md":
        failures.append(f"markdown links: a percent-encoded target was not decoded: {relative!r}")

    behaviour += 1
    relative, anchor, _query = split_link_target("<my file.md>")
    if relative != "my file.md" or anchor is not None:
        failures.append(f"markdown links: an angle-bracketed target was not handled: {relative!r}")

    behaviour += 1
    targets = extract_link_targets("[x][ref]\n\n[ref]: MISSING.md\n")
    if "MISSING.md" not in targets:
        failures.append("markdown links: a reference-style link definition was not extracted")

    behaviour += 1
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

    behaviour += 1
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

    behaviour += 1
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

    behaviour += 1
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
    # Behaviour cases: file discovery rejects links that leave the repository.
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
        print(f"  skipped 6 discovery symlink case(s): symbolic links are not available here "
              f"({type(exc).__name__}: {exc})")

    behaviour += 1
    files, rejected = repo_files(discovery_root, (".md",))
    names = {os.path.relpath(path, discovery_root).replace(os.sep, "/") for path in files}
    if "docs/normal.md" not in names:
        failures.append(f"file discovery: a normal Markdown file was not found, got {sorted(names)}")

    behaviour += 1
    files, rejected = repo_files(discovery_root, (".yml",))
    names = {os.path.relpath(path, discovery_root).replace(os.sep, "/") for path in files}
    if ".github/ISSUE_TEMPLATE/forms.yml" not in names:
        failures.append(f"file discovery: a normal YAML file was not found, got {sorted(names)}")

    if symlink_cases:
        behaviour += 1
        files, rejected = repo_files(discovery_root, (".md",))
        names = {os.path.relpath(path, discovery_root).replace(os.sep, "/") for path in files}
        rejected_names = {name for name, _reason in rejected}
        if "external.md" in names:
            failures.append("file discovery: an external Markdown symlink entered the inventory")
        if "external.md" not in rejected_names:
            failures.append(
                f"file discovery: the external Markdown symlink was not reported, got {rejected}"
            )

        behaviour += 1
        files, rejected = repo_files(discovery_root, (".yml",))
        names = {os.path.relpath(path, discovery_root).replace(os.sep, "/") for path in files}
        rejected_names = {name for name, _reason in rejected}
        if "external.yml" in names:
            failures.append("file discovery: an external YAML symlink entered the inventory")
        if "external.yml" not in rejected_names:
            failures.append(
                f"file discovery: the external YAML symlink was not reported, got {rejected}"
            )

        behaviour += 1
        files, rejected = repo_files(discovery_root, (".md",))
        names = {os.path.relpath(path, discovery_root).replace(os.sep, "/") for path in files}
        if "internal.md" not in names:
            failures.append("file discovery: an internal Markdown symlink was not accepted")
        if "alias.md" not in names:
            failures.append("file discovery: a second internal symlink was not accepted")

        behaviour += 1
        files, rejected = repo_files(discovery_root, (".md",))
        rejected_names = {name for name, _reason in rejected}
        if "broken.md" not in rejected_names:
            failures.append(
                f"file discovery: a symlink with a missing target was not reported, got {rejected}"
            )

        behaviour += 1
        files, rejected = repo_files(discovery_root, (".md",))
        names = {os.path.relpath(path, discovery_root).replace(os.sep, "/") for path in files}
        if "linkdir/docs/normal.md" not in names:
            failures.append(
                "file discovery: a symlinked directory inside the repository was not followed, "
                f"got {sorted(names)}"
            )

        behaviour += 1
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

    behaviour += 1
    # The content behind an external symlink must never be read by the
    # validator. A file whose content would break YAML parsing proves it.
    outside_root = tempfile.mkdtemp()
    with open(os.path.join(outside_root, "poison.yml"), "w", encoding="utf-8") as handle:
        handle.write("name: POISON-MARKER\ndescription: [unclosed\n")
    discovery_root = make_temp_repo(files={"README.md": "# Root\n"})
    try:
        os.symlink(os.path.join(outside_root, "poison.yml"),
                    os.path.join(discovery_root, "poison.yml"))
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
        print("  skipped 1 external-content case(s): symbolic links are not available here")
    shutil.rmtree(discovery_root, ignore_errors=True)
    shutil.rmtree(outside_root, ignore_errors=True)

    # ------------------------------------------------------------------
    # Behaviour cases: the schema refresh is transactional.
    # ------------------------------------------------------------------
    good_downloads = {
        name: open(os.path.join(SCHEMA_SOURCE_DIR, name), "rb").read()
        for name in ("github-issue-forms.json", "github-issue-config.json")
    }
    for name in update_schemas.UPSTREAM_THIRD_PARTY:
        good_downloads[name] = b"placeholder"

    behaviour += 1
    broken = dict(good_downloads)
    broken["github-issue-forms.json"] = b"{ this is not json"
    try:
        update_schemas.build_artifacts(broken)
    except update_schemas.UpdateError:
        pass
    else:
        failures.append("schema refresh: invalid upstream JSON was accepted")

    behaviour += 1
    not_a_schema = dict(good_downloads)
    not_a_schema["github-issue-config.json"] = b'{"type": 12}'
    try:
        update_schemas.build_artifacts(not_a_schema)
    except update_schemas.UpdateError:
        pass
    else:
        failures.append("schema refresh: a document that is not a JSON Schema was accepted")

    behaviour += 1
    try:
        update_schemas.build_artifacts({"github-issue-forms.json": b"{}"})
    except update_schemas.UpdateError:
        pass
    else:
        failures.append("schema refresh: a missing download was accepted")

    behaviour += 1
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

    behaviour += 1
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
            with open(os.path.join(target_dir, name), "wb") as handle:
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
        behaviour += 1
        temp_root = make_temp_repo()
        try:
            artifacts = {f"f{i}.json": f'{{"v": {i}}}\n'.encode() for i in range(5)}
            target_dir = seed_target(temp_root, artifacts)
            staging = stage_for(temp_root, artifacts)
            original_replace, failing_replace = inject_promotion_failure(fail_at)
            os.replace = failing_replace
            try:
                update_schemas.promote(artifacts, staging, target_dir)
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
        behaviour += 1
        temp_root = make_temp_repo()
        try:
            artifacts = {f"f{i}.json": f'{{"v": {i}}}\n'.encode() for i in range(5)}
            target_dir = seed_target(temp_root, artifacts)
            staging = stage_for(temp_root, artifacts)
            backup_dir = os.path.join(target_dir, update_schemas.BACKUP_DIR_NAME)

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
                update_schemas.promote(artifacts, staging, target_dir)
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
                backup = os.path.join(backup_dir, name)
                if os.path.exists(backup):
                    survivors.append((name, backup))
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

    # A failure while removing the backups after a successful promotion is
    # reported but does not fail the promotion.
    behaviour += 1
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
            update_schemas.promote(artifacts, staging, target_dir)
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
    behaviour += 1
    temp_root = make_temp_repo()
    try:
        artifacts = {f"f{i}.json": f'{{"v": {i}}}\n'.encode() for i in range(3)}
        target_dir = seed_target(temp_root, artifacts)
        staging = stage_for(temp_root, artifacts)
        update_schemas.promote(artifacts, staging, target_dir)
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

    total = negative + positive + behaviour
    print(
        f"validate_docs tests: {negative} negative case(s), {positive} positive control(s), "
        f"and {behaviour} behaviour case(s) checked ({total} total)"
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
