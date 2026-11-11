#!/usr/bin/env python3
"""Refresh the vendored JSON Schemas used to validate GitHub forms.

This script is a MAINTENANCE tool. It is not run by CI, because CI must not
depend on network access. Run it manually when the upstream schemas change:

    python scripts/update_schemas.py

It downloads the upstream schemas from SchemaStore, applies the documented
patch described in schemas/README.md, writes them into schemas/, and then
regenerates the private vulnerability reporting form schema from the patched
issue forms schema.
"""

import datetime
import hashlib
import json
import os
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "schemas")

UPSTREAM = {
    "github-issue-forms.json": "https://www.schemastore.org/github-issue-forms.json",
    "github-issue-config.json": "https://www.schemastore.org/github-issue-config.json",
}

# Element types GitHub supports in a private vulnerability reporting form.
# https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository
VULNERABILITY_TYPES = ["checkboxes", "dropdown", "input", "markdown", "textarea"]

# Top-level keys GitHub accepts in a private vulnerability reporting form.
VULNERABILITY_TOP_LEVEL = ["name", "description", "body"]

# GitHub's documentation lists `min_length` as a valid validation for `input`
# and `textarea`. The upstream SchemaStore schema only lists `required`, so a
# documented, valid form would be rejected. schemas/README.md records this.
PATCH_NOTE = "min_length added for input and textarea per GitHub's form schema documentation"


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "naabtech-docs-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def write_json(name, data):
    path = os.path.join(SCHEMA_DIR, name)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")
    print(f"wrote schemas/{name}")


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path):
    with open(path, "rb") as handle:
        return sha256_bytes(handle.read())


def apply_min_length_patch(schema):
    """Add `min_length` to the input and textarea validations."""
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
        raise SystemExit(f"expected to patch 2 validations blocks, patched {patched}")
    return schema


def derive_vulnerability_schema(issue_forms_schema):
    """Restrict the issue forms schema to the vulnerability reporting form rules."""
    schema = json.loads(json.dumps(issue_forms_schema))
    schema["$id"] = "https://naabtech.ir/schemas/github-vulnerability-report-form.json"
    schema["title"] = "GitHub private vulnerability reporting form schema"
    schema["$comment"] = (
        "Derived from github-issue-forms.json by restricting the element types and "
        "top-level keys that GitHub supports for private vulnerability reporting "
        "forms. Regenerate with scripts/update_schemas.py. See schemas/README.md."
    )

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
        raise SystemExit(f"expected {len(VULNERABILITY_TYPES)} element branches, kept {len(kept)}")
    definitions["form_item"]["allOf"] = kept

    schema["properties"] = {k: v for k, v in schema["properties"].items() if k in VULNERABILITY_TOP_LEVEL}
    schema["required"] = ["name", "description", "body"]
    return schema


def main():
    os.makedirs(SCHEMA_DIR, exist_ok=True)
    issue_forms = None
    provenance = {
        "retrieved_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "https://www.schemastore.org/",
        "schemas": {},
    }
    for name, url in UPSTREAM.items():
        print(f"fetching {url}")
        raw = download(url).encode("utf-8")
        data = json.loads(raw.decode("utf-8"))
        if name == "github-issue-forms.json":
            data = apply_min_length_patch(data)
            issue_forms = data
        write_json(name, data)
        provenance["schemas"][name] = {
            "upstream_url": url,
            "upstream_sha256": sha256_bytes(raw),
            "vendored_sha256": sha256_file(os.path.join(SCHEMA_DIR, name)),
            "patched": name == "github-issue-forms.json",
        }

    if issue_forms is None:
        raise SystemExit("issue forms schema was not fetched")
    derived_name = "github-vulnerability-report-form.json"
    write_json(derived_name, derive_vulnerability_schema(issue_forms))
    provenance["schemas"][derived_name] = {
        "derived_from": "github-issue-forms.json",
        "upstream_url": "https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository",
        "vendored_sha256": sha256_file(os.path.join(SCHEMA_DIR, derived_name)),
        "patched": False,
        "derived": True,
    }

    write_json("PROVENANCE.json", provenance)
    print("\nSchemas updated. Review schemas/README.md and re-run the validation tests.")


if __name__ == "__main__":
    sys.exit(main())
