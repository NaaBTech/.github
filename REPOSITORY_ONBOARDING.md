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

- [ ] **Name** — chosen to match the project, consistently across the repository, the README, and any package metadata. A product published by the organization carries the short brand name as its prefix, so it is named `NaaB <Product>`.
- [ ] **Description** — one sentence describing what the project is. No claims about scale, customers, or certification.
- [ ] **Visibility** — decided deliberately. Public for work that is meant to be open; private for internal or client work. A repository that has been public keeps its history publicly reachable.
- [ ] **README** — what the project is, how to install it, how to use it, and how to get help. A repository without a README has no entry point.
- [ ] **Default branch** — `main`, matching the rest of the organization.
- [ ] **Project documentation** — anything longer than the README lives in `docs/` or equivalent, with the README linking to it.
- [ ] **LICENSE** — every project needs its own license, chosen for that project. The organization provides **no** default license for projects: GitHub does not use the `.github` repository as the source of a default project license, so a project without one is unlicensed until this is added. The license on this repository covers its own contents only.
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

### Organization-Level Security Configuration

The checklist above is repository by repository. Organization owners can instead manage security settings across repositories with **custom security configurations**, which is the right tool once there are several repositories to keep consistent.

A custom security configuration is a named set of enablement settings for GitHub's security products, including **private vulnerability reporting**, secret scanning and push protection, the dependency graph, Dependabot alerts, and code scanning.

To create one: **Organization Settings → Security → Advanced Security → Configurations → New configuration → Custom configuration**.

What it can do:

- **Configure private vulnerability reporting for selected eligible repositories.** A configuration includes a private vulnerability reporting setting, which can be enabled, disabled, or left as it is.
- **Apply a configuration to groups of existing repositories.** Open the configuration's **Repositories** tab, filter for the repositories in scope, and choose **Apply configuration**. This is how existing repositories are brought in — a default for new repositories does not do it for them.
- **Define a default for newly created repositories.** In the configuration's **Policy** section, **Use as default for newly created repositories** can be set to `Public`, `Private and internal`, or `All repositories`.
- **Enforce the configuration.** Setting **Enforce configuration** blocks repository owners from changing the features the configuration enables or disables. Features the configuration does not set are not enforced, and some situations can break enforcement.

Two limitations to keep in mind:

- **A default for newly created repositories does not backfill existing repositories.** The default is only applied automatically to repositories created in the organization afterwards. A repository transferred into the organization still needs a configuration applied manually. Existing repositories must be covered by applying the configuration to them explicitly.
- **Private vulnerability reporting does not become available for private or internal repositories through this mechanism.** It remains a public-repository feature. Private and internal repositories still need an agreed private reporting route, such as an address monitored by the organization.

After applying a configuration, **verify it**. Each repository's configuration status reflects the result of the operation — `attached`, `attaching`, or `failed` — so check the repositories you intended to cover rather than assuming the change landed.

> **Not enabled.** NaaB Tech has not created an organization-level security configuration. Every setting described above is an option that an organization owner can configure, not something that is currently in place.

Reference: [Creating a custom security configuration](https://docs.github.com/en/code-security/how-tos/secure-at-scale/configure-organization-security/establish-complete-coverage/create-custom-configuration) and [Applying a configuration to repositories](https://docs.github.com/en/code-security/how-tos/secure-at-scale/configure-organization-security/establish-complete-coverage/apply-custom-configuration).

---

## 4. Development Workflow

- [ ] **Branch protection or rulesets** — on the default branch, requiring review before merge, and blocking force pushes and branch deletion. Rulesets are preferred where available because they can be configured at the organization level.
- [ ] **Review requirements** — a second approval for changes that touch authentication, authorization, cryptography, or deployment configuration.
- [ ] **Continuous integration** — a workflow under `.github/workflows/` that builds and tests the project on every pull request.
- [ ] **Automated tests** — the test suite runs in CI, and a failing test fails the build.
- [ ] **Dependabot** — version updates enabled, with a weekly schedule.
- [ ] **Release and versioning** — a documented convention: tag format, changelog location, and how a release is published.

> A workflow file belongs to the repository that contains it. The `.github` repository holds `validate-docs.yml`, which validates the organization's default files and runs only here. It is not inherited by other repositories — see [Community Health Files Are Not Inherited as Workflows](#community-health-files-are-not-inherited-as-workflows).

### Community Health Files Are Not Inherited as Workflows

The organization's `.github` repository provides **community health defaults**: contribution guidelines, the code of conduct, the security policy, support guidance, issue forms, and the pull request template. GitHub serves those to every repository in the organization that does not define its own.

**GitHub Actions workflow files are not inherited this way.** A workflow file in `.github/workflows/` runs only in the repository that contains it. The `validate-docs.yml` workflow in this repository runs only in `NaaBTech/.github` — it does not run in any other NaaB Tech repository, and it is not an organization-wide default.

Every project that needs continuous integration therefore needs its own workflow file in its own `.github/workflows/` directory. A project with no workflow file has no CI, regardless of what this repository contains.

### Sharing One Workflow Across Repositories

If the same checks are needed in several repositories, the workflow has to be made **reusable**, and each repository has to call it explicitly.

1. A reusable workflow must explicitly declare the `workflow_call` trigger:

   ```yaml
   on:
     workflow_call:
   ```

2. Each consuming repository adds its own caller workflow that calls it by path and reference. Using a hypothetical example — `example-org/example-repo` is not a NaaB Tech repository, and no such reusable workflow exists today:

   ```yaml
   jobs:
     validate-docs:
       uses: example-org/example-repo/.github/workflows/validate-docs.yml@main
   ```

   A reusable workflow is called from a **job**, not from a step, and the reference is `owner/repository/.github/workflows/file.yml@ref`. Reusable workflows must sit directly in a repository's `.github/workflows/` directory — subdirectories of that directory are not supported.

3. **A consuming repository must call the workflow explicitly.** Nothing runs automatically. A repository that does not contain the caller workflow gets no checks.

4. **The documentation validator in this repository is not a reusable workflow.** `validate-docs.yml` does not declare `on: workflow_call`, so it cannot be called from another repository, and it is not offered as a shared workflow.

   Making it reusable would take more than adding the trigger. It validates this repository's own files — the vendored schemas, the default forms, and the organization-specific label, naming, and link rules — and it assumes those paths exist. Turning it into a reusable workflow would mean deciding what it should validate in a calling repository, what inputs it accepts, and how it reports results back. That is a deliberate adaptation, not a one-line change, and it has not been done.

5. **If the shared workflow lives in a private repository**, grant access to the repositories that will use it: in the private repository, go to **Settings → Actions → General**, and in the **Access** section select **Accessible from repositories in the 'NaaBTech' organization**.

   Be aware of the trade-off: making a private repository accessible to Actions workflows in other repositories means outside collaborators on those repositories can indirectly access the private repository, and can view the logs of workflow runs that use it. Share a workflow from a private repository only when that is acceptable.

Reference: [Sharing actions and workflows with your organization](https://docs.github.com/en/actions/how-tos/reuse-automations/share-with-your-organization) and [Reuse workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows).

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
