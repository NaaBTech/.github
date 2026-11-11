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
| [`SUPPORT.md`](SUPPORT.md) | Default support guidance and escalation routing. |
| [`PULL_REQUEST_TEMPLATE.md`](PULL_REQUEST_TEMPLATE.md) | Default pull request template. |
| [`.github/ISSUE_TEMPLATE/bug_report.yml`](.github/ISSUE_TEMPLATE/bug_report.yml) | Default issue form for bug reports. |
| [`.github/ISSUE_TEMPLATE/feature_request.yml`](.github/ISSUE_TEMPLATE/feature_request.yml) | Default issue form for feature requests. |
| [`.github/ISSUE_TEMPLATE/config.yml`](.github/ISSUE_TEMPLATE/config.yml) | Default issue template chooser configuration. |
| [`.github/VULNERABILITY_REPORT.yml`](.github/VULNERABILITY_REPORT.yml) | Default private vulnerability report form. |

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
│   │   └── config.yml                 # Default issue template chooser
│   └── VULNERABILITY_REPORT.yml       # Default private vulnerability report form
├── CODE_OF_CONDUCT.md                 # Default code of conduct
├── CONTRIBUTING.md                    # Default contribution guidelines
├── PULL_REQUEST_TEMPLATE.md           # Default pull request template
├── SECURITY.md                        # Default security policy
├── SUPPORT.md                         # Default support guidance
└── README.md                          # This file
```

---

## How Organization Defaults Work

This repository is the organization's `.github` repository. GitHub serves the files here as **defaults** for every repository in the organization.

The rules are:

1. A default applies only when the target repository does **not** define its own file of the same type.
2. If a repository defines a valid `.github/ISSUE_TEMPLATE` folder of its own, **none** of the organization's default issue templates are used for that repository.
3. Files that can live in more than one location are resolved in this order: the repository's `.github` folder, then the repository root, then the repository's `docs` folder.
4. Defaults apply to repositories of any visibility.

A repository may therefore replace any default here with something more specific, and that is an intended use — not a deviation. Individual repositories are expected to define stricter rules where their technology, audience, or release process requires it.

> **Location note.** GitHub resolves default issue templates and the default funding and vulnerability-report files from the `.github` folder *inside* this repository, which is why they live under [`.github/`](.github) rather than in the root. Root-level files here are the defaults for the remaining community health file types.

---

## Maintaining These Files

- **Single source of truth.** These defaults are edited here and nowhere else. Individual repositories are not expected to copy them.
- **Consistent terminology.** Use "NaaB Tech" for the company, "NaaB Tech organization" for the GitHub organization, and `naabtech.ir` for the website. Keep the Persian brand name ناب تک to the organization profile and the root README.
- **No fabricated information.** Never add contact addresses, customer names, certifications, partnerships, response-time commitments, funding details, or project statistics that have not been confirmed. Where a value is genuinely required but not yet available, use a clearly marked placeholder and track it as an open item.
- **Repository-specific rules win.** A default must stay general enough to apply across different technologies. Anything that only makes sense for one repository belongs in that repository.
- **Change discipline.** Changes to these files follow the conventions in [`CONTRIBUTING.md`](CONTRIBUTING.md), including the branch naming and commit message conventions described there.

---

## Reference

- [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [Customizing your organization's profile](https://docs.github.com/en/organizations/collaborating-with-groups-in-organizations/customizing-your-organizations-profile)
- [Setting up your project for healthy contributions](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions)
- [Syntax for issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct.html)
