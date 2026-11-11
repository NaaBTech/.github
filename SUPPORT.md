# Support

This document explains where to ask a question, how to report a problem, and what to expect from each channel.

Two separate modes of support:

- **Community support** — free, best-effort help from the NaaB Tech maintainers and other contributors. There is no response-time commitment.
- **Business and service inquiries** — questions about working with NaaB Tech, sent through the official channels listed at the end of this document. Any contractual support arrangement is agreed separately and in writing; nothing in this repository constitutes such an arrangement.

This is the organization-level default. A repository may define its own support channels in its `SUPPORT.md` or `README`; where it does, those channels take precedence.

---

## Choose the Right Channel

| You want to | Go to |
| --- | --- |
| Report a defect | An **issue** in the affected repository, using the **Bug report** form |
| Request a feature or propose a change | An **issue** in the affected repository, using the **Feature request** form |
| Ask a question about using or configuring a project | An **issue** using the **Question** form, or **Discussions** where the repository has them enabled |
| Report a security vulnerability | **Not** a public issue — follow [SECURITY.md](SECURITY.md) |
| Discuss an idea before writing code | An issue, or **Discussions** if it is enabled |
| Report abusive behavior | See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Make a business or service inquiry | The official channels listed under [Business and Service Inquiries](#business-and-service-inquiries) |

Blank issues are not accepted from contributors — please use one of the forms. Maintainers of a repository can still open a blank issue.

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

A question is not a bug report. If something does not behave as documented, use the **Bug report** form; if you want something new, use the **Feature request** form. Use a question for anything else — how to configure something, what an option means, or how to achieve a result.

**Discussions**, where the repository has them enabled, are the right place for open-ended conversation: usage questions, conceptual questions, and ideas that have not yet become a concrete proposal. If a repository shows a **Discussions** tab in its header, it is enabled — check there first.

If Discussions are not enabled for a repository, use the **Question** form instead. It asks for the question, what you are trying to accomplish, what you have already tried, and any relevant references. Keep one topic per issue.

Questions are answered on a best-effort basis. A maintainer may answer directly, close the question with an answer, convert it into a feature discussion, or point you to existing documentation.

---

## Reporting a Security Vulnerability

Security vulnerabilities are **never** reported through a public issue, pull request, or discussion — including a Discussion. A public report gives everyone, including attackers, a head start.

Use GitHub's private vulnerability reporting — the **Security** tab → **Report a vulnerability** — where it is enabled for the repository. The feature is available for **public repositories**, and only where it has been enabled for that repository, so the option may not be present everywhere.

If it is not available, email **[info@naabtech.ir](mailto:info@naabtech.ir)** with the subject line `Security report — <repository>`, and follow the other routes in [SECURITY.md](SECURITY.md).

Do not include customer data, credentials, tokens, or other confidential material in a public issue, a discussion, or a support channel. Before publishing anything publicly, allow time for the report to be reviewed and a fix to be prepared.

---

## Finding Documentation

| Looking for | Where to look |
| --- | --- |
| How to install, configure, or use a project | The repository's `README.md` and any `docs/` directory |
| How a project is developed and released | The repository's `CONTRIBUTING.md` and release notes |
| Organization-level standards | [The `.github` repository](https://github.com/NaaBTech/.github) |
| Security posture and disclosure process | [SECURITY.md](SECURITY.md) |
| Community expectations | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| How a new repository is set up | [REPOSITORY_ONBOARDING.md](REPOSITORY_ONBOARDING.md) |
| Product and service information | The [official website](https://naabtech.ir) |

Documentation for a specific project lives with that project. If a repository's documentation is missing or out of date, that is itself a contribution opportunity — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Business and Service Inquiries

Questions about NaaB Tech's cybersecurity, software engineering, networking, and infrastructure work, and about working with the company, can be sent to **[info@naabtech.ir](mailto:info@naabtech.ir)** or through the [official website](https://naabtech.ir). Providing details about your situation makes the response more useful.

NaaB Tech's officially published channels are listed in the [organization repository](https://github.com/NaaBTech/.github/blob/main/README.md#officially-published-channels). A channel appearing there means it is published by the company — it does not guarantee a response time or that the account is actively monitored.

Community support is provided on a best-effort basis by maintainers and contributors. NaaB Tech publishes no response-time or service-level commitment for community support, and does not operate a staffed support desk. Where a contractual support arrangement is required, it is agreed separately and in writing.

Public messaging channels are useful for questions that do not need confidentiality. They are **not** the right channel for a vulnerability report, and they are not a substitute for a support agreement. Never send customer data, credentials, or other confidential material to a public channel.
