# Pull Request

## Summary

<!-- What changed, in two or three sentences? Focus on the outcome, not the file list. -->

## Motivation

<!-- Why is this needed? Describe the problem it solves. -->

Related issue: <!-- e.g. Fixes #123, or "None" -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (no behavior change)
- [ ] Documentation
- [ ] Build, tooling, or dependency update
- [ ] Security improvement or hardening

## Testing

<!-- What did you run, and what was the result? State it plainly. -->

- [ ] Added or updated tests
- [ ] Existing test suite passes locally
- [ ] Verified manually
- [ ] Not applicable — no testable behavior change

## Documentation

- [ ] Updated the documentation affected by this change
- [ ] Not applicable — no documentation change needed

## Security impact

<!--
Does this change affect authentication, authorization, input handling, cryptography,
dependencies, or the exposure of a system? If so, describe the threat you considered
and how it is addressed. Write "None" if the change has no security impact.
-->

- [ ] This change and its description contain no undisclosed vulnerability details, so the pull request is safe to review publicly

> If this pull request fixes a vulnerability that is not yet public, do not raise it here. Use a private security advisory and follow the disclosure process in [SECURITY.md](SECURITY.md).

## Breaking changes

<!--
Describe anything that would break an existing user, consumer, or integration,
and the migration path. Write "None" if there are none.
-->

## Reviewer checklist

- [ ] The change is scoped to one logical unit and contains no unrelated edits
- [ ] The branch name follows the repository's convention
- [ ] Commit messages follow the repository's convention
- [ ] New and modified code is formatted and passes linting
- [ ] Tests cover the changed behavior, or the change is not testable
- [ ] Secrets, tokens, and credentials are not present in the diff or commit history
