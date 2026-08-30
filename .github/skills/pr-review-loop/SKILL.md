---
name: pr-review-loop
description: Iteratively drive a mfgparams pull/merge request to green — fixing code until GitHub Copilot (balanced) code review comments and all required CI jobs pass — then require explicit user approval, a high-level summary of all commits, and cleanup of stale branches before closing. Use whenever asked to "work on a PR/MR until it's mergeable", "address Copilot review comments", "get CI green on this PR", or "finish up and close this MR".
---

# PR Review Loop (mfgparams)

Use this skill whenever you are asked to drive an open pull request (the
user may call it an "MR") to a mergeable, closeable state: fixing code
against GitHub Copilot code review feedback and CI failures in a loop,
with explicit checkpoints before anything destructive happens (merge,
close, branch/worktree deletion).

Prefer `gh` CLI (per this repo's convention) over the GitHub MCP server for
all PR/CI/review operations below.

## 1. Setup — identify the PR and gather state

Start the **time log** for this session first, before anything else in
this section — including the ambiguity confirmation below, which is
itself a human-blocked wait and must be captured:
- **loop-start timestamp** — capture once, as the very first action of
  this skill (e.g. `date -u +%Y-%m-%dT%H:%M:%SZ`).
- **waiting intervals** — every time execution pauses on a human decision
  (an `ask_user` call, a plain-text confirmation question the user must
  answer before you proceed, or any other point where you are explicitly
  waiting on the user rather than doing agent work), record a
  `(wait-start, wait-end)` pair. `wait-start` is when the question is
  asked / the pause begins; `wait-end` is when the user's answer resumes
  the loop. Do **not** count CI-polling waits or Copilot-review-polling
  waits — the agent is still driving those, not blocked on the human —
  only count waits that are genuinely blocked on a human response.

```bash
gh pr view <number-or-branch> --json number,title,url,headRefName,baseRefName,state,mergeable,reviewDecision,commits,body
gh pr checks <number-or-branch>
```

If no PR number/branch is given, infer it from the current branch
(`git branch --show-current`) and confirm with the user if ambiguous —
record this confirmation as a waiting interval in the time log if it
happens.

Keep the fetched `body` (the PR description) on hand — §2's suppression
check depends on cross-referencing it against the "Quality & Security Gate
Exceptions" table, and it can go stale if the description is edited
mid-loop, so re-fetch it whenever re-checking suppression status.

Initialize (mentally or in a scratch note) two counters for this session:
- **review-fix commit count** — commits made *specifically* to address a
  Copilot review comment or a failing CI job. Reported at the §4 budget
  checkpoint; it no longer triggers that checkpoint on its own.
- **running summary** — one line per commit describing what changed and
  why, to be presented at the §4 budget checkpoint and again at closure.

Also track a boolean:
- **copilot-review-invoked** — set true only after explicitly requesting
  Copilot review via the `requested_reviewers` API call (§3 step 7) at
  least once in this session.

At closure, derive from the time log:
  - **total wall time** = now − loop-start timestamp.

  - **time waiting on human decisions** = sum of all recorded waiting
    intervals.
  - **time agent was working** = total wall time − time waiting on human
    decisions.

### Declare the review intensity before the first fix

Pick an intensity from the diff, state the choice and its budget in chat
in one line, and proceed. Do **not** ask by default — the user may
override with a single word (`low` / `medium` / `high` / `very high`) at
any point, which re-baselines the budget without resetting counters
already spent.

| Intensity | Max rounds | Agent-busy budget | Severity floor (fix in-loop) | Auto-select when |
|---|---:|---:|---|---|
| **low** | 2 | 20 min | HIGH+ | docs/prose only, or <=50 changed lines with no `src/` |
| **medium** | 3 | 40 min | MEDIUM+ | <=300 changed lines, no new public API |
| **high** | 5 | 75 min | MEDIUM+ | new public API, formula changes, `ci.yml` gating, `harness.py` |
| **very high** | 8 | 120 min | LOW+ | new feature spec, >1000 changed lines, release, constitution amendment |

The minute budgets are single thresholds, not ranges — a range gives two
agents on the same PR two different checkpoint times. They are upper
bounds calibrated against this repo's measured agent-busy cost of ~8 min
per round on small PRs and ~27 min on large ones (#71).

**Selection precedence: the highest-intensity matching row wins.** A
1500-line docs-only spec PR matches both `low` and `very high`; it is
`very high`. **If no row matches** — say a 600-line test-only refactor
with no new public API, no formula/`ci.yml`/`harness.py` change and no new
spec — default to **medium** rather than inventing a row.

At **very high** the floor is `LOW+`, so LOW is in scope; but a LOW fix
still needs explicit human approval before it is made. The point of very
high is thoroughness on a release or a constitution amendment, not
unattended prose churn.

Severity bands are defined in `.github/skills/code-review/SKILL.md` §0.
The **floor** is the lowest band fixed inside the loop; everything below
it is deferred, not fixed — though until the deferral path lands the
floor drives §4's stop conditions and reporting only, and every finding
is still fixed or rebutted (see §3). Get the changed-line count from
`gh pr view <number> --json additions,deletions` (verified on PR #71:
`{"additions":1920,"deletions":40}`) — prefer it over piping `gh pr diff`
into `diffstat`, which is not installed everywhere.

**Rounds bind; minutes are advisory.** A round — one Copilot review
submission and the fix batch answering it — is mechanically countable, so
**rounds exhausted always ends the loop**. The agent-busy budget cannot
be enforced mid-round: it is derived after the fact from the §6 time log
and is self-reported, so it never silently ends the loop on its own.
Instead, once agent-busy time crosses its budget, the **next round
boundary** fires the §4 checkpoint even if rounds remain. This keeps a
large PR (#71: ~27 min per round) from spending five rounds before anyone
looks, without pretending a soft measure is a hard gate.

Initialize a third counter alongside the two above:
- **review round count** — incremented once per completed Copilot review
  round (a review submission plus the fix batch answering it). This, not
  the commit count, is what §4's budget is spent against.

## 2. Fetch Copilot review comments, excluding suppressed ones

Copilot review runs at the "balanced" preset for this repo (see
`.github/skills/code-review/SKILL.md` for the review context Copilot
itself uses). Fetch review threads via the GraphQL API so resolved state
is available (REST `pulls/comments` does not expose it):

```bash
gh api graphql -f query='
  query($owner:String!,$repo:String!,$pr:Int!,$cursor:String) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$pr) {
        reviews(last:20, states:[COMMENTED, CHANGES_REQUESTED]) {
          nodes { author { login } body state }
        }
        reviewThreads(first:100, after:$cursor) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            isResolved
            isOutdated
            comments(first:10) { nodes { author { login } body path line } }
          }
        }
      }
    }
  }' -f owner=<org> -f repo=<repo> -F pr=<number>
```

If `pageInfo.hasNextPage` is `true`, re-run with `-F cursor=<endCursor>`
and merge the results — a PR with more than 100 review threads (rare, but
possible on a long-running one) would otherwise silently hide older or
newer threads beyond the first page, and §5 could incorrectly declare no
actionable comments remain.

A comment counts as **suppressed / not actionable** — and must be
**ignored** — if any of the following hold:

- The review thread `isResolved: true` (a maintainer already resolved it).
- The comment is about a finding that already has a matching in-code
  suppression comment (`# noqa: C901`, `# nosec B###`) **and** a
  corresponding entry in the PR description's "Quality & Security Gate
  Exceptions" table (see `.github/pull_request_template.md`) — this repo's
  documented, accepted-exception convention.
- The author is not a Copilot review bot (e.g. `copilot-pull-request-reviewer`)
  — human/other-bot comments are informational context, not a gate, unless
  the user says otherwise.

Everything else from the Copilot reviewer that is unresolved is in scope
and must be fixed or explicitly rebutted (with a reply comment) before
proceeding.

Keep each thread's `id` (a `PRRT_...` node ID) for the session — §4's
novelty-stall check is defined over these IDs, and they are the only
stable handle on "have I seen this finding before". Verified against this
repo: `reviewThreads(first:3){nodes{id ...}}` on PR #71 returns
`PRRT_kwDOTTuBh86cnh5v` and siblings.

## 3. Iterate: fix → commit → push → re-check

Repeat until both are true: all required CI jobs are green **and** no
non-suppressed Copilot review comments remain unresolved.

1. Pick the highest-value unresolved item (correctness/test bugs before
   style nits) or the first failing CI job.

   Band every open finding per `.github/skills/code-review/SKILL.md` §0
   as you go, and record the counts — §4's checkpoint report and the §6
   histogram both need them, and the §1 severity floor is what §4's
   novelty-stall check is measured against.

   **The floor does not yet gate what gets fixed.** Every non-suppressed
   finding is still fixed or explicitly rebutted here, exactly as before;
   the floor currently drives §4's stop conditions and reporting only.
   Triage-before-fix, per-round batching, and the deferral path for
   below-floor findings are a follow-up to issue #76 — until they land,
   there is no exit for a finding other than fixing or rebutting it, so
   do not silently skip a LOW.
2. Make the fix. Follow `.github/instructions/python.instructions.md` and
   the priorities in `.github/skills/code-review/SKILL.md` (calculation
   correctness > resource limits > tests > extensibility > style).
3. **Local pre-check before pushing** — apply the relevant checklist
   yourself against the diff, catching mechanically-checkable issues
   before spending a Copilot review round on them (each round costs
   ~2-10 min, see §7's anti-pattern on blind sleeps):
   - Changes under `src/`/`tests/`/`.github/workflows/ci.yml`: re-read
     `.github/skills/code-review/SKILL.md` §2a, §3, §6a, §6b, §7a against
     the diff — these sections were written from patterns Copilot has
     repeatedly found in this repo (silent zero/placeholder substitution
     on error, CI-gating precedence bugs, resource-limit scoping,
     derived-key collisions, spec-kit artifact drift). §7a specifically
     targets `ci.yml` gating logic, so don't skip this check just because
     the change is to a workflow file rather than application code.
   - Changes under `.github/skills/**/*.md` (editing a skill itself, as
     you may be doing right now): apply
     `.github/skills/skill-authoring/SKILL.md` — grep the file for every
     mention of any concept/flag/command you changed, and verify any
     newly-asserted CLI/API behavior claim in a real shell before writing
     it down as fact.
   - This is not a substitute for the remote Copilot review (§5's exit
     criteria still requires it) — it's a cheap filter to reduce how many
     rounds you need.
4. Run the smallest targeted test/lint/build command locally that covers
   the change before pushing (see repo CI job list below) — don't rely on
   CI alone for feedback loop speed.
5. Commit with a message describing the specific review comment or CI
   failure addressed (not a generic "fix review comments"). Increment the
   review-fix commit counter and append a line to the running summary.
6. Push: `git push`. Capture the new head SHA (`git rev-parse HEAD`) — it
   identifies which CI/review run belongs to this specific commit.
7. Re-request Copilot review if it doesn't auto re-review on push:
   `gh api repos/:owner/:repo/pulls/:number/requested_reviewers -X POST
   -f "reviewers[]=copilot-pull-request-reviewer[bot]"` (a PR comment
   saying `@copilot review` is not reliable — use the API call). Set
   `copilot-review-invoked=true` when this is done.
8. **Poll for completion — don't blind-sleep a fixed 4-5 minutes.** The
   Copilot review surfaces as a pollable GitHub Actions run for the
   pushed commit; required CI jobs are best read via `gh pr checks`
   directly (see below for why). Poll both adaptively instead of
   guessing a wait or comparing review timestamps (stale timestamps from
   a *previous* round are easy to mistake for a fresh one — poll run
   status instead, it's unambiguous):

   ```bash
   gh run list --branch <branch> --limit 10 \
     --json databaseId,name,status,conclusion,headSha,createdAt,updatedAt
   ```

   Filter to `headSha == <new SHA>` and `name == "Running Copilot Code
   Review"`. If re-review was requested more than once for the same
   commit (e.g. after the discovery-timeout fallback below), more than
   one matching run can exist — pick the one with the highest
   `databaseId`/latest `createdAt`, not just any match, or a stale
   run's conclusion can be read as if it were the fresh one.

   Do **not** gate on the separate `CI` aggregate run reaching
   `completed`: that workflow can't finish until every job in it does,
   including non-required supporting jobs (`performance`,
   `quality-summary`) that are allowed to fail by design (§5, §7) — using
   it as a stop condition makes those jobs an unintended blocker/timing
   floor. Use `gh pr checks <number>` directly against the required-jobs
   list instead; it reflects each job's own state without waiting on
   slower non-required jobs to finish first.

   Poll like this, not with one long fixed sleep:
   - First check after a short delay (~20-30s) — cheap, catches the many
     small-diff review cases that finish in under 2 minutes; `gh pr
     checks` for required jobs on this repo's small/doc-only PRs is often
     already green by then too (~40-90s typical for the full required set
     regardless of PR size).
   - If no matching `Running Copilot Code Review` run for this SHA has
     appeared yet after ~60-90s (distinct from one appearing and still
     being `in_progress`), don't keep waiting out the full 12-minute cap
     assuming it's merely queued — this can mean automatic re-review
     didn't trigger for this push. Immediately issue the
     `requested_reviewers` call from step 7 (if not already done for this
     SHA) and keep polling for the newest run it creates.
   - Otherwise keep polling every 20-30s.
   - After ~2.5-3 minutes total (roughly 70-80% of the historical average
     for this repo), it's fine to space checks out to ~45-60s apart to
     cut down on tool-call volume for the long tail.
   - Cap at ~12 minutes on the review run; if still not completed by
     then, report this to the user rather than continuing to poll
     silently — it may indicate a stuck run.
   - `status: completed` is not the same as success — check `conclusion`
     too. A `cancelled`/`timed_out`/`failure` conclusion on the Copilot
     review run means don't proceed as if freshly reviewed: report it and
     re-request the review instead of silently re-fetching stale threads
     and treating `copilot-review-invoked=true` as sufficient.
   - Stop polling and proceed once the newest matching Copilot review run
     shows `status: completed` with a successful `conclusion`, **and**
     `gh pr checks` shows all *required* jobs passing — don't wait out a
     fixed timer past that point, and don't let a still-running
     non-required job hold things up.

   (Verified empirically across PRs #30/#31/#35: this repo's Copilot
   review surfaces as an `event: dynamic` Actions run named `Running
   Copilot Code Review`, so it does appear in `gh run list`. If a future
   GitHub change stops surfacing it there, fall back to `gh api
   repos/:owner/:repo/commits/<sha>/check-runs` instead.)
9. Re-fetch review threads (§2) to see what's newly resolved/added.
   This closes a **review round**: snapshot this round's thread `id`s,
   band each new finding, and record the per-band counts for §4's
   histogram. Then increment the review round count (§1) — **unless every
   finding fixed in this round was CRITICAL**, in which case the round
   does not consume budget (§4's critical override; without this
   exemption the override cannot actually be executed). Finally, evaluate
   §4's four triggers before starting another round — the budget is
   checked at this boundary, not mid-fix.

## 4. Budget checkpoint

The §1 budget, not a flat commit count, decides when to stop and ask. A
flat count cannot tell #35 (4 trivial rounds, ~10 min) apart from #71
(4 rounds, ~110 min) — they are the same number and nothing like the same
amount of work.

Stop looping immediately — do not start another fix — when **any** of
these fires:

1. **Rounds exhausted.** The review round count reaches the §1 maximum
   for the declared intensity.
2. **Agent-busy budget crossed.** At the next round boundary after
   agent-busy time (§1 time log) exceeds the intensity's minute budget.
   Never mid-round; see §1's "rounds bind, minutes are advisory".
3. **Novelty stall.** Two consecutive non-novel rounds (defined below) —
   the loop has converged and further rounds will not improve it.
4. **Late escalation.** A CRITICAL or HIGH finding appears in the final
   budgeted round. This means the intensity was chosen too low, not that
   one more round will finish the job — so it forces the checkpoint
   rather than a silent budget extension.

### Novelty — the mechanical definition

Snapshot the set of non-suppressed review thread `id`s (§2) after each
round. A round is **novel** if it contains at least one thread whose `id`
was not present in any earlier round this session **and** whose
`code-review` §0 band is at or above the intensity floor. Otherwise the
round is **non-novel**.

Bands below the floor never make a round novel, no matter how many of
them arrive — a round producing eleven LOW prose nits at medium intensity
is non-novel.

One judgement call is allowed on top of the mechanical rule, and it must
be logged: Copilot sometimes re-raises a finding you already fixed as a
*fresh* thread with a new `id`, which the ID rule alone would score as
novel. When you judge a new thread to be a restatement of a finding
already resolved this session, record it as non-novel and name it in the
checkpoint report ("thread X counted non-novel: restates the already-fixed
Y"). Do not make the reverse call — never score a genuinely new thread as
non-novel to reach a stall faster.

### The critical override

A CRITICAL finding (`code-review` §0) is **always fixed**, even past an
exhausted budget. It does not consume budget — mechanically, §3 step 9
skips the round-count increment for a round whose fixes were all CRITICAL
— and it resets the novelty counter to zero. Budgets bound how much
polish a PR gets; they never let a fundamentally broken change through.

A round mixing CRITICAL with lower-band fixes **does** consume its round:
the exemption is for rounds spent solely on CRITICAL, not for any round
that happens to contain one.

### At the checkpoint, report

1. All review-fix commits made so far this session (one line each: SHA or
   message + what it addressed).
2. **Severity histogram** — counts per band per round, and the session
   total. This is the number that tells the user whether the remaining
   work is real.
3. **Open findings by band**, with the current intensity floor marked.
4. **Elapsed vs. budget** — rounds used/max, agent-busy minutes vs. the
   minute budget, and which of the four triggers fired.
5. Current CI status: which required jobs are green/red.
6. A recommendation — continue at this intensity, escalate the intensity
   (state which, and why the original choice was wrong), or stop and
   merge/defer.

Then ask the user, via `ask_user`, whether to continue. Only resume the
loop (§3) on an explicit yes — do not assume. Record this as a waiting
interval in the time log (§1).

If the user says continue, they are granting a **new budget**, not an
unlimited one: re-baseline at the same intensity (its full round and
minute allowance again) unless they name a different one, and
re-checkpoint when that budget is spent.

## 5. Exit criteria for the loop

The loop (§3) is done only when, on a fresh fetch:
- `copilot-review-invoked=true` (balanced Copilot review was explicitly
  requested on this PR).
- `gh pr checks <number>` shows all required jobs passing (no pending
  jobs either — wait them out). Required jobs in this repo's `ci.yml`:
  `lint`, `complexity`, `typecheck`, `security`, `dependency-scan`,
  `test (3.9)`, `test (3.10)`, `test (3.11)`, `test (3.12)`, `build`,
  `docs`, plus `Analyze (python)` and `CodeQL`. **There is no check named
  plain `test`** — `013-tox-multi-python-testing` converted that job into a
  Python-version matrix, and a matrixed job only ever emits per-leg check
  names, so waiting for a bare `test` entry to appear waits forever.
  `performance` and `deploy-docs`/`quality-summary` are supporting jobs —
  check `ci.yml` if unsure which are branch-protection required. To read
  the authoritative list rather than trusting this one:
  `gh api repos/:owner/:repo/rulesets/19477007 --jq '[.rules[] |
  select(.type=="required_status_checks") |
  .parameters.required_status_checks[].context]'`
- No unresolved, non-suppressed Copilot review comments remain (§2).
- A fresh `gh pr view <number> --json mergeable,reviewDecision` shows
  `mergeable=MERGEABLE` and `reviewDecision` is not `CHANGES_REQUESTED`
  (re-fetch these two fields explicitly here — the values captured back
  in §1's setup step can go stale after a force-push, a base-branch
  update, or a maintainer's own review since the loop started).

Do not treat "PR looks fine to me" as sufficient — always do the fresh
`gh pr checks` + review-thread re-fetch before declaring done.

## 6. Closure — never automatic

Once §5's exit criteria are met, the PR is *ready* to close/merge, but you
must not merge, close, or delete anything yet.

1. Produce a high-level summary of **all** changes/commits on the PR
   (not just this session's fixes) — pull the full commit list:
   `gh pr view <number> --json commits --jq '.commits[].messageHeadline'`
   and group it into a short narrative (what the PR does overall, then
   what was fixed during review iteration). Confirm CI status and review
   status explicitly in that summary (green checkmarks, 0 unresolved
   required comments). Present this narrative in chat.
2. Ask the user for explicit approval via `ask_user` — do not merge/close
   on an assumption of approval, and do not proceed on a vague or partial
   answer. Record the moment this question is asked as the start of the
   **closure-approval** waiting interval in the time log (§1); its end is
   whenever the user responds.

Only after explicit approval:

1. Merge/close the PR per the user's stated preference (e.g.
   `gh pr merge <number> --squash` — confirm merge method if not already
   agreed).
2. Delete the now-stale remote branch (`gh pr merge --delete-branch`, or
   `git push origin --delete <branch>` if closed without the flag).
3. Clean up local state, in this order: first remove any associated
   worktree (`git worktree remove <path>`), *then* delete the local
   branch. Removing the worktree first avoids "branch is checked out"
   failures, and — since the merge above was a squash (the local branch's
   history is not an ancestor of the updated base branch) — use the
   force form `git branch -D <branch>`, not `-d`, or plain `-d` will
   refuse to delete it. Only use `-d` here if the merge method was a
   true (non-squash) merge or rebase.
4. Re-run `git branch -vv` and `git worktree list` to confirm cleanup.

Note: merged PRs cannot be reopened on GitHub. If post-merge Copilot review is
required, open a follow-up PR and request review there.

Once merge/close and cleanup above are actually complete (not merely
approved), finalize and publish the time accounting — this is the *only*
point where "now" for total wall time should be captured, since it is the
first moment after every step this metric is meant to cover (including
merge, branch deletion, and cleanup) has actually finished:

1. Finalize the time accounting from the time log (§1):
   - **Total wall time** — this "now" minus the loop-start timestamp.
   - **Time agent was working** — total wall time minus all recorded
     human-decision waiting intervals (this includes CI/review polling
     time, since the agent was actively driving that, not blocked).
   - **Time waiting on human decisions** — the sum of the recorded
     waiting intervals (e.g. "ambiguous PR confirmation — 1m", "budget
     checkpoint: continue? — 4m", "closure approval — 2m"), including the
     closure-approval interval closed above.
   Report these three numbers in chat.
2. Post an AIC usage summary comment on the PR using real markdown newlines.
   Do not use inline `--body "...\n..."` strings because GitHub CLI will post
   literal `\n` characters. Always write the comment to a file (heredoc) and
   post with `--body-file`, for example:

```bash
cat > /tmp/pr-aic-summary.md <<'EOF'
## Session usage summary for authoring this PR

### Scope
Covers the PR-authoring session, including review-loop and CI-fix work.

### Time accounting
_(Loop-invocation window only — from this skill's first action to closure,
not the entire PR-authoring session, which may have started earlier.)_
- **Total wall time (this review loop):** <start> -> <end> (~<total_duration>)
- **Agent working time:** ~<working_duration> (drafting fixes, running
  gates, polling CI/Copilot review, committing/pushing)
- **Waiting on human decisions:** ~<waiting_duration> across
  <wait_count> checkpoint(s):
  - <checkpoint description> — ~<duration>
  - <checkpoint description> — ~<duration>

### Review rounds and severity

- **Intensity:** <declared intensity> (<max_rounds> rounds / <minute_budget> min budget)
- **Rounds used:** <rounds_used> / <max_rounds>
- **Checkpoint trigger:** <rounds exhausted | budget crossed | novelty stall | late escalation | none>

| Round | CRITICAL | HIGH | MEDIUM | LOW | Novel? |
|---:|---:|---:|---:|---:|---|
| 1 | <n> | <n> | <n> | <n> | <yes/no> |
| 2 | <n> | <n> | <n> | <n> | <yes/no> |
| **Total** | <n> | <n> | <n> | <n> | — |

### Totals
- **Session turns:** <turn_count>
- **AIC events:** <event_count>
- **Input tokens:** <input_tokens>
- **Output tokens:** <output_tokens>
- **Total AI usage:** <total_aiu> AIU

### By model

| Model | AIC events | Input tokens | Output tokens | AIU |
|---|---:|---:|---:|---:|
| <model> | <events> | <input> | <output> | <aiu> |

### Copilot code-review credits
- **Per-session code-review credit total:** <value or "not separately exposed in local telemetry">.
- **Attribution status:** <how review activity is/is not isolated>.

### Cost note
USD value may be unavailable from local telemetry unless billing rates are available.
EOF
gh pr comment <number> --repo <owner>/<repo> --body-file /tmp/pr-aic-summary.md
rm /tmp/pr-aic-summary.md
```

   Pass `--repo <owner>/<repo>` explicitly (captured during §1 setup) rather
   than relying on the current checkout to infer it — by this point the
   local worktree/branch may already be removed (§6 cleanup runs first),
   so an inferred-repo lookup could fail and silently drop this required
   post-closure comment.

   If prior malformed summary comments exist (literal `\n`), replace them by
   editing the latest summary comment or deleting malformed ones with:
   `gh api repos/<owner>/<repo>/issues/comments/<comment_id> -X DELETE`.
   If the PR was merged (rather than closed without merging), this comment
   necessarily lands *after* the merge — that is expected and fine; it does
   not need to land before merge the way earlier drafts of this skill
   required.


## 7. Anti-patterns to avoid

- Counting all commits (docs typos, rebases) toward the review-fix
  commit count instead of only review/CI-fix commits.
- Treating the agent-busy minute budget (§1) as a hard stop and abandoning
  a round half-finished — rounds bind, minutes only bring the §4
  checkpoint forward to the next round boundary.
- Fixing a finding without banding it first (`code-review` §0) — §4's
  histogram and novelty check both read the bands, so an unbanded fix
  leaves the budget unaccountable. (An unbanded finding still gets fixed:
  `code-review` §0 defaults it to the floor, not to LOW.)
- Treating a resolved-but-still-`isOutdated:false`-with-new-diff thread as
  settled — GitHub can silently re-open relevance after a force-push;
  always re-fetch after pushing.
- Ignoring a Copilot comment because it "seems minor" without it actually
  meeting a suppression criterion from §2.
- Merging, closing, or deleting branches/worktrees without a fresh,
  explicit user approval in the same session.
- Treating `performance` job or opt-in test suites as blocking when they
  are not part of required status checks (verify in branch protection or
  `ci.yml` before treating a red non-required job as a blocker).
- Blind-sleeping a fixed 4-5 minutes after every push "to be safe" before
  checking CI/review status. Copilot review latency in this repo ranges
  from ~1-2 min (small/single-file diffs) to ~8-10 min (large multi-file
  diffs) — a fixed long sleep wastes idle time on the common fast case and
  still isn't safe for the slow tail. Use the adaptive polling in §3 step
  8 instead.
- Inferring whether a new Copilot review has landed by comparing review
  `submittedAt` timestamps against a remembered "latest so far" value —
  it's easy to re-fetch too early, see the same stale review, and
  misread it as "already reviewed, must be up to date." Poll the
  `Running Copilot Code Review` Actions run's `status`/`conclusion`
  fields for the pushed commit's SHA instead — unambiguous completion
  signal, no timestamp bookkeeping required.
- Counting CI-polling or Copilot-review-polling time as "waiting on human
  decisions" in the closure time accounting — the agent is actively
  driving those waits, so they belong in agent working time, not human
  waiting time.
- Forgetting to close out a recorded waiting interval (no matching
  `wait-end`) before computing closure totals. Total wall time is fixed by
  the loop-start/loop-end timestamps regardless, but an unclosed interval
  can't be counted toward human-waiting time, so its duration is silently
  misattributed to agent working time instead (understating the former,
  overstating the latter).
- Capturing the loop-start timestamp after the ambiguity confirmation in
  §1, or finalizing total wall time right after closure approval instead
  of after merge/close and cleanup actually finish — both under-measure
  the metric by excluding a real span of the session it is meant to cover.
