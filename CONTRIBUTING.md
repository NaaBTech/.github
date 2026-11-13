# Contributing to NaaB Tech

Thank you for your interest in contributing to NaaB Tech. This guide describes how contributions are handled across the organization's repositories, of any visibility: how to report a problem, how to propose a change, and what is expected of a pull request.

Participation in this organization is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Scope and Precedence

These guidelines are the **organization-level default**. They apply to any repository in the [NaaB Tech](https://github.com/NaaBTech) organization that does not define its own contribution guidelines.

**An individual repository may define additional or stricter requirements.** If a repository has its own `CONTRIBUTING.md`, that file describes the expectations for that specific project and takes precedence over this document wherever the two differ. Repository-level rules typically cover the language, tooling, test commands, review process, and release process that only that project has.

Where a repository is silent on a topic, the guidance below applies.

---

## Before You Contribute

1. **Search for existing work.** Check the issue tracker and open pull requests to see whether the problem or idea has already been reported. Include closed issues — the answer may already be documented there.
2. **Check that the project is actively maintained.** Repositories may be archived or paused. A repository's README and recent activity indicate its current status.
3. **Open an issue first for anything substantial.** A short discussion before implementation prevents duplicated effort and confirms that a change is wanted before you spend time on it.
4. **Keep contributions scoped.** Pull requests that mix unrelated changes are difficult to review and slow to merge.

---

## Reporting a Bug

Use the **Bug report** issue form in the repository where the problem occurs.

A good bug report contains:

- **What you did**, **what you expected**, and **what happened instead**, as three separate statements.
- **Steps to reproduce** that someone else can follow without asking you questions. A minimal reproduction is ideal.
- **The affected version**, commit, or release, and the environment it runs in.
- **Logs, error output, and screenshots**, with credentials, tokens, and personal data removed before posting.

If a similar report already exists, add your reproduction details to it instead of opening a duplicate.

---

## Suggesting a Feature

Use the **Feature request** issue form.

Explain the problem before the solution. A feature request is strongest when it describes the situation that forces the need, who encounters it, and what happens today. Proposed solutions are welcome, but a problem statement remains valid even when the suggested approach changes during discussion.

---

## Opening an Issue

- **Use a specific, searchable title.** "Login fails on reset when the token has expired" is more useful than "Login broken".
- **One topic per issue.** Unrelated questions are easier to resolve separately.
- **Format code and logs** in fenced code blocks so they remain readable.
- **Never post secrets.** API keys, passwords, private keys, and tokens must be removed. If one has been exposed, revoke it first — see [Security Considerations](#security-considerations).
- **Use the Question form** for usage questions when the repository does not have Discussions enabled.
- **Use Discussions** for open-ended conversation when the repository has Discussions enabled. Issues are otherwise for actionable items: defects, proposals, and tracked work.
- **Do not use a public issue for a security vulnerability.** Follow [SECURITY.md](SECURITY.md) instead.

---

## Working on a Change

### Branch Naming

Create a focused branch from the default branch. If you do not have write access to the repository, fork it first and branch from the fork's default branch. Use the following prefixes:

| Prefix | Use for |
| --- | --- |
| `feature/` | New functionality |
| `fix/` | A defect fix |
| `docs/` | Documentation only |
| `refactor/` | A change to internal structure with no behavior change |
| `security/` | A security improvement or hardening change |

Examples:

```text
feature/session-token-rotation
fix/incorrect-timezone-handling
docs/deployment-guide
refactor/extract-request-parser
security/tighten-request-body-limits
```

The `security/` prefix is for **ordinary, non-sensitive security work**: tightening input validation, adding a security header, improving authentication logic, reducing an exposed default, or hardening configuration. Such changes are ordinary pull requests and are reviewed and merged like any other.

It is **not** the place to disclose a vulnerability. If you have found an unpatched vulnerability, do not open a public issue, branch, commit, or pull request that describes it. Follow [SECURITY.md](SECURITY.md) and let the fix be coordinated through a private security advisory first. A public security pull request must never disclose an unresolved vulnerability; if one does, it should be converted into a private advisory before it is merged.

Keep branches short-lived. Rebase or merge the default branch into your branch before requesting review if it has moved significantly.

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) where it fits the change:

```text
<type>(<scope>): <short summary>
```

Common types:

| Type | Meaning |
| --- | --- |
| `feat` | A new feature |
| `fix` | A defect fix |
| `docs` | Documentation changes only |
| `refactor` | Internal restructuring, no behavior change |
| `perf` | A performance improvement |
| `test` | Adding or correcting tests |
| `build` | Build system, dependencies, packaging |
| `ci` | Continuous integration configuration |
| `chore` | Maintenance that does not touch source or tests |
| `revert` | Reverts an earlier commit |

Write the summary in the imperative mood and keep it under roughly 72 characters. Explain the reasoning in the body when it is not obvious from the diff:

```text
fix(auth): reject tokens issued before the signing key rotation

Tokens minted with the previous signing key were still accepted after
rotation, which allowed a revoked session to stay valid. Compare the
issued-at claim against the current key generation.
```

### Pull Requests

- Use the pull request template. Fill in every relevant section; delete the ones that genuinely do not apply rather than leaving empty headings.
- Link related issues using closing keywords such as `Fixes #123` or `Closes #123`.
- Keep the change to one logical unit. A refactor and a behavior change belong in separate pull requests.
- Make sure the branch builds and that existing tests pass before requesting review.
- Write a description that lets a reviewer understand *why* the change is needed, not only what changed.
- Respond to review comments. If a suggestion is declined, explain why — that discussion is useful to future readers.

---

## Code Quality

- **Match the surrounding code.** Follow the conventions of the repository, including naming, file structure, and formatting. Run the project's formatter and linter before submitting.
- **Keep changes reviewable.** Avoid unrelated reformatting, reordering, or dependency upgrades in a feature pull request. Separate them.
- **Remove dead code.** Do not leave commented-out blocks or unused variables behind.
- **Handle errors explicitly.** Do not silently swallow exceptions, and do not log secrets or personal data.
- **Treat dependencies carefully.** Prefer well-maintained packages, review the license of anything added, and avoid adding a dependency where a small amount of standard library code would do.
- **Never commit credentials.** Keep secrets out of source, configuration, fixtures, and commit history.

---

## Testing

- **Add or update tests** for the behavior you changed. A change that alters behavior without a test is difficult to trust.
- **Reproduce the bug first.** For a defect fix, add a test that fails against the current code and passes with the fix.
- **Run the full test suite** locally when you can. Report exactly what you ran, and say so plainly if you could not run it.
- **Do not weaken or delete a test to make a change pass.** A failing test is information. If a test genuinely needs to change, say why in the pull request.
- **Keep tests deterministic.** No reliance on network access, wall-clock time, or unordered iteration.

---

## Documentation

- Update the documentation that your change affects — `README`, usage guides, configuration references, and API documentation.
- Match the existing tone and structure of the document you are editing.
- Document the behavior as it is after your change, not as it was before.
- If a change introduces a breaking change, call it out explicitly in the pull request and in the relevant documentation.

---

## Security Considerations

- **Report vulnerabilities privately.** Never open a public issue, pull request, or discussion for a security vulnerability. Follow [SECURITY.md](SECURITY.md).
- **Do not disclose an unresolved vulnerability in public.** Unpatched vulnerability details must not appear in a public branch name, commit message, issue, pull request, or review comment. A fix for a known vulnerability is coordinated through a private security advisory, and is made public once the fix and the disclosure timeline are agreed.
- **Distinguish ordinary hardening from confidential remediation.** A public `security/` pull request is appropriate for a general security improvement. If the change fixes a specific vulnerability that is not yet public, keep it out of the public repository until the advisory process has completed.
- **Do not include proof-of-concept data that is unsafe to publish.** Exploit payloads, real credentials, and customer data must not appear in an issue or pull request.
- **Assume every pull request is reviewed by someone other than its author.** Write code that a stranger can understand and verify.
- **Be careful with authorizations.** If a change alters authentication, authorization, session handling, cryptography, or input validation, state the security impact explicitly in the pull request, including the threat you considered and how it is addressed.
- **Do not introduce new dependencies that handle security-critical work** without a clear reason and a review of their maintenance status.

---

## Code of Conduct

Participation in NaaB Tech repositories is governed by the [Code of Conduct](CODE_OF_CONDUCT.md), which is based on the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct.html). Reports of unacceptable behavior are handled by the organization maintainers, as described in that document.

---

## Reporting Abuse

For behavior that violates GitHub's Terms of Service, including spam and malicious content, use GitHub's [abuse reporting](https://support.github.com/contact/report-abuse) flow.
