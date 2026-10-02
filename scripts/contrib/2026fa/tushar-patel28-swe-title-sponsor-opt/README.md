---
owner: tushar-patel28
term: 2026fa
component: swe-title-sponsor-opt
status: DRAFT
promoted_to: null
---

# swe-title-sponsor-opt — sponsored-title check with an OPT-start timeline gate

## Executive summary

**What this is.** A small offline tool for an international student looking for software, AI or cloud jobs. For each job opening on the student's list it asks two questions. First, does the company's public visa-sponsorship history include a job title in the student's field? Second, does the start date fall inside the student's work-permit window? It then hands the answers to the project's existing scoring tool and writes a report with a next step per opening.

**Why read it.** It shows how to run the tool and its tests, and it lists every definition the student still has to approve before the results mean anything.

**What it does and doesn't decide.** It never says a company "does not sponsor". Missing data is reported as unknown. It never marks an opening ready to apply until a person has confirmed the posting is still live. With today's definitions no opening can reach a plain "Apply": the data has no filing years, so the strongest sponsorship level it supports is "likely". The date arithmetic is for planning and is not immigration advice.

## Run (from the repo root)

```bash
python3 scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/title_sponsor_opt.py
```

Defaults: the fictional persona and candidate roles in `sample/`, `crosswalk.json`, `mappings.json`, the 80 Days CSV, and the BLS compact table. Output goes to `course/2026fa/submissions/tushar-patel28/runs/`:

| File | For | What |
|---|---|---|
| `roles.json` | scorer | role-evidence records shaped like `data/examples/ch11-roles.json`, plus extra evidence fields the scorer ignores |
| `role-scores.json`, `role-scores.md` | provenance | written by the **real** scorer CLI (`npm run score -- … --out-dir …`), unchanged |
| `swe-title-sponsor-opt-<date>.json` | agents | every input, gate result, label, and the scorer trace |
| `swe-title-sponsor-opt-<date>.md` | human | executive summary, decision table, next action per role, BLS wage context |

Every input path can be overridden: `--persona --roles --crosswalk --mappings --csv --bls --out-dir`. Exit codes: `0` ok (per-role input errors are reported, not fatal), `2` bad inputs/config, `3` scorer failed or a guard tripped.

## Test (from the repo root)

```bash
python3 -m unittest discover -s scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/tests -v
```

The suite is offline. Every end-to-end test runs the real scorer CLI into a temp dir. It covers:
- one test per failure case F1–F6 from the change brief;
- one deliberate break per gate: G1 near-miss/namesake/ambiguous, G2 band edges and bad dates, G3 an input that claims liveness was checked;
- a labels check over the whole agent log;
- three `BROKEN-*` mutant scorers that must each be rejected by a guard.

## Files

| Path | Label | Role |
|---|---|---|
| `title_sponsor_opt.py` | — | the one-command pipeline |
| `crosswalk.json` | your-input | title keywords → SWE / AI / Cloud (`[TODO: DEFINE]` in the recipe) |
| `mappings.json` | your-input | evidence → tier/p, fit p, timeline bands, liveness assumption, next-action rule |
| `sample/persona.json`, `sample/candidate-roles.json` | your-input | fictional persona; real company names, fictional postings |
| `fixtures/` | — | test fixtures and mutant scorers (see `fixtures/README.md`) |
| `tests/test_title_sponsor_opt.py` | — | unittest suite |

## Reused maintained code (not copied)

- `normalize_company_name` + `COMPANY_SUFFIXES` from `scripts/sec/sec-all-quarters.py`. They're extracted with `ast` and executed, because that module imports pandas at top level and pandas isn't installed.
- `present` / `h1b_present` / `H1B_COLUMNS` from `scripts/sec/validate-h1b-join-sample.py` (stdlib only, imported directly).
- The scorer `scripts/score/role-scorer.mjs`, always through `npm run score`, never with `--profile`.

## F6: the "work authorized" scorer bug (documented reproduction)

`applyProfile` in `scripts/score/role-scorer.mjs` treats any profile whose `authorization` text matches `/authorized/` as not needing sponsorship. That sets the sponsorship weight to 0. An F-1 profile written as "F-1 STEM OPT — work authorized (EAD)" trips it. Observed during recon on 2026-10-01 (output to `/tmp`, nothing tracked changed):

```
node scripts/score/role-scorer.mjs data/examples/ch11-roles.json --out-dir /tmp/score-recon-profile \
  --profile <(echo '{"authorization":"F-1 STEM OPT — work authorized (EAD)"}')
→ profile_needs_sponsorship: false
→ biotech-data 0.1785 Skip   (without --profile: 0.446 Apply)
```

The same effect, reproduced without `--profile` by the mutant in this folder:

```
node scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/fixtures/BROKEN-sponsorship-weight-zero.mjs \
  data/examples/ch11-roles.json --out-dir /tmp/tspo-mut
→ sponsorship weight 0 · biotech-data Skip
```

This tool never passes `--profile`. It also refuses to run if `--profile` ever appears in the scorer command, and it fails (exit 3) if any sponsorship term in the scorer output has weight 0. The scorer itself isn't patched here.
