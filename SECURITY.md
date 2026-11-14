# Security Policy

NaaB Tech builds and operates software and infrastructure. This policy explains how to report a vulnerability in that software, how a report is handled, and — separately — what authorization is required before any system is tested.

This policy is the organization-level default. An individual repository may include its own `SECURITY.md` with more specific guidance; where it exists, it takes precedence over this document for that repository.

---

## Scope

This policy applies to:

- Software, APIs, web applications, infrastructure, configuration, and documentation published in NaaB Tech repositories, of any visibility.
- Systems operated by NaaB Tech.

It does **not** apply to:

- Third-party products and services. Report those to their own maintainers.
- Systems that NaaB Tech does not own or operate. See [Authorization and Permissions](#authorization-and-permissions).
- Systems covered by a signed agreement with a customer. Contact the organization through the [official website](https://naabtech.ir) or [info@naabtech.ir](mailto:info@naabtech.ir).

---

## Reporting a Vulnerability

**Do not open a public issue, pull request, or discussion for a vulnerability.** A public report gives everyone — including attackers — a head start.

Reporting a vulnerability is always permitted. Nothing else in this policy is authorized by it. See [Authorization and Permissions](#authorization-and-permissions).

### Preferred: GitHub private vulnerability reporting

GitHub provides a private reporting channel for repositories. When it is enabled for a repository, use it:

1. Open the affected repository on GitHub.
2. Go to the **Security** tab.
3. Select **Report a vulnerability**.
4. Describe the issue and submit the report.

The report opens a private advisory that only you and the maintainers can see. You receive a reference for the advisory, which is how fixes and any public credit are tracked.

**Availability is limited, and it depends on repository configuration.**

- GitHub's private vulnerability reporting interface is available for **public repositories** in which it has been enabled. It is not available for private or internal repositories through the web interface.
- The feature is enabled **per repository** by an owner, maintainer, or administrator. It is not enabled organization-wide by default.
- The private report form for this organization is [`.github/VULNERABILITY_REPORT.yml`](.github/VULNERABILITY_REPORT.yml). It is used where private reporting has been enabled, and a repository may replace it with its own form. **The form does not enable the feature** — it only customizes the questions asked once the feature is already enabled for that repository.

If the **Report a vulnerability** option is not present on a repository, use one of the alternatives below. This policy does not promise that the option is available in any given repository.

#### Enabling it across the organization

Individual repositories can be configured one at a time, but organization owners can also manage this across the organization with **custom security configurations**. A custom security configuration is a named set of enablement settings for GitHub's security products, and it includes a private vulnerability reporting setting that can be enabled, disabled, or left unchanged.

To create one: **Organization Settings → Security → Advanced Security → Configurations → New configuration → Custom configuration**. Apply it to existing repositories from the configuration's **Repositories** tab, and use **Use as default for newly created repositories** in its **Policy** section to cover repositories created afterwards.

Three things to keep in mind:

- **A default for newly created repositories does not backfill existing repositories.** Existing repositories have to be covered by applying the configuration to them explicitly.
- **Private vulnerability reporting does not become available for private or internal repositories through this mechanism.** It remains a public-repository feature, and private or internal repositories need an agreed private reporting route instead.
- **Verify the result.** Each repository's configuration status reflects the outcome of the operation, so confirm that the repositories you intended to cover are attached.

> **Not enabled.** NaaB Tech has not created an organization-level security configuration. The settings described here are options an organization owner can configure, not a description of the current state.

Reference: [Creating a custom security configuration](https://docs.github.com/en/code-security/how-tos/secure-at-scale/configure-organization-security/establish-complete-coverage/create-custom-configuration).

### Alternatives

If private reporting is not available for the repository in question:

- Email **[info@naabtech.ir](mailto:info@naabtech.ir)** with the subject line `Security report — <repository>`. State clearly in the subject line that the message is a security report, so it is routed to the maintainers rather than treated as a general inquiry.
- For issues affecting several repositories, contact the organization owners through [github.com/NaaBTech](https://github.com/NaaBTech).

> **Open item.** `info@naabtech.ir` is NaaB Tech's published general contact address. It is not a dedicated security mailbox, and it is not a continuously monitored security intake channel. A dedicated security address would route reports more reliably and should be designated once that mailbox exists and is staffed. Until then, mark the message clearly so that it reaches the maintainers rather than being treated as a general inquiry, and avoid putting sensitive detail in the subject line.

### What to include

A complete report helps more than a long one. An incomplete report is still welcome — see [Triage](#triage) below.

| Information | Why it matters |
| --- | --- |
| **Affected component** | The repository, and the path or component within it if the issue is limited to one. |
| **Affected version** *(if known)* | The release tag, commit SHA, or deployment identifier where the issue was observed. |
| **Description** | What the vulnerability is and what an attacker gains by exploiting it. |
| **Impact** *(if you can assess it)* | The concrete consequence — unauthorized access, data exposure, privilege escalation, service degradation, and so on. |
| **Steps to reproduce** *(if you have them)* | A sequence a maintainer can follow to confirm the issue. |
| **Proof of concept** *(optional)* | Request code, a request/response pair, or a configuration excerpt. A proof of concept does not need to be weaponised, and must not contain real credentials or personal data. |
| **Suggested remediation** *(optional)* | If you have one. This does not affect how the report is triaged. |
| **Your contact details** *(optional)* | A way to reach you for follow-up questions. Only if you are comfortable sharing them. |

Redact credentials, tokens, private keys, and personal data from anything you attach.

### Triage

Reports are triaged by **risk**, not strictly in the order they arrive. The following factors determine priority:

| Factor | What it means for priority |
| --- | --- |
| **Severity** | The extent of the impact if the vulnerability is exploited. |
| **Exploitability** | How much effort an attacker needs, and whether a working path exists. |
| **Impact** | The consequence for NaaB Tech, its users, or its customers. |
| **Affected users and systems** | How widely the issue is exposed, and whether it sits on a critical path. |
| **Exposure and reachability** | Whether the affected component is publicly reachable, and whether it is reachable without authentication. |
| **Evidence of active exploitation** | Whether the vulnerability appears to be in use in the wild. |

Reports with evidence of active exploitation are treated as the most urgent. Reports that are confirmed not to affect NaaB Tech software are closed with an explanation.

Once a report is received:

- You are kept informed through the private advisory thread, or the email thread where private reporting is unavailable. That thread is the channel for clarification, remediation updates, and credit decisions.
- Credit is offered in the advisory or release notes if you want it, in the form you prefer, including anonymous credit.

> **No service-level commitment.** NaaB Tech does not publish response-time, triage-time, or remediation-time commitments for vulnerability reports. Nothing in this policy is a service-level agreement, and no ordering described above is a guarantee of a particular outcome.

### Coordinated disclosure

The goal is a fix that is available before the details are public.

- The report is acknowledged through the private channel where one is available.
- The report is validated and its severity assessed.
- A disclosure timeline is agreed with the reporter, based on the work needed to release a fix.
- Remediation and disclosure decisions, and the reasoning behind them, are explained to the reporter.
- Where an issue affects widely used software, coordination with the relevant ecosystem may be necessary. That can extend the timeline, and the reason is explained to the reporter.
- Credit is provided as agreed.

**NaaB Tech asks that the details of a vulnerability are not made public until a disclosure timeline has been agreed.** This is a request for coordination, not a legal claim about what a reporter is required to do. Publishing a proof of concept prematurely exposes every user of the affected software and hands attackers a ready-made tool, which is why the request is made.

If you believe a coordinated timeline is not being honored, contact the organization through the [official website](https://naabtech.ir) or [info@naabtech.ir](mailto:info@naabtech.ir) and ask for escalation.

---

## Authorization and Permissions

**Reporting a vulnerability is not the same as being authorized to test for one.** These are separate permissions, and this policy grants only the first.

| Permission | Granted by | What it requires |
| --- | --- | --- |
| **Reporting a vulnerability** | This policy | Nothing. Always permitted. |
| **Testing a NaaB Tech-operated system** | The owner of that system, in writing | An authorization that names the assets, scope, timeframe, and permitted methods. |
| **Testing a customer-operated or customer-owned system** | The customer or the actual system owner | The same, in writing, from the customer. NaaB Tech's involvement does not substitute for it. |
| **Testing a third-party system or service** | That system's owner | Nothing in this document applies to third-party systems. |
| **Conducting a contracted penetration test or security assessment** | A signed engagement agreement | The agreement defines the scope, timing, and test methods. |

Key points:

- **Reporting does not authorize further testing.** Submitting a report is always permitted. Reading, scanning, or interacting with a system beyond what is needed to file the report is not.
- **Testing live systems requires explicit written authorization from the owner of the system.** A verbal assurance, a public bug bounty listing, or the existence of this policy is not authorization.
- **Authorization must be specific.** It should name the assets in scope, the window during which testing is permitted, the techniques allowed, and the contact point for unexpected results. An authorization for one system says nothing about any other.
- **Customer systems require the customer's authorization.** NaaB Tech operating, hosting, or maintaining a system for a customer does not make NaaB Tech the owner of that system for testing purposes.
- **If authorization is unclear, do not proceed.** Treat the activity as not permitted until the owner confirms it in writing. Questions can be sent to [info@naabtech.ir](mailto:info@naabtech.ir).

### Rules of engagement

Where authorization does exist, the following are outside it:

- Accessing data that is not yours, or data the tester is not authorized to access.
- Accessing accounts, systems, or data belonging to other users or customers.
- Extracting, downloading, or retaining personal data, credentials, keys, or configuration beyond the minimum needed to demonstrate the issue.
- Introducing malware, or modifying data in a way that leaves the system in an altered state.
- Introducing denial-of-service conditions, including sustained load, resource exhaustion, and lockout of legitimate users.
- Destroying, corrupting, or deleting data, including test data, without written authorization.
- Deceptive or destructive testing against shared infrastructure.
- Using social engineering, physical intrusion, or impersonation of staff, contractors, or users.
- Scanning, probing, or testing systems that are not named in the authorization.
- Continuing to test after a report has been filed and remediation work has begun.

### No safe-harbor commitment

This policy does not grant permission to test any system, and it does not promise legal protection for testing that was not authorized.

- Reporting a vulnerability is the only activity this policy authorizes.
- NaaB Tech has not adopted a safe-harbor, immunity, or indemnification provision. A researcher who tests a system without the owner's authorization may be exposed to legal risk, and nothing in this document waives any right or remedy available to the owner of a system.
- NaaB Tech will not make public accusations against a researcher who acts in good faith and reports findings through the routes described above. That is a statement about how reports are handled, not a legal guarantee.

> **Owner decision.** A safe-harbor provision can be added to this policy. Before it is published it should be drafted and approved by the organization owners and reviewed by legal counsel, and it should name the assets it covers. This policy deliberately does not define an in-scope asset list, because doing so would imply that those assets are authorized for testing.

There is no bug bounty program. Participation is voluntary and unpaid.

---

## Reporting a Vulnerability in a Third-Party Component

If a NaaB Tech repository depends on a vulnerable third-party project, report it to that project's maintainers through its own disclosure process. Reporting it privately to NaaB Tech as well is welcome — it helps us plan an upgrade or mitigation — but the fix has to come from the upstream project.

Please do not open a public issue in a NaaB Tech repository to report an upstream vulnerability.

---

## Related Documentation

- [Contributing guidelines](CONTRIBUTING.md) — how to report a non-security defect and propose a change.
- [Support guidance](SUPPORT.md) — where to ask questions that are not security reports.
- [Code of Conduct](CODE_OF_CONDUCT.md) — expectations for interaction in NaaB Tech spaces.
- [Repository onboarding](REPOSITORY_ONBOARDING.md) — how private vulnerability reporting is configured for each repository.
- [GitHub: Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [GitHub: Reporting a vulnerability privately](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately)
- [GitHub: Coordinated disclosure of security vulnerabilities](https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/coordinated-disclosure)
