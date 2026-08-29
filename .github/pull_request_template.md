## Summary

<!-- What does this PR change and why? -->

## Quality & Security Gate Exceptions

<!--
Constitution Principle IX requires that any accepted complexity (ruff C901/mccabe) or
security (bandit) finding be restated here with its rationale, in addition to the
in-code `# noqa: C901` / `# nosec B###` suppression comment (which is required too, see
README.md "Quality & Security Gates"). If this PR introduces no such exceptions, delete
this section or write "None".

Reviewers: reject this PR if a complexity/security suppression exists in the diff without
a matching entry here.
-->

- [ ] This PR introduces no undocumented complexity/security exceptions, **or**
- [ ] Every complexity/security exception below has a matching in-code suppression comment:

| File:line | Gate | Rationale |
|---|---|---|
| | | |

## Checklist

- [ ] Tests added/updated for the change
- [ ] All required CI checks pass (`lint`, `complexity`, `typecheck`, `security`,
  `dependency-scan`, `test (3.9)`, `test (3.10)`, `test (3.11)`, `test (3.12)`,
  `build`, `docs`, `Analyze (python)`, CodeQL)
