# Security Policy

NaaB Tech builds and operates software and infrastructure. Security is a core part of the work, not an afterthought, and this policy describes how vulnerabilities in our software are reported, triaged, and resolved.

This policy is the organization-level default. An individual repository may include its own `SECURITY.md` with more specific guidance; where it exists, it takes precedence over this document for that repository.

---

## Scope

This policy applies to:

- Public repositories in the [NaaB Tech](https://github.com/NaaBTech) organization.
- Software, APIs, web applications, and infrastructure published or operated by NaaB Tech.
- Configuration, deployment artifacts, and documentation in those repositories.

It does **not** apply to:

- Third-party products and services. Report those to their own maintainers.
- Systems that are not operated by NaaB Tech. See [Security Research and Authorization](#security-research-and-authorization).
- NaaB Tech systems that are explicitly covered by a signed agreement with a customer. Contact the organization through the [official website](https://naabtech.ir) for those.

---

## Reporting a Vulnerability

**Do not open a public issue, pull request, or discussion for a security vulnerability.** A public report gives everyone — including attackers — a head start.

### Preferred: GitHub private vulnerability reporting

GitHub provides a private reporting channel for each repository. When it is enabled, use it:

1. Open the affected repository on GitHub.
2. Go to the **Security** tab.
3. Select **Report a vulnerability**.
4. Describe the issue and submit the report.

The report opens a private advisory that only you and the maintainers can see. You receive a reference for the advisory, which is how fixes and any public credit are tracked.

**Availability depends on repository configuration.** Private vulnerability reporting is enabled per repository by its maintainers, and it may not be enabled everywhere in the organization. If the **Report a vulnerability** option is not present on a repository, use one of the alternatives below. This policy does not promise that the option is available in every repository.

A private report form is provided at [.github/VULNERABILITY_REPORT.yml](.github/VULNERABILITY_REPORT.yml) and is used where the organization has enabled private reporting.

### Alternatives

If private reporting is not available for the repository in question:

- Use the contact channel on the [official website](https://naabtech.ir) and ask for the security team. Mark the message as containing a security report so that it is routed appropriately.
- For issues affecting several repositories, contact the organization owners through [github.com/NaaBTech](https://github.com/NaaBTech).

> **Open item.** NaaB Tech has not published a dedicated security contact address. Until one is designated, the channels above are the available routes. Publishing a monitored address such as `security@naabtech.ir` is an improvement this policy should adopt once the mailbox exists and is staffed.

### What to include

A complete report helps more than a long one. Please include:

| Information | Why it matters |
| --- | --- |
| **Affected repository** | The repository name, and the path or component within it if the issue is limited to one. |
| **Affected version** | The release tag, commit SHA, or deployment identifier where the issue was observed. For unreleased code, the commit SHA or branch. |
| **Description** | What the vulnerability is and what an attacker gains by exploiting it. |
| **Impact** | The concrete consequence — unauthorized access, data exposure, privilege escalation, service degradation, and so on. |
| **Steps to reproduce** | A minimal sequence of steps that a maintainer can follow to confirm the issue. |
| **Proof of concept** | Request code, a request/response pair, or a configuration excerpt. A proof of concept does not need to be weaponised, and should not contain real credentials or personal data. |
| **Suggested remediation** | If you have one. This is optional and does not affect how the report is triaged. |
| **Your contact details** | A way to reach you for follow-up questions. Only if you are comfortable sharing them. |

Redact credentials, tokens, private keys, and personal data from anything you attach.

### Triage and communication

Once a report is received:

- The report is reviewed to confirm the issue, reproduce it, and determine severity and affected versions.
- You are kept informed through the private advisory thread. That thread is the channel for clarification, remediation updates, and credit decisions.
- Reports are triaged in the order they are received.
- Reports that cannot be reproduced or are found not to affect NaaB Tech software are closed with an explanation.
- Credit is offered in the advisory or release notes if you want it, in the form you prefer, including anonymous credit.

> **No service-level commitment.** NaaB Tech does not publish response-time, triage-time, or remediation-time commitments for vulnerability reports. Nothing in this policy is a service-level agreement. If you require a guaranteed response window, that is a commercial arrangement — contact the organization through the [official website](https://naabtech.ir).

### Coordinated disclosure

The goal is a fix that is available before the details are public.

- NaaB Tech works with the reporter to agree on a disclosure timeline once the issue is confirmed and a fix or mitigation is in place.
- A remediation is prepared, a fix or mitigation is released, and the advisory is published — or the report is closed with the reporter's agreement.
- Where the issue affects widely used software, coordination with the relevant ecosystem may be necessary. That can extend the timeline, and the reason will be explained.
- Credit is provided as agreed.

**Do not publish the vulnerability before the disclosure is coordinated.** Publishing a proof of concept prematurely exposes every user of the affected software and gives attackers a ready-made tool. If you believe a coordinated timeline is not being honoured, contact the organization through the [official website](https://naabtech.ir) and ask for escalation.

---

## Rules of Engagement

The following are **not** permitted when researching a NaaB Tech system, even when a vulnerability is genuine:

- Accessing data that is not yours, or data that the reporter is not authorised to access.
- Accessing accounts, systems, or data belonging to other users or customers.
- Extracting, downloading, or retaining personal data, credentials, keys, or configuration beyond the minimum needed to demonstrate the issue.
- Introducing malware, or modifying data in a way that leaves the system in an altered state.
- Introducing denial-of-service conditions, including sustained load, resource exhaustion, and lockout of legitimate users.
- Destroying, corrupting, or deleting data, including test data, without written authorisation.
- Deceptive or destructive testing against shared infrastructure.
- Using social engineering, physical intrusion, or impersonation of staff, contractors, or users.
- Scanning, probing, or testing systems that are not owned or operated by NaaB Tech.
- Continuing to test after a vulnerability has been reported and remediation work has begun.

### Safe harbour

Good-faith research that follows this policy is authorised by NaaB Tech.

- NaaB Tech will not pursue legal action against anyone who follows these rules, including for activities that would otherwise breach a NaaB Tech acceptable-use or terms-of-service condition.
- NaaB Tech will not hold a reporter liable for damages arising from research conducted under this policy.
- This safe harbour covers research against NaaB Tech-owned and NaaB Tech-operated systems. It does not extend to third-party systems, and it does not cover activity that violates the rules of engagement above.

There is no bug bounty programme. Participation is voluntary and unpaid.

---

## Security Research and Authorization

**Researching a system is not the same as being authorised to test it.**

- Permission to *report* a vulnerability does not imply permission to *test* for one.
- Testing requires explicit authorisation from the owner of the system. For systems owned by a customer, that authorisation must come from the customer. NaaB Tech's involvement does not substitute for it.
- If you are unsure whether a system is in scope, or whether your activity is authorised, stop and ask through the [official website](https://naabtech.ir) before proceeding.
- Authorised penetration tests and security assessments are performed under a written agreement that defines scope, timing, and test methods. Requests for such work should go through the website.
- Port scanning, vulnerability scanning, and automated tooling against production systems are out of scope unless they are explicitly covered by an authorisation agreement.

When you are not sure whether something is permitted, treat it as prohibited until it is confirmed in writing.

---

## Reporting a Vulnerability in a Third-Party Component

If a NaaB Tech repository depends on a vulnerable third-party project, report it to that project's maintainers through its own disclosure process. Reporting it privately to NaaB Tech as well is welcome — it helps us plan an upgrade or mitigation — but the fix has to come from the upstream project.

Please do not open a public issue in a NaaB Tech repository to report an upstream vulnerability.

---

## Related Documentation

- [Contributing guidelines](CONTRIBUTING.md) — how to report a non-security defect and propose a change.
- [Support guidance](SUPPORT.md) — where to ask questions that are not security reports.
- [Code of Conduct](CODE_OF_CONDUCT.md) — expectations for interaction in NaaB Tech spaces.
- [GitHub: Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [GitHub: Reporting a vulnerability privately](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately)
- [GitHub: Coordinated disclosure of security vulnerabilities](https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/coordinated-disclosure)
