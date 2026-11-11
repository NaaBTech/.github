# Support

This document explains where to ask a question, how to report a problem, and what to expect from each channel.

NaaB Tech operates in two clearly separate modes of support:

- **Community support** — free, best-effort help from maintainers and other contributors in public repositories. There is no response-time commitment.
- **Commercial support and business inquiries** — contracted support, engagement scoping, and partnership enquiries, arranged through the [official website](https://naabtech.ir).

This is the organization-level default. A repository may define its own support channels in its `SUPPORT.md` or `README`; where it does, those channels take precedence.

---

## Choose the Right Channel

| You want to | Go to |
| --- | --- |
| Report a defect | An **issue** in the affected repository, using the **Bug report** form |
| Request a feature or propose a change | An **issue** in the affected repository, using the **Feature request** form |
| Ask a general question | **Discussions** in the repository, if it is enabled; otherwise an issue with the `question` label |
| Report a security vulnerability | **Not** a public issue — follow [SECURITY.md](SECURITY.md) |
| Discuss an idea before writing code | An issue, or **Discussions** if it is enabled |
| Report abusive behaviour | See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Request a service, quote, or contract | The [official website](https://naabtech.ir) or [info@naabtech.ir](mailto:info@naabtech.ir) |

---

## Reporting a Bug

Open an issue in the repository where the problem occurs and use the **Bug report** form. Include the affected version, the environment, the steps to reproduce, the expected result, the actual result, and any relevant logs with secrets removed.

If the same problem has already been reported, add your details to the existing issue instead of opening a duplicate.

Before you report a defect that may be a configuration or environment problem, confirm that you have reproduced it with a clean setup where possible. That shortens triage considerably.

---

## Requesting a Feature

Open an issue using the **Feature request** form. Describe the problem the feature would solve before describing the solution — that is what makes a request actionable even if the implementation differs from what you had in mind.

Repository maintainers assess requests against the project's direction, maintenance capacity, and roadmap. A request being discussed does not imply it will be implemented.

---

## Asking Questions

**Discussions**, where the repository has them enabled, are the right place for open-ended questions: usage questions, conceptual questions, and ideas that have not yet become a concrete proposal. If a repository shows a **Discussions** tab in its header, it is enabled — check there first.

If Discussions are not enabled for a repository, use the issue tracker instead. Open an issue, choose the option closest to your request, and explain the question in the body. Keep one topic per issue.

Maintainers answer questions on a best-effort basis. They may close a question with an answer, convert it into a feature discussion, or redirect you to existing documentation.

---

## Reporting a Security Vulnerability

Security vulnerabilities are **never** reported through a public issue, pull request, or discussion.

Use GitHub's private vulnerability reporting — the **Security** tab → **Report a vulnerability** — where it is enabled for the repository. Availability depends on how each repository is configured, so the option may not be present everywhere.

If it is not available, email [info@naabtech.ir](mailto:info@naabtech.ir) with the subject line `Security report — <repository>`, or follow the other routes in [SECURITY.md](SECURITY.md). Before you publish anything publicly, allow time for the report to be reviewed and a fix to be prepared.

---

## Finding Documentation

| Looking for | Where to look |
| --- | --- |
| How to install, configure, or use a project | The repository's `README.md` and any `docs/` directory |
| How a project is developed and released | The repository's `CONTRIBUTING.md` and release notes |
| Organization-level standards | [The `.github` repository](https://github.com/NaaBTech/.github) |
| Security posture and disclosure process | [SECURITY.md](SECURITY.md) |
| Community expectations | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Product and service information | The [official website](https://naabtech.ir) |

Documentation for a specific project lives with that project. If a repository's documentation is missing or out of date, that is itself a contribution opportunity — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Commercial Support and Business Inquiries

Support that is contracted — including guaranteed response windows, dedicated engineering time, and service-level terms — is not provided through GitHub. Those requests are handled through the [official website](https://naabtech.ir) or by email to [info@naabtech.ir](mailto:info@naabtech.ir).

The same channels are used for enquiries about cybersecurity, software engineering, networking, and infrastructure services, and for partnership discussions. Providing details about your situation there makes the response more useful.

NaaB Tech's published channels are:

| Channel | Link |
| --- | --- |
| Website | [naabtech.ir](https://naabtech.ir) |
| Email | [info@naabtech.ir](mailto:info@naabtech.ir) |
| LinkedIn | [company/naabtech](https://linkedin.com/company/naabtech) |
| X | [@naabtech](https://x.com/naabtech) |
| Telegram | [t.me/NaaBTech](https://t.me/NaaBTech) |
| Instagram | [@naabtech.ir](https://instagram.com/naabtech.ir) |
| GitHub | [github.com/NaaBTech](https://github.com/NaaBTech) |

Public messaging channels are useful for questions that do not need confidentiality. They are not the right channel for a vulnerability report, and not a substitute for a support agreement.
