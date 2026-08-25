---
name: skill-authoring
description: Repo-specific checklist for writing or editing files under .github/skills/**/SKILL.md in mfgparams. Applies to any PR that changes a skill's own documentation (not application code) — catches the recurring class of self-consistency and unverified-CLI-behavior bugs found by Copilot review across this repo's own skill-editing PRs (#22, #25, #29, #31, #35).
---

# Skill Authoring Checklist (mfgparams)

Use this skill whenever a PR modifies a file under `.github/skills/**` —
that is, the skill is documentation *about how an agent should operate*
(e.g. `pr-review-loop`, `pypi-package-builder`, `code-review`), as
opposed to application code under `src/`/`tests/`. Copilot review has
repeatedly found the same two classes of bug in this category of PR, and
they are checklist-able before ever asking for a remote review round.

## 1. Single definition per concept — grep before you ship

When a PR redefines how a flag, counter, or concept works (e.g. when
`copilot-review-invoked` moved from "set after posting a PR comment" to
"set after an API call"), that concept is very likely mentioned in more
than one place in the same file — a title in prose, a bullet list, an
exit-criteria check, an anti-pattern note. Copilot has flagged this
mismatch on the *same file* three separate times (PRs #25, #31, #35).

Before finishing an edit to any `.github/skills/**/*.md` file:

```bash
grep -n "<the changed term or flag name>" .github/skills/<skill>/SKILL.md
```

Read every match. If the definition/behavior changed, every match must be
consistent with the new behavior — not just the section you were
actively editing. Do this for every renamed command, redefined boolean,
or changed step-ordering assumption before committing.

## 2. Verify CLI/API behavior empirically, don't assert it from memory

Several Copilot findings were about a documented command or API behavior
that was subtly wrong or repo-specific, not a general truth:

- `git branch -d` vs `-D` — `-d` refuses to delete a branch that isn't
  fully *merged* (this includes a squash-merged branch, which git can't
  detect as merged), and refuses an intentionally-discarded unmerged
  branch. If the skill's own merge flow uses squash merges, document `-D`
  after confirmed-merged verification, not `-d`.
- `gh api ... /requested_reviewers` defaults to **GET** — a fallback
  command written without `-X POST` and the reviewer payload silently
  lists current reviewers instead of requesting a new review. Always
  include the explicit method/payload in the documented command, and
  test it once in a real shell before writing it into a skill as fact.
- GraphQL connection fields (e.g. `reviewThreads(first:100)`) paginate —
  don't assume a fixed `first:N` always returns everything; either note
  the pagination limit explicitly or document following `pageInfo` /
  `endCursor`.
- A claim about what does/doesn't appear in a `gh` command's output
  (e.g. "X only shows workflow runs, not check runs") should be verified
  against this repo's actual `gh run list`/`gh api` output before being
  written as a hard fact — it may be correct in general but wrong for
  this repo's specific setup (or vice versa). Cite the verifying command
  and its actual output in the commit message when making such a claim.
- Branch/worktree deletion ordering: git refuses to delete a branch that
  is still checked out in a worktree. Document worktree removal *before*
  branch deletion, not after.

## 3. Exit-criteria completeness

If a skill defines "done"/"exit criteria" conditions (e.g. §5 of
`pr-review-loop`), make sure they cover every state fetched during setup
that could block the stated goal — not just the states the skill actively
polls for. A skill that fetches `mergeable`/`reviewDecision` during setup
but never re-checks them before declaring "ready to merge" can still hit
a real merge conflict or a required human approval it never accounted
for.

## 4. Don't let a rewritten step silently drop content

When restructuring a step (e.g. splitting a "poll CI" step into an
adaptive-polling block), diff the old step against the new one for
content that quietly disappeared (a required-jobs list, a caveat, a
worked example) rather than being deliberately superseded. This has
happened in this repo when a step was rewritten for one concern (polling
efficiency) and incidentally dropped an unrelated but still-needed detail
(the required-CI-jobs enumeration).

## 5. This checklist itself is a local pre-check

Applying this file's rules to your own diff *before* pushing and
requesting Copilot review (see `pr-review-loop` §3 step "local pre-check")
is the intended way to consume it — it exists specifically to catch
issues that don't need an LLM review round to find, because they're
mechanically checkable (grep for redefinitions, run the command once to
verify its real behavior).
