# NaaB Tech — Organization Resources

This repository holds the organization-wide resources for the [NaaB Tech](https://github.com/NaaBTech) GitHub organization:

- The **organization profile** shown on [github.com/NaaBTech](https://github.com/NaaBTech).
- **Default community health files** — contribution guidelines, code of conduct, security policy, support guidance, issue forms, and a pull request template that apply across the organization's repositories.
- The **repository layout** and conventions used for these files, so they stay consistent as the organization grows.

Nothing here is application code. It is documentation and configuration, maintained so that every NaaB Tech repository starts from the same baseline.

---

## Contents

| File | Purpose |
| --- | --- |
| [`profile/README.md`](profile/README.md) | Organization profile. Rendered on the organization page on GitHub. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Default contribution guidelines for all organization repositories. |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) | Default code of conduct, based on the Contributor Covenant v2.1. |
| [`SECURITY.md`](SECURITY.md) | Default security policy and vulnerability disclosure process. |
| [`SUPPORT.md`](SUPPORT.md) | Default support guidance and channel routing. |
| [`PULL_REQUEST_TEMPLATE.md`](PULL_REQUEST_TEMPLATE.md) | Default pull request template. |
| [`REPOSITORY_ONBOARDING.md`](REPOSITORY_ONBOARDING.md) | Checklist for preparing and maintaining a repository. |
| [`.github/ISSUE_TEMPLATE/bug_report.yml`](.github/ISSUE_TEMPLATE/bug_report.yml) | Default issue form: bug report. |
| [`.github/ISSUE_TEMPLATE/feature_request.yml`](.github/ISSUE_TEMPLATE/feature_request.yml) | Default issue form: feature request. |
| [`.github/ISSUE_TEMPLATE/question.yml`](.github/ISSUE_TEMPLATE/question.yml) | Default issue form: question. |
| [`.github/ISSUE_TEMPLATE/config.yml`](.github/ISSUE_TEMPLATE/config.yml) | Default issue template chooser configuration. |
| [`.github/VULNERABILITY_REPORT.yml`](.github/VULNERABILITY_REPORT.yml) | Default private vulnerability report form. |
| [`schemas/README.md`](schemas/README.md) | Where the JSON Schemas come from, how they are licensed, and how to refresh them. |

---

## Repository Layout

```text
.github/
├── profile/
│   └── README.md                      # Organization profile
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml             # Default issue form: bug report
│   │   ├── feature_request.yml        # Default issue form: feature request
│   │   ├── question.yml               # Default issue form: question
│   │   └── config.yml                 # Default issue template chooser
│   ├── VULNERABILITY_REPORT.yml       # Default private vulnerability report form
│   └── workflows/
│       └── validate-docs.yml          # Validation workflow for this repository
├── CODE_OF_CONDUCT.md                 # Default code of conduct
├── CONTRIBUTING.md                    # Default contribution guidelines
├── PULL_REQUEST_TEMPLATE.md           # Default pull request template
├── SECURITY.md                        # Default security policy
├── SUPPORT.md                         # Default support guidance
├── README.md                          # This file
├── REPOSITORY_ONBOARDING.md           # Repository setup and maintenance checklist
├── schemas/
│   ├── github-issue-forms.json        # Vendored JSON Schema for issue forms
│   ├── github-issue-config.json       # Vendored JSON Schema for the chooser
│   ├── github-vulnerability-report-form.json
│   │                                   # Derived schema for vulnerability forms
│   ├── PROVENANCE.json                # Where each schema came from, and when
│   └── README.md                      # Schema sources, licensing, and maintenance
├── scripts/
│   ├── validate_docs.py               # File, form, and link validation
│   ├── test_validate_docs.py          # Validator tests: negative cases and positive controls
│   └── update_schemas.py              # Refreshes the vendored schemas
├── .gitattributes                     # Normalises line endings to LF
├── .gitignore                         # Ignores Python bytecode and node_modules
├── .markdownlint.json                 # markdownlint configuration
├── .markdownlintignore                # Paths excluded from markdownlint
├── .yamllint.yml                      # yamllint configuration
├── package.json                       # Node tooling declaration
├── package-lock.json                  # Pinned Node dependency tree
└── requirements-docs.txt              # Pinned Python tooling
```

### Which files are inherited

Not every file in this repository applies to other organization repositories. There are four distinct groups:

| Group | Files | Applies to |
| --- | --- | --- |
| **Organization defaults** | `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`, `.github/VULNERABILITY_REPORT.yml` | Every organization repository that does not define its own file of the same type |
| **Organization profile** | `profile/README.md` | The organization page on GitHub only |
| **This repository only** | `README.md`, `REPOSITORY_ONBOARDING.md`, `.github/workflows/`, `schemas/`, `scripts/`, and the tool configuration files | The `NaaBTech/.github` repository only |
| **Settings, not files** | Labels, private vulnerability reporting, branch protection, rulesets, code scanning, and Dependabot | Configured in GitHub, per repository or per organization |

`README.md` at the root of this repository is the readme for **this** repository. It is not a community health file and is not inherited by other repositories. `REPOSITORY_ONBOARDING.md` is a maintainer guide for this repository; GitHub has no mechanism for inheriting it.

**Workflows are not organization defaults.** GitHub inherits community health files between repositories; it does not inherit workflow files. The `validate-docs.yml` workflow runs only in `NaaBTech/.github`. Every project that needs CI has its own workflow in its own `.github/workflows/` directory — see [REPOSITORY_ONBOARDING.md](REPOSITORY_ONBOARDING.md).

---

## How Organization Defaults Work

This repository is the organization's `.github` repository. GitHub serves the files here as **defaults** for the organization's repositories.

The rules are:

1. A default applies only when the target repository does **not** define its own file of the same type. A repository's own file always wins.
2. If a repository defines a valid `.github/ISSUE_TEMPLATE` folder of its own, **none** of the organization's default issue templates are used for that repository.
3. Files that can live in more than one location are resolved in this order: the repository's `.github` folder, then the repository root, then the repository's `docs` folder.
4. Defaults apply to the organization's repositories regardless of their visibility.
5. **Defaults are not copied into the target repository.** They are served by GitHub when the page is requested. They do not appear in the target repository's Git history, in a clone, in a package, or in a download.

A repository may therefore replace any default here with something more specific, and that is an intended use — not a deviation. Individual repositories are expected to define stricter rules where their technology, audience, or release process requires it.

> **Location note.** GitHub resolves default issue templates, the default funding file, and the default vulnerability-report file from the `.github` folder *inside* this repository, which is why they live under [`.github/`](.github) rather than in the root. Root-level files here are the defaults for the remaining community health file types.

### What a default does not do

Defaults supply guidance and templates. They do not:

- Add configuration, code, or settings to a repository.
- Enable a repository setting, such as private vulnerability reporting, branch protection, or code scanning.
- Create labels in a repository. See [Label Requirements](#label-requirements).

---

## Label Requirements

The default issue forms apply labels automatically: `bug`, `enhancement`, and `question`.

**GitHub applies a label only if a label with that name already exists in the destination repository.** A label created in this repository does not propagate to other repositories.

Two things are therefore required for automatic labelling to work:

1. **The label must exist in the destination repository.** It is present in this repository, because the default forms live here.
2. **New repositories need the labels up front.** Organization owners can configure default labels under **Organization Settings → Repository → General → Repository labels**. Default labels are included in **newly created repositories only** — adding, editing, or deleting an organization default label does not add, edit, or delete that label in existing repositories.

Existing repositories in the organization therefore need `bug`, `enhancement`, and `question` created in them, or the forms will be submitted without a label. That is a repository-level action, performed by a maintainer of each repository. The checklist in [`REPOSITORY_ONBOARDING.md`](REPOSITORY_ONBOARDING.md) covers it.

---

## Officially Published Channels

These are the channels NaaB Tech publishes on its GitHub organization profile. They are the only contact details that may be referenced in these files.

| Channel | Link |
| --- | --- |
| Website | [naabtech.ir](https://naabtech.ir) |
| Email | [info@naabtech.ir](mailto:info@naabtech.ir) |
| GitHub Organization | [github.com/NaaBTech](https://github.com/NaaBTech) |
| LinkedIn | [company/naabtech](https://linkedin.com/company/naabtech) |
| X | [@naabtech](https://x.com/naabtech) |
| Telegram | [t.me/NaaBTech](https://t.me/NaaBTech) |
| Instagram | [@naabtech.ir](https://instagram.com/naabtech.ir) |

Three separate things are worth distinguishing:

- **Officially published** — the channel appears in NaaB Tech's GitHub organization profile. It is a sanctioned contact route.
- **Responding** — the URL currently returns a successful response. This is a transient technical condition and says nothing about whether the channel is maintained.
- **Actively maintained** — someone is actively posting to or answering on the channel. This cannot be inferred from a published URL, and is not claimed for any channel listed above.

A channel is listed here because it is officially published, not because it responded when this file was last edited. A temporary server error does not make an official channel invalid, and a channel that stops responding remains an official route until the organization owners say otherwise.

Anything not on this list must be confirmed with the organization owners before it is added to a document.

---

## License

**This repository has no license file, and that is an open decision for the organization owners.**

GitHub does not use an organization's `.github` repository as the source of a default license for other projects, so each software project needs its own license. That is a separate matter from licensing the contents of *this* repository — its documentation, the Python scripts, and the vendored schemas.

- Until a license is chosen, the contents of this repository are **not** licensed for reuse. The public visibility of the repository does not grant permission to copy or redistribute it.
- The two vendored upstream schemas are redistributed under the **Apache-2.0** license of the [SchemaStore](https://github.com/SchemaStore/schemastore) repository. See [`schemas/README.md`](schemas/README.md) and `schemas/PROVENANCE.json` for the attribution and hashes.
- `github-vulnerability-report-form.json` is derived in this repository from one of those upstream schemas and is covered by the same terms.

Selecting a license for this repository requires the owners' approval and, where appropriate, legal review.

---

## Maintaining These Files

- **Single source of truth.** These defaults are edited here and nowhere else. Individual repositories are not expected to copy them.
- **Consistent terminology.** Use "NaaB Tech" for the company, "NaaB Tech organization" for the GitHub organization, and `naabtech.ir` for the website. Keep the Persian brand name ناب تک to the organization profile and the root README.
- **No fabricated information.** Never add contact addresses, customer names, certifications, partnerships, response-time commitments, funding details, or project statistics that have not been confirmed. Use only the channels in [Officially Published Channels](#officially-published-channels). Where a value is genuinely required but not yet available, use a clearly marked placeholder and track it as an open item.
- **No unapproved legal commitments.** Safe-harbour provisions, immunity, indemnification, response-time guarantees, and bug bounty terms are business and legal decisions. They require the organization owners' approval and, where appropriate, legal review before they are written into these files.
- **Repository-specific rules win.** A default must stay general enough to apply across different technologies. Anything that only makes sense for one repository belongs in that repository.
- **Change discipline.** Changes to these files follow the conventions in [`CONTRIBUTING.md`](CONTRIBUTING.md), including the branch naming and commit message conventions described there.
- **Validate before merging.** The `Validate documentation` workflow checks YAML syntax, the GitHub form schemas, required file naming, and internal links on every pull request. The validation itself reads only files in this repository, so a third-party website outage cannot fail a documentation change. Installing the tooling still needs access to the Python and npm package registries, so a registry outage can prevent the workflow from completing setup. Run the same checks locally:

  ```bash
  python -m pip install --requirement requirements-docs.txt
  npm ci
  python scripts/validate_docs.py .
  python scripts/test_validate_docs.py
  yamllint --strict --config-file .yamllint.yml .
  npx --no-install markdownlint --config .markdownlint.json "**/*.md"
  ```

  The Python dependencies are pinned in `requirements-docs.txt` and the Node dependency tree is pinned in `package-lock.json`, so a local run and the CI run use the same versions.

---

## Reference

- [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [Customizing your organization's profile](https://docs.github.com/en/organizations/collaborating-with-groups-in-organizations/customizing-your-organizations-profile)
- [Setting up your project for healthy contributions](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions)
- [Syntax for issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [Managing default labels for repositories in your organization](https://docs.github.com/en/organizations/managing-organization-settings/managing-default-labels-for-repositories-in-your-organization)
- [Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct.html)
