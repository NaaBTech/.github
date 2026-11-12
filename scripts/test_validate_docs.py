#!/usr/bin/env python3
"""Negative and positive tests for the documentation validator.

The suite contains two kinds of case:

- **Negative cases** — intentionally invalid documents. The validator must
  report an error for each one, so that a regression which silently accepts a
  malformed form is caught. There are 20 of these.
- **Positive control cases** — valid documents. The validator must report no
  errors at all for these, so that the checks cannot become so strict that
  they reject a good form. There are 2 of these.

That is 22 cases in total. The expected error text is pinned for each
negative case, so a change in the validator that stops detecting a problem is
visible.

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
    VULNERABILITY_FORM_SCHEMA,
    boolean_key_errors,
    parse_yaml_text,
    resolve_within,
    run_checks,
    validate_config_document,
    validate_form_document,
)

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
]


def run():
    failures = []
    positive = 0
    negative = 0

    # Positive control cases: valid documents must produce no errors at all.
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
        failures.append(
            "workflow with an 'on:' key: the fixture no longer exercises a boolean key"
        )

    # A link target that leaves the repository must be rejected.
    positive += 1
    repo_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    if resolve_within(repo_root, "../../../../Windows/win.ini") is not None:
        failures.append("link escaping the repository: expected the target to be rejected")
    if resolve_within(repo_root, "CONTRIBUTING.md") is None:
        failures.append("link inside the repository: expected the target to be accepted")

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
        elif expected.lower() not in error.lower() and name == "malformed YAML":
            failures.append(f"{name}: expected the error to mention '{expected}', got '{error}'")

    for name, text, expected in CONFIG_CASES:
        negative += 1
        data, error = parse_yaml_text(text)
        if error:
            failures.append(f"{name}: the fixture itself did not parse: {error}")
            continue
        errors = validate_config_document(name, data)
        if not errors:
            failures.append(f"{name}: expected an error, but the validator reported none")
        elif not any(expected.lower() in message.lower() for message in errors):
            failures.append(f"{name}: expected an error containing '{expected}', got {errors}")

    # The warning tier: a Markdown file that nothing links to is reported as a
    # warning, and a warning alone must not be reported as an error. The same
    # temporary repository also carries a workflow whose `on:` key YAML parses
    # as a boolean, which must not be reported at all.
    positive += 1
    with tempfile.TemporaryDirectory() as temp_root:
        os.makedirs(os.path.join(temp_root, "schemas"))
        os.makedirs(os.path.join(temp_root, ".github", "workflows"))
        for schema_name in (
            "github-issue-forms.json",
            "github-vulnerability-report-form.json",
            "github-issue-config.json",
        ):
            shutil.copy(
                os.path.join(SCHEMA_SOURCE_DIR, schema_name),
                os.path.join(temp_root, "schemas", schema_name),
            )
        with open(os.path.join(temp_root, "README.md"), "w", encoding="utf-8") as handle:
            handle.write("# Temporary repository\n")
        with open(os.path.join(temp_root, "orphan.md"), "w", encoding="utf-8") as handle:
            handle.write("# Orphan document\n")
        with open(
            os.path.join(temp_root, ".github", "workflows", "example.yml"), "w", encoding="utf-8"
        ) as handle:
            handle.write(WORKFLOW_WITH_ON_KEY)

        errors, warnings = run_checks(temp_root)

        if not any("orphan.md" in message for message in warnings):
            failures.append(
                "orphan Markdown file: expected a warning, got warnings "
                f"{warnings} and errors {errors}"
            )
        if any("orphan.md" in message for message in errors):
            failures.append(
                "orphan Markdown file: expected a warning only, but it was also reported as an error"
            )
        workflow_errors = [
            message for message in errors if "example.yml" in message
        ]
        if workflow_errors:
            failures.append(
                "workflow with an 'on:' key: expected no errors, got " f"{workflow_errors}"
            )

    total = negative + positive
    print(
        f"validate_docs tests: {negative} negative case(s) and {positive} positive control(s) "
        f"checked ({total} total)"
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
