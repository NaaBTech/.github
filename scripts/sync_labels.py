#!/usr/bin/env python3
"""Synchronize standard labels across NaaB Tech repositories.

The default issue forms in NaaBTech/.github apply 'bug', 'enhancement',
and 'question'. GitHub applies a label only if it already exists in the
destination repository.

This tool helps organization maintainers audit or create the standard label
set in any NaaB Tech repository using either GitHub API or the GitHub CLI (gh).

Usage:
    python scripts/sync_labels.py --dry-run
    python scripts/sync_labels.py --repo NaaBTech/<repository> --token <token>
    python scripts/sync_labels.py --export-gh
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

# The standard NaaB Tech label set: (name, color, description)
STANDARD_LABELS = [
    {
        "name": "bug",
        "color": "d73a4a",
        "description": "Something is not working or behaving as documented.",
    },
    {
        "name": "enhancement",
        "color": "a2eeef",
        "description": "New feature request or improvement to existing functionality.",
    },
    {
        "name": "question",
        "color": "d876e3",
        "description": "Usage questions, configuration help, or general inquiry.",
    },
    {
        "name": "documentation",
        "color": "0075ca",
        "description": "Improvements or additions to documentation and guides.",
    },
    {
        "name": "security",
        "color": "e11d48",
        "description": "Security improvement, hardening, or advisory remediation.",
    },
    {
        "name": "dependencies",
        "color": "0366d6",
        "description": "Pull requests that update dependency files or tooling.",
    },
]


def export_gh_commands(repo=None):
    """Output gh CLI commands to create the standard labels."""
    target = f" --repo {repo}" if repo else ""
    lines = [f"# Standard labels for NaaB Tech repositories{target}"]
    for label in STANDARD_LABELS:
        name = label["name"]
        color = label["color"]
        desc = label["description"]
        lines.append(
            f'gh label create "{name}" --color "{color}" --description "{desc}" --force{target}'
        )
    return "\n".join(lines)


def sync_api(repo, token, dry_run=False):
    """Create or update labels via GitHub REST API."""
    if dry_run:
        print(f"[dry-run] Would sync {len(STANDARD_LABELS)} standard labels to {repo}:")
        for label in STANDARD_LABELS:
            print(f"  - {label['name']} (#{label['color']}): {label['description']}")
        return 0

    if not token:
        sys.stderr.write(
            "error: a GitHub personal access token (--token) is required to apply labels.\n"
        )
        return 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "NaaBTech-Label-Sync",
    }

    url = f"https://api.github.com/repos/{repo}/labels"
    success = 0
    for label in STANDARD_LABELS:
        payload = json.dumps(label).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status in (200, 201):
                    print(f"created: {label['name']}")
                    success += 1
        except urllib.error.HTTPError as exc:
            if exc.code == 422:
                # Label already exists; update it via PATCH.
                patch_url = f"{url}/{label['name']}"
                patch_req = urllib.request.Request(
                    patch_url, data=payload, headers=headers, method="PATCH"
                )
                try:
                    with urllib.request.urlopen(patch_req) as patch_resp:
                        if patch_resp.status == 200:
                            print(f"updated: {label['name']}")
                            success += 1
                except urllib.error.HTTPError as patch_exc:
                    sys.stderr.write(f"failed to update {label['name']}: {patch_exc}\n")
            else:
                sys.stderr.write(f"failed to create {label['name']}: {exc}\n")

    print(f"\nSynced {success}/{len(STANDARD_LABELS)} labels to {repo}.")
    return 0 if success == len(STANDARD_LABELS) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Audit and synchronize standard labels across NaaB Tech repositories."
    )
    parser.add_argument(
        "--repo",
        default="NaaBTech/.github",
        help="Target repository (e.g. NaaBTech/my-project). Defaults to NaaBTech/.github.",
    )
    parser.add_argument(
        "--token",
        help="GitHub personal access token with repository admin or write permissions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview standard labels without making API calls.",
    )
    parser.add_argument(
        "--export-gh",
        action="store_true",
        help="Print equivalent 'gh label create' commands.",
    )

    args = parser.parse_args()

    if args.export_gh:
        print(export_gh_commands(args.repo))
        return 0

    return sync_api(args.repo, args.token, dry_run=args.dry_run or not args.token)


if __name__ == "__main__":
    sys.exit(main())
