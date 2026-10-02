---
status: DRAFT          # sample run succeeded 2026-10-01, but SNICKERDOODLE requires zero open TODOs before SPECIFIED, and RUNNABLE-SAMPLE also needs a run-log entry and a human reading of the run report. See "Lifecycle evidence".
todos_open: 7
last_gate: null
attestation: null
recipe_version: 0.1.0
---

# tushar-patel28-swe-title-sponsor-opt — sponsored-title check with an OPT-start timeline gate

## Executive summary

For each job opening on an international student's list, this recipe answers two questions:

1. Does the company's H-1B record list a sponsored job title in the student's role family? The families, in priority order, are Software, then AI, then Cloud/Infrastructure.
2. Does the role's start date land inside the student's OPT window?

It labels every value by where it came from and runs the repository's existing scorer unchanged. It stops at a human gate before anything is marked Apply. It never says a company "does not sponsor": missing data is unknown. Under the current definitions no role can reach a plain Apply, because the data has no filing years and so cannot support the strongest sponsorship tier. The timeline arithmetic is planning arithmetic, not immigration advice.

Chapters claimed: **Ch 7** (sponsorship tier, Unknown ≠ Avoid) and **Ch 10** (visa timeline as a gate), combined by the **Ch 11** scorer. BLS wages (Ch 9) appear as context only, because the scorer's `role_quality` weight is 0.

Two customers: this file is for the agent; `recipes/cases/2026fa/tushar-patel28-swe-title-sponsor-opt.card.md` is for the human. The spec is `course/2026fa/submissions/tushar-patel28/CHANGE-BRIEF.md`; its predictions are never edited.

**Handoff condition (done when):** a sample run is complete when all of the following hold. "Looks right" is not the condition.
- Stdout prints `roles · scored · not scored` with counts that sum to the input count.
- `roles.json` holds exactly the roles that passed input validation.
- The real scorer CLI wrote `role-scores.json` in the same run.
- Both guards pass (sponsorship weight > 0 on every sponsorship term; every timeline = 0 role is a gated Skip).
- The agent log has zero unlabelled values.
- The report opens with an executive summary and shows every Apply or "tailor" action as blocked at G3.

## Required reads

Read in this order before running:

1. `SNICKERDOODLE.md` — gates, provenance, TODO closure.
2. `DOMAIN.md` — layout; known gaps #3 (role_quality weight 0) and #9.
3. `course/2026fa/submissions/tushar-patel28/CHANGE-BRIEF.md` — the spec: gates, failure cases F1–F6, predictions P1–P4.
4. `book/chapters/07-who-sponsors-the-80-days-sponsorship-scorer.md` — the tier definitions and the rule that Unknown is not Avoid.
5. `data/80-days-to-stay/data/SEC_DOL_H1b_data_mapped-entity-resolution-readiness-audit.md` — why there is no SOC field.
6. `scripts/score/role-scorer.mjs` — input shape, tier names, gates, and the `applyProfile` "authorized" bug.
7. This recipe and its card.

Prefer those local files over external lookup. Do not read `private/` or `search/resume.json`.

## Source inventory

| Source | Exact path | Label | Used for |
|---|---|---|---|
| 80 Days sponsorship CSV (30,369 rows; 1,557 with H-1B fields) | `data/80-days-to-stay/80-days-csv/mapped_student_employment_targets_v3.csv` | record | G1 entity match; `top_job_titles_sponsored` |
| BLS / O*NET compact table | `data/bls/compact/soc_occupation_compact.csv` | record | median wage per family (context only) |
| Company-name normalizer | `scripts/sec/sec-all-quarters.py` :: `normalize_company_name`, `COMPANY_SUFFIXES` | record (maintained code) | G1 key, executed via `ast` because the module imports pandas |
| H-1B presence check | `scripts/sec/validate-h1b-join-sample.py` :: `present`, `h1b_present`, `H1B_COLUMNS` | record (maintained code) | matched-h1b vs no-h1b-trace |
| Scorer | `scripts/score/role-scorer.mjs` via `npm run score -- <roles.json> --out-dir <dir>` | record (its output) | composite, recommendation, audit trace |
| Liveness check (human, at G3) | `npm run ats:liveness -- <posting_url>` | record (when run) | clearing G3; **not run by this recipe** |
| Title → family crosswalk | `scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/crosswalk.json` | your-input | family check |
| Mappings (tier/p, fit p, timeline bands, liveness assumption, next action) | `scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/mappings.json` | your-input | votes, G2, decisions |
| Persona (fictional) | `scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/sample/persona.json` | your-input | EAD start date |
| Candidate roles | `scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/sample/candidate-roles.json` | your-input | company, title, family, start date, posting URL |

**Deliberately not used:**
- **Form D funding.** The shipped samples join on name alone: 15 of 200 matched, with only one sponsoring company.
- **H-1B approval counts.** Every approval and denial value in the CSV is even, which suggests double counting. Sponsorship is read as present or absent, never as a size.
- **`--profile`.** The scorer's authorization regex zeroes the sponsorship weight for "work authorized" F-1 text (F6).

## Phase gates

Each role stops at the first failed gate. There is no fallback and no default.

| Gate | Test | Pass | Fail |
|---|---|---|---|
| Input | `company`, `title`, `role_family` ∈ {SWE, AI, Cloud}, `posting_url` present; `role_id` unique | role proceeds | error naming the role; **not sent to the scorer** |
| G1 entity | `normalize_company_name(company)` equals the key of **exactly one** CSV row | `matched-h1b` if any H-1B column is present, else `no-h1b-trace` (unknown). A human must still confirm the row's name, city and state (namesake check). | `not-found` (0 rows) → tier Unknown, no sponsorship vote; `ambiguous` (2+ rows) → tier Unknown, no vote, next action "pick the right company row" |
| Family check (matched-h1b only) | `ast.literal_eval(top_job_titles_sponsored)` gives a non-empty list of strings; any title matches a crosswalk pattern for the role's family | `in-top-titles`: "a title in this family appears in the company's top sponsored titles" | `not-in-top-titles` → "not in top titles (unknown)"; parse failure → `titles-unreadable`, no family claim |
| G2 timeline | `start_date` is `YYYY-MM-DD` and valid; `days = start − EAD start` falls in exactly one band | factor 1.0 (0–60 days) or 0.6 (61–90 days) | factor 0 (before the EAD start, or > 90 days), which the scorer turns into a gated Skip; missing or invalid date → error naming the role, not scored |
| G3 liveness (human) | `npm run ats:liveness -- <posting_url>` has been run by a human and logged | the role may be acted on | **always fails offline.** Liveness is sent as `{factor: 1.0, source: "your-input", assumed: true, checked: false}`, and every Apply or "tailor" action is shown as "blocked at G3 until npm run ats:liveness is run by a human". |
| Scorer guards | every sponsorship term in `role-scores.json` has weight > 0; the scorer echoes exactly the gates sent; every timeline = 0 role is `Skip` with reason `gated: timeline` | report is written | exit 3; no report (a broken or mis-configured scorer must not produce decisions) |

## Definitions (open)

Each of these is a human decision. Claude proposed the values on 2026-10-01; the human closes each with one sentence of reasoning.

- **Crosswalk:** `crosswalk.json`. Regex keywords per family; SWE ≈ "software engineer/developer, backend, frontend, full stack…", AI ≈ "machine learning, ML, AI, applied/research scientist, data scientist…", Cloud ≈ "cloud, devops, site reliability, infrastructure, platform engineer…". A bare "Engineer" maps to no family. The data has no SOC field, so this file *is* the definition. [TODO: DEFINE]
- **Sponsorship evidence → tier and p:** tier names come from the scorer (`soft_sponsorship_tiers: likely / possible / unknown`; `data/examples/ch11-roles.json` uses Proven / Likely / None). [TODO: DEFINE] Proposed:

  | Evidence state | Tier | p | Reasoning |
  |---|---|---|---|
  | matched-h1b + in-top-titles | Likely | 0.6 | H-1B trace plus a title in my family. Not Proven: Ch.7's Proven needs "strong, recent filing history", and the CSV has no filing year and possibly double-counted counts. 0.6 is the Likely value in the Ch.11 example. |
  | matched-h1b + not-in-top-titles | Possible | 0.4 | The company does sponsor, but my family is not in a list of only a few titles. 0.4 is a proposal below Likely; **no record produced it**. |
  | matched-h1b + titles-unreadable | Possible | 0.4 | Same evidence, with no family claim possible. |
  | no-h1b-trace / not-found / ambiguous | Unknown | none (no vote) | No evidence either way. Never Avoid/None: the upstream README says empty fields do not mean non-sponsorship. Sending p = 0 would assert non-sponsorship. |

  Consequence: the best composite is (0.6·0.35 + 0.8·0.3) × 1 × 1 = 0.45, and the scorer demotes Likely to Consider. **No role can be a machine Apply** until a human supplies evidence for Proven, for example a recent LCA record checked by hand.
- **Fit p:** SWE 0.8, AI 0.7, Cloud 0.6. This encodes the priority order SWE > AI > Cloud as equal steps. The top value is 0.8, not 1.0, because a family preference says nothing about fit to a specific posting. Labelled your-input, not model-judgment. [TODO: DEFINE]
- **Timeline bands:** values supplied by the human in the build request (2026-10-01): before the EAD start → 0; 0–60 days → 1.0; 61–90 → 0.6; > 90 → 0. Proposed reasoning: 90 days is the post-completion OPT unemployment allowance, and the 61–90 band is softened because the clock is nearly spent. Note that the scorer treats a factor < 0.6 as a "soft spot", so 0.6 itself is *not* soft. The human must confirm the reasoning. [TODO: DEFINE]
- **Next action:** scorer Apply, or Consider with tier Likely → "tailor an application" (Ch.7: Likely justifies targeted effort), always shown blocked at G3. Consider with Possible/Unknown → "network into the company" (Ch.7: Unknown gets "a different kind of attention"). Skip → "skip". Two outcomes sit outside the three-action set: an ambiguous G1 → "blocked: pick the right company row, then re-run"; an input error → "blocked: fix the input and re-run". [TODO: DEFINE]

## Proposed additions

- **Timeline factor from dates.** ~~Proposed in the brief as DEV~~ **closed 2026-10-01**: `g2_timeline()` in `title_sponsor_opt.py` exists, conformance passes, tests cover every band edge and bad-date input, and the handoff condition above was met by the sample run.
- **Human liveness results file.** Accept a file of `npm run ats:liveness` results recorded by a human (URL, date, result, who) so G3 can be cleared per role and the block text dropped only for those roles. Without it, G3 can never clear inside this recipe. [TODO: DEV]
- **Company alias table.** A human-maintained file mapping a posting's company name to a chosen CSV row, or to "not in this dataset". It would resolve `ambiguous` cases such as `SALESFORCE COM INC` vs `SALESFORCECOM INC` and record that, for example, "Google" has no row. Each alias is your-input; the code is DEV. [TODO: DEV]

## Primary stored tools

```bash
# the run (from the repo root)
python3 scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/title_sponsor_opt.py
# tests (offline; each end-to-end test calls the real scorer CLI into a temp dir)
python3 -m unittest discover -s scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/tests -v
# conformance
node scripts/conformance.mjs scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/ recipes/cases/2026fa/
# G3, by a human, per candidate the human wants to act on (network call — not run by this recipe)
npm run ats:liveness -- <posting_url>
```

## Workflow

1. Check the inputs: persona `ead_start_date`, crosswalk patterns compile, every evidence state has a mapping, and the CSV has the required columns. Any failure stops the run (exit 2).
2. For each role, run the input gate, G1, the family check and G2, and record each result with its label.
3. Write `roles.json` with only the roles that passed. Sponsorship carries tier and p (or `p: null` for Unknown), fit carries p, liveness is assumed, timeline carries the computed factor. Evidence goes in extra fields, which the scorer ignores.
4. Run `npm run score -- <roles.json> --out-dir <runs dir>`, never with `--profile`. Read `role-scores.json`.
5. Run the guards (sponsorship weight > 0, gate echo, gated Skip on timeline 0). If one fails, exit 3.
6. Write the agent log and the human report.
7. The human confirms G1 rows, reads the report, runs liveness for any role they want to act on, and logs the run.

## Output contract

All outputs are written to `course/2026fa/submissions/tushar-patel28/runs/`:

- **`roles.json`:** an array shaped like `data/examples/ch11-roles.json`. Every term carries a `source` from {record, model-judgment, your-input}.
- **`role-scores.json`, `role-scores.md`:** written by the scorer, unchanged. (`role-scores.md` is the scorer's own format and has no executive summary; that's a scorer-side gap, not changed here.)
- **`swe-title-sponsor-opt-<date>.json` (agents):**
  - top-level blocks `run`, `inputs` (with SHA-256 per file), `dataset_context`, `bls_context`, `roles[]`, `scorer_run`, `summary`;
  - each role carries `input`, `g1_entity`, `family_check`, `sponsorship_vote`, `fit_vote`, `g2_timeline`, `g3_liveness`, `scorer` (verbatim) and `decision`, or `error`;
  - every scalar sits inside an object `{value, source}`.
- **`swe-title-sponsor-opt-<date>.md` (human):**
  - an executive summary first;
  - a label legend;
  - a decision table: role, family, G1, family check, start vs EAD, timeline factor, liveness, votes, composite, scorer recommendation, shown decision, next action — each with its label;
  - the per-role audit arithmetic;
  - the G1 rows to confirm;
  - the top titles behind each family check;
  - roles not scored;
  - BLS median wage per family, labelled record and kept out of the score;
  - dataset-level family coverage;
  - what the run cannot tell you;
  - the run record.
- **Labelling rule:** a value read from a data file, or the scorer's output, is `record`. A value that depends on a definition the human wrote (crosswalk match, tier, p, timeline factor, next action) is `your-input`, even when its inputs include records. `model-judgment` is not used.
- **Not emitted:** any approval count as a magnitude; any "does not sponsor"; any machine Apply shown without the G3 block.

## What it can verify

- Whether a company name, normalized by the repository's own normalizer, matches zero, one, or several rows.
- Whether that row carries any H-1B trace.
- Whether a title matching the human's crosswalk for a family appears in the company's top sponsored titles.
- Where a start date falls relative to the EAD start, under the stated bands.
- That the real scorer used exactly the gates sent, and that sponsorship kept a non-zero weight.

## What it cannot verify

- Sponsorship for an occupation (SOC). The data has no SOC field; the closest is a list of a few top titles with no per-title counts. This matches `recipes/cases/2026su/case-ml-sponsorship-triage.md` ("ML-specific SOC sponsorship until LCA-by-SOC tooling exists").
- How much or how recently a company sponsors: there's no filing year, and the counts are suspect.
- Anything about a company that is absent, has no trace, or is ambiguous: these are unknown.
- Whether a posting is live (G3 is human-only), or whether a matched row is the same company and not a namesake (G1 human check).
- Immigration eligibility. The timeline is planning arithmetic, not advice; the student confirms with their DSO.

## Verification checks

- Conformance: `node scripts/conformance.mjs scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/ recipes/cases/2026fa/`.
- F1 an invented company → `not-found`, tier Unknown, no sponsorship vote.
- F2 Hugging Face → `no-h1b-trace`, no vote.
- F3 day −1 and day 91 → factor 0 → real scorer `Skip`, reason `gated: timeline`.
- F4 missing, `2027-02-30` and `next spring` → error naming the role, not sent to the scorer.
- F5 the truncated title list in the fixture → `titles-unreadable`, no family match.
- F6 the guard passes on the real scorer; `BROKEN-sponsorship-weight-zero` is rejected.
- G1 break: `Databricks Labs` and `Cohere` → `not-found` (no fuzzy matching, no namesake); Salesforce → `ambiguous`.
- G2 break: every band edge (−1, 0, 60, 61, 90, 91); `BROKEN-timeline-ignored` and `BROKEN-gate-zero-off` are rejected.
- G3 break: a role file claiming `liveness_checked: true` is ignored; every Apply or tailor action is shown blocked.
- PII: `node scripts/pii-scan.mjs` adds no finding. Fixture rows have `phone`, `executive_officers` and `board_directors` removed.

## Stop conditions — and the next action per result

| Result | Stop? | Next action |
|---|---|---|
| Persona EAD start missing or invalid; crosswalk or mappings missing an entry; CSV missing a column | stop, exit 2 | fix the definition or input; an upstream schema change is logged as a blocker |
| Scorer exits non-zero, or a guard trips (weight 0, gate mismatch, timeline 0 not gated) | stop, exit 3, no report | do not use any decision; check for `--profile`, a scorer change, or a stale mutant; log it |
| Role input error (missing or invalid date, missing field, bad family) | that role only | "blocked: fix the input and re-run". Never default a date. |
| G1 `ambiguous` | role scored with no sponsorship vote | "blocked: pick the right company row, then re-run" (the proposed alias table) |
| G1 `not-found` or `no-h1b-trace` | role scored with no sponsorship vote | per scorer: Consider → "network into the company" and look for a direct sponsorship signal; Skip → "skip". Never record "does not sponsor". |
| `not-in-top-titles` / `titles-unreadable` | role scored as Possible | usually "network into the company"; ask about sponsorship for this role family directly |
| G2 factor 0 | scorer gated Skip | "skip" this posting. If the start date is negotiable, ask about it, then re-run with the new date. |
| Consider with Likely, or Apply | role scored | "tailor an application — blocked at G3 until npm run ats:liveness is run by a human" |
| Asked to pass `--profile`, use approval counts as magnitudes, fuzzy-match names, or default a date | refuse | each would put a number in the output that no record produced |

## Logging rules

- Do **not** edit `logs/RUN_LOG.md`. Add `logs/runs/2026fa-tushar-patel28-<n>.md` for every sample or break-test run.
- Machine log and human report: `course/2026fa/submissions/tushar-patel28/runs/swe-title-sponsor-opt-<date>.{json,md}`.
- Never log `private/`, `search/resume.json`, real contact details, or the real student's dates. Use the fictional persona only.

### Run-log template (`logs/runs/2026fa-tushar-patel28-<n>.md`)

```markdown
## YYYY-MM-DD — swe-title-sponsor-opt sample run

- **Recipe:** recipes/cases/2026fa/tushar-patel28-swe-title-sponsor-opt.md v0.1.0
- **Inputs:** sample/persona.json, sample/candidate-roles.json, crosswalk.json, mappings.json (sha256 from the run log), 80 Days v3 CSV, BLS compact
- **Command:** python3 scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/title_sponsor_opt.py
- **Outputs:** course/2026fa/submissions/tushar-patel28/runs/ (roles.json, role-scores.{json,md}, swe-title-sponsor-opt-<date>.{json,md})
- **Result:** <roles in / scored / not scored; scorer Apply·Consider·Skip; next actions; guards passed>
- **Gates:** G1 rows confirmed by <name> (<n> of <m>); G3 liveness run for <list> by <name> — or "not cleared"
- **Predictions:** P1–P4 confirmed / contradicted, one line each
- **Open issues:** <open TODOs, defects found>
```

## Lifecycle evidence

- **2026-10-01 sample run:** succeeded. Exit 0; 12 roles, 11 scored, 1 not scored (start date "TBD"); scorer Consider 8 · Skip 3; both guards passed. 23 offline tests pass.
- **Why still DRAFT:** seven typed TODOs are open. SPECIFIED requires zero, with each closure's evidence. RUNNABLE-SAMPLE further needs a run-log entry and a human reading of the run report. Neither exists yet.

## Prior art

These Summer 2026 case recipes are DRAFT templates with no implementation; this recipe neither replaces nor duplicates them:
- `recipes/cases/2026su/case-fullstack-swe-sponsor-triage.md` and `case-backend-swe-opt-triage.md`: SWE sponsor triage before OPT, aimed at the same reader.
- `case-ml-sponsorship-triage.md`, `case-nlp-ml-sponsorship-triage.md` and `case-data-ml-h1b-triage.md`: AI/ML-family triage. The ML case names the SOC gap this recipe works around.
- `case-opt-timeline-fit-company-targeting.md`: timeline fit as a targeting signal. Here it becomes a computed gate.

None matches sponsored titles against a role-family crosswalk, computes `timeline.factor` from dates, or runs the scorer.
