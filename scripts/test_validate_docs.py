#!/usr/bin/env python3
"""Negative tests for the documentation validator.

Every case below is an intentionally invalid document. The test asserts that
the validator reports an error for each one, so that a regression which
silently accepts a malformed form is caught.

The cases also pin the expected error text, so a change in the validator that
stops detecting a problem is visible.

Usage:
    python scripts/test_validate_docs.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_docs import (  # noqa: E402
    EXPECTED_LABELS,
    ISSUE_FORM_SCHEMA,
    VULNERABILITY_FORM_SCHEMA,
    parse_yaml_text,
    validate_config_document,
    validate_form_document,
)

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
    checked = 0

    # Valid documents must produce no errors at all.
    for name, kind, text in (
        ("valid issue form", "issue", VALID_ISSUE_FORM),
        ("valid vulnerability form", "vulnerability", VALID_VULNERABILITY_FORM),
    ):
        data, error = parse_yaml_text(text)
        checked += 1
        if error:
            failures.append(f"{name}: the fixture itself did not parse: {error}")
            continue
        schema = ISSUE_FORM_SCHEMA if kind == "issue" else VULNERABILITY_FORM_SCHEMA
        errors = validate_form_document(name, data, schema, EXPECTED_LABELS)
        if errors:
            failures.append(f"{name}: expected no errors, got {errors}")

    for name, kind, text, expected in FORM_CASES:
        checked += 1
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
        checked += 1
        data, error = parse_yaml_text(text)
        if error is None:
            failures.append(f"{name}: expected a YAML parse error, but the text parsed successfully")
        elif expected.lower() not in error.lower() and name == "malformed YAML":
            failures.append(f"{name}: expected the error to mention '{expected}', got '{error}'")

    for name, text, expected in CONFIG_CASES:
        checked += 1
        data, error = parse_yaml_text(text)
        if error:
            failures.append(f"{name}: the fixture itself did not parse: {error}")
            continue
        errors = validate_config_document(name, data)
        if not errors:
            failures.append(f"{name}: expected an error, but the validator reported none")
        elif not any(expected.lower() in message.lower() for message in errors):
            failures.append(f"{name}: expected an error containing '{expected}', got {errors}")

    print(f"validate_docs negative tests: {checked} case(s) checked")
    if failures:
        for failure in failures:
            print(f"  FAIL {failure}")
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("  all cases behaved as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
