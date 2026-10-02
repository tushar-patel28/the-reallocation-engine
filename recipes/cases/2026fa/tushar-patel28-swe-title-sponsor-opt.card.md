# Sponsored-title and OPT-timeline check — human card

## Executive summary

**What this is.** The one-page guide for the person who decides what to do with each job opening on their list. A tool reads two public data sets and the person's own definitions. For each opening it tells you whether the company's visa-sponsorship history includes a job title in your field, and whether the start date fits your work-permit window. It then suggests one next step: tailor an application, network into the company, or skip.

**Why read it.** The tool deliberately stops short of three decisions that are yours: whether a matched company really is the company you mean, whether a posting is still open, and whether its own definitions are right. This card says where each of those decisions sits and what to look at.

**What it decides and what it doesn't.** It never says a company "does not sponsor": no match, no data and two possible matches are all reported as unknown. It can't tell you whether a company sponsors your exact occupation, because the data lists only a few job titles per company. Under today's definitions nothing reaches a plain "Apply". The date arithmetic is for planning and is not immigration advice.

**Audience:** the student (and a reviewer) deciding where to spend application hours.
**Agent twin:** `recipes/cases/2026fa/tushar-patel28-swe-title-sponsor-opt.md`
**Chapters:** 7 (sponsorship tiers; Unknown is not Avoid), 10 (timeline as a gate), 11 (the scorer that combines them).

## Purpose

Answer two questions for each opening, with every value labelled by where it came from:

1. Does a title in my family (Software, then AI, then Cloud) appear in this company's top sponsored titles?
2. Does the start date fall within 0–90 days after the persona's EAD start?

## What it can verify

- Whether your company name, normalized the way the repository normalizes names, matches zero, one, or several rows in the sponsorship data.
- Whether the matched row has any sponsorship trace at all.
- Whether one of the company's few top sponsored titles matches *your* keyword list for the family.
- How many days after your EAD start the role begins, and which band that falls in.
- That the project's real scorer used exactly the gates the tool sent, and that the sponsorship vote kept its weight.

## What it cannot verify

- **Sponsorship for your occupation.** There is no occupation code in the data, only a short list of top titles per company, with no counts per title. Lists hold 1 to 14 titles, and 867 of the 1,557 companies with sponsorship data list just one.
- **How much, or how recently, a company sponsors.** There are no filing years, and the approval counts look double-counted, so they are not used.
- **Whether a posting is real or open.** That is G3, and only you can clear it.
- **Whether a match is the right company.** That is the G1 check: confirm name, city and state.
- **Your immigration position.** Confirm dates and the 90-day allowance with your DSO.

## Dependencies

- The 80 Days sponsorship file (company-level; 1,557 of 30,369 rows have sponsorship data).
- The BLS occupation table (median wages; context only, not in the score).
- The project's scorer (unchanged), and the repository's own name normalizer.
- Your definitions: the title keyword list and the mappings. Both are labelled as your input.

## Annotated commands

```bash
# Run the check on the sample list (fictional persona, real company names, fictional postings).
python3 scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/title_sponsor_opt.py
#   → prints roles in / scored / not scored, the scorer's counts, and the next-action counts,
#     then the paths of the report (for you) and the log (for agents).

# Prove the checks catch what they claim to catch (offline).
python3 -m unittest discover -s scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/tests -v

# Clear G3 yourself, one posting at a time, before you act on it (network call).
npm run ats:liveness -- <posting_url>
```

## What it produces

- **A report for you.** It contains:
  - a plain-language summary;
  - a decision table showing, per opening, the company match, the family check, start date vs EAD, the timeline factor, liveness (assumed), the votes, the score, the scorer's recommendation, the decision shown to you, and the next action, each with its label;
  - the arithmetic behind every score;
  - the matched rows to confirm;
  - median wages per family as context.
- **A log for agents.** It contains every input, with a fingerprint per file, every gate result, and the scorer's own output, unchanged.

## Named failure modes

| # | What goes wrong | What you see | What to do |
|---|---|---|---|
| F1 | Company not in the data (e.g. "Google") | `not-found`, tier Unknown, no sponsorship vote | Not evidence against sponsorship. Look for a direct signal (careers page, recruiter). |
| F2 | Company in the data with no sponsorship trace | `no-h1b-trace`, Unknown | Same as F1 |
| F3 | Start date before your EAD start, or more than 90 days after | timeline factor 0, gated Skip | Skip, or ask whether the start date can move, then re-run |
| F4 | Start date missing or invalid (e.g. "TBD") | error naming the role; not scored | Get a real date; the tool will not guess one |
| F5 | Title list unreadable | `titles-unreadable`; no family claim | Treat as unknown for your family |
| F6 | The scorer's "work authorized" bug would zero sponsorship for an F-1 profile | the run stops with an error if it ever happens | Nothing to do; the tool never passes a profile and checks the weight every run |
| — | Two rows match one name (e.g. "Salesforce.com, Inc.") | `ambiguous`; next action "pick the right company row" | Choose the row; an alias file is a proposed addition |
| — | Namesake (e.g. "Cohere" vs "Cohere Health") | exact match only, so `not-found` | Use the company's full legal name if you mean the one in the data |

## What you still decide

These are open definitions, all labelled your-input in the outputs:
- the title keyword list per family;
- the mapping from evidence to sponsorship tier and probability (the strongest tier the data supports today is "Likely");
- the fit values for your priority order (0.8 / 0.7 / 0.6);
- the reasoning behind the timeline bands you supplied;
- the next-action rule.

## Next action per result

- **Tailor an application:** only after you confirm the company row and run the liveness check on the posting.
- **Network into the company:** sponsorship for your family is unknown or only possible. Ask about it directly.
- **Skip:** the start date is outside your window, or the evidence is too thin for a lower-priority family.
- **Blocked:** fix the input (a date) or pick the company row, then re-run.
