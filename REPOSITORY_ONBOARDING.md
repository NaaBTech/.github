# Repository Onboarding

A repeatable checklist for preparing a NaaB Tech GitHub repository, and for keeping it healthy afterwards.

**This is a checklist, not a record.** It describes what should be true for each repository. Nothing in it asserts that a setting is currently enabled anywhere. Confirm each item on the repository you are working on, and record the result there.

---

## How the Pieces Fit Together

Before starting, it helps to know which layer each decision belongs to. Getting this wrong is the usual cause of a setting that was configured once and then silently lost.

| Layer | Where it lives | Who changes it |
| --- | --- | --- |
| **Files in the repository** | Committed to the repository: `README.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/`, `.github/workflows/`, `LICENSE`, and similar | Anyone with write access, through a pull request |
| **Repository settings** | The GitHub settings for that one repository: visibility, topics, branches, Actions permissions, security features | A maintainer or administrator of that repository |
| **Organization settings** | Organization Settings: default labels, default branch name, member permissions, security policies | An organization owner |
| **Organization defaults** | The `.github` repository: the community health files every repository inherits | Anyone with write access to `.github` |

A committed file is the durable choice — it travels with the repository and is reviewable. A settings toggle is per-repository and has to be repeated for each repository.

---

## 1. Basic Repository Setup

- [ ] **Name** — chosen to match the project, consistently across the repository, the README, and any package metadata.
- [ ] **Description** — one sentence describing what the project is. No claims about scale, customers, or certification.
- [ ] **Visibility** — decided deliberately. Public for work that is meant to be open; private for internal or client work. A repository that has been public keeps its history publicly reachable.
- [ ] **README** — what the project is, how to install it, how to use it, and how to get help. A repository without a README has no entry point.
- [ ] **Default branch** — `main`, matching the rest of the organization.
- [ ] **Project documentation** — anything longer than the README lives in `docs/` or equivalent, with the README linking to it.
- [ ] **LICENSE** — every project needs its own license, chosen for that project. The organization deliberately has **no** default license file: GitHub does not use the `.github` repository as the source of a default project license, so a project without one is unlicensed until this is added.
- [ ] **Topics** — set on the repository so it is discoverable.

---

## 2. Community Health

**Understand what is inherited.** Every repository in the organization inherits the community health files in the `.github` repository. A default is used only where the repository does not define its own file of that type, and a repository-level file always takes precedence. Nothing is copied into the repository — the defaults are served by GitHub.

- [ ] **Repository-specific policies** — added only where the project genuinely needs something different. Each override should be specific to the project, not a copy of the default.
- [ ] **Issue forms** — the organization provides Bug report, Feature request, and Question forms by default. A project that needs its own forms adds `.github/ISSUE_TEMPLATE/` to the repository, which replaces **all** the organization defaults for that repository.
- [ ] **Labels** — the default forms apply `bug`, `enhancement`, and `question`. Those labels must exist in the repository, or the forms are submitted without a label. Organization default labels apply to **newly created repositories only**, so an existing repository needs them created manually. Labels belong to the repository, so a maintainer of that repository creates them.
- [ ] **Pull request template** — inherited by default. Add a repository-level one only if the project needs a different one.
- [ ] **Support and Code of Conduct** — inherited by default, and linked from the README.
- [ ] **Issue tracker** — enabled, with the forms above available in the template chooser.

---

## 3. Security

- [ ] **`SECURITY.md`** — inherited from the organization. Override it only if the project needs different instructions, and never remove the disclosure route in doing so.
- [ ] **Private vulnerability reporting** — enable it for **public repositories** in **Settings → Security and quality → Advanced Security → Private vulnerability reporting**. The feature is public-repository-only, is enabled per repository, and is **not** switched on by the presence of a `VULNERABILITY_REPORT.yml` file. Private and internal repositories need an agreed private route instead.
- [ ] **Vulnerability report form** — the organization default is inherited for public repositories with private reporting enabled. A project may add its own `.github/VULNERABILITY_REPORT.yml`.
- [ ] **Dependency security** — the dependency graph, Dependabot alerts, and Dependabot security updates. These are repository settings and are enabled per repository.
- [ ] **Secret protection** — secret scanning and push protection, where the plan supports them. Both are repository settings.
- [ ] **Code scanning** — where supported and appropriate for the language in use. A default analysis setup is a reasonable starting point; CodeQL is not relevant to every project.
- [ ] **Security contact** — until a dedicated security address exists, `info@naabtech.ir` is the fallback route, and reports must be marked clearly in the subject line. Record the route in the repository's `SECURITY.md` if it differs.
- [ ] **Access** — the smallest team that can maintain the repository, and no stale accounts with write access.

---

## 4. Development Workflow

- [ ] **Branch protection or rulesets** — on the default branch, requiring review before merge, and blocking force pushes and branch deletion. Rulesets are preferred where available because they can be configured at the organization level.
- [ ] **Review requirements** — a second approval for changes that touch authentication, authorization, cryptography, or deployment configuration.
- [ ] **Continuous integration** — a workflow under `.github/workflows/` that builds and tests the project on every pull request.
- [ ] **Automated tests** — the test suite runs in CI, and a failing test fails the build.
- [ ] **Dependabot** — version updates enabled, with a weekly schedule.
- [ ] **Release and versioning** — a documented convention: tag format, changelog location, and how a release is published.

> A workflow file placed in the `.github` repository under `.github/workflows/` is an **organization-wide default** — it runs in every repository in the organization. Workflows that belong to one project only belong in that project.

---

## 5. Maintenance

- [ ] **Dependencies** — kept current; automated update PRs reviewed rather than merged blindly.
- [ ] **Documentation** — accurate and current. Stale documentation is a defect, and correcting it is a welcome contribution.
- [ ] **Repository access** — reviewed periodically, and former collaborators removed when they leave.
- [ ] **Archive rather than delete** — a project that is no longer maintained is archived with a short note in its README explaining why, rather than deleted.
- [ ] **Security settings** — reviewed periodically: branch protection, private vulnerability reporting, secret scanning, and the security contact route.
- [ ] **Community health files** — if the repository has its own copies, reviewed for drift against the organization defaults.

---

## Verifying the Result

After onboarding, confirm on the repository itself:

1. The repository's **About** panel shows the description, website, and topics.
2. Opening a new issue shows the expected templates in the chooser.
3. Submitting a test issue applies the `bug`, `enhancement`, or `question` label.
4. The **Security** tab shows the security policy, and **Report a vulnerability** is present for a public repository where private reporting was enabled.
5. The repository's README links to the contributing, code of conduct, and support documents.
6. The default branch is protected, and a test pull request triggers the CI workflow.
