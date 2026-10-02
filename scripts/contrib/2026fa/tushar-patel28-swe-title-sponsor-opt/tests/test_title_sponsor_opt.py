"""Offline tests for title_sponsor_opt.py — one per failure case F1–F6, one deliberate break per gate,
the F-1 sponsorship-weight guard, and BROKEN-* mutant scorers.

Every end-to-end test runs the REAL scorer CLI (npm run score) — never a copy. Mutants are the real
scorer with one string replaced (fixtures/mutant-runner.mjs). All outputs go to temp dirs; nothing in the
repo is written. No network calls.

Run from the repo root:
    python3 -m unittest discover -s scripts/contrib/2026fa/tushar-patel28-swe-title-sponsor-opt/tests -v
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
FIX = PKG / "fixtures"
sys.path.insert(0, str(PKG))

import title_sponsor_opt as tso  # noqa: E402

LABELS = set(tso.LABELS)


def fixture_args(out_dir: Path, **over):
    argv = ["--persona", str(FIX / "persona.fixture.json"), "--roles", str(FIX / "roles-cases.json"),
            "--csv", str(FIX / "sponsorship-fixture.csv"), "--out-dir", str(out_dir)]
    for k, val in over.items():
        argv += [f"--{k.replace('_', '-')}", str(val)]
    return tso.parse_args(argv)


def unlabelled_leaves(obj, path="$", inside=False):
    """Every scalar must sit inside a dict carrying source ∈ LABELS. None marks an absent block."""
    bad = []
    if isinstance(obj, dict):
        labelled = inside or obj.get("source") in LABELS
        if "source" in obj and obj.get("source") not in LABELS and not inside:
            bad.append(f"{path}.source={obj.get('source')!r}")
        for k, val in obj.items():
            bad += unlabelled_leaves(val, f"{path}.{k}", labelled)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            bad += unlabelled_leaves(val, f"{path}[{i}]", inside)
    elif obj is not None and not inside:
        bad.append(f"{path}={obj!r}")
    return bad


class RealScorerRun(unittest.TestCase):
    """One fixture run through the real scorer CLI, shared by the case tests."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="tspo-test-"))
        cls.res = tso.build(fixture_args(cls.tmp))
        cls.log = cls.res["log"]
        cls.by_id = {e["role_id"]["value"]: e for e in cls.log["roles"]}
        cls.sent = {r["role_id"]: r for r in json.loads(cls.res["roles_path"].read_text())}
        cls.scores = json.loads((cls.tmp / "role-scores.json").read_text())
        cls.scored = {r["role_id"]: r for r in cls.scores["roles"]}
        cls.report = cls.res["report_path"].read_text()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ── F1–F6 ────────────────────────────────────────────────────────────────
    def test_F1_not_found_is_unknown_never_does_not_sponsor(self):
        e = self.by_id["f1-not-found"]
        self.assertEqual(e["g1_entity"]["status"]["value"], "not-found")
        self.assertEqual(e["sponsorship_vote"]["tier"]["value"], "Unknown")
        self.assertIsNone(e["sponsorship_vote"]["p"]["value"])
        self.assertNotIn(self.sent["f1-not-found"]["sponsorship"]["tier"], ("None", "Avoid"))
        votes = [x["factor"] for x in self.scored["f1-not-found"]["trace"]["votes"]]
        self.assertNotIn("sponsorship", votes, "an unknown company must not send a sponsorship vote (p=0 would claim non-sponsorship)")

    def test_F2_no_h1b_trace_is_unknown_not_zero(self):
        e = self.by_id["f2-no-trace"]
        self.assertEqual(e["g1_entity"]["status"]["value"], "no-h1b-trace")
        self.assertEqual(len(e["g1_entity"]["matched_rows"]), 1)
        self.assertEqual(e["sponsorship_vote"]["tier"]["value"], "Unknown")
        self.assertIsNone(self.sent["f2-no-trace"]["sponsorship"]["p"])

    def test_F3_outside_window_is_gated_skip_by_real_scorer(self):
        for rid, days in (("f3-before", -1), ("f3-after", 91)):
            with self.subTest(rid):
                self.assertEqual(self.by_id[rid]["g2_timeline"]["days_after_ead_start"]["value"], days)
                self.assertEqual(self.sent[rid]["timeline"]["factor"], 0.0)
                self.assertEqual(self.scored[rid]["machine_recommendation"], "Skip")
                self.assertTrue(self.scored[rid]["reason"].startswith("gated: timeline"), self.scored[rid]["reason"])

    def test_F4_missing_or_invalid_date_is_a_named_error_with_no_default(self):
        for rid in ("f4-missing", "f4-invalid", "f4-text"):
            with self.subTest(rid):
                e = self.by_id[rid]
                self.assertIsNotNone(e["error"])
                self.assertIn(rid, e["error"]["value"])
                self.assertIn("no default", e["error"]["value"])
                self.assertNotIn("g2_timeline", e)
                self.assertNotIn(rid, self.sent, "an errored role must not reach the scorer (it would default timeline to 1)")
                self.assertEqual(e["decision"]["next_action"]["value"], "blocked: fix the input and re-run")
        self.assertIn("matched-in", self.scored, "other roles must still be scored")

    def test_F5_unparseable_titles_claim_no_family(self):
        e = self.by_id["f5-unreadable"]
        self.assertEqual(e["g1_entity"]["status"]["value"], "matched-h1b")
        self.assertEqual(e["family_check"]["status"]["value"], "titles-unreadable")
        self.assertEqual(e["family_check"]["matched_titles"]["value"], [])
        self.assertIn("no family claim", e["family_check"]["claim"]["value"])
        self.assertEqual(self.sent["f5-unreadable"]["sponsorship"]["tier"], "Possible")

    def test_F6_guard_passes_on_real_scorer_and_weight_is_positive(self):
        n = tso.check_sponsorship_weights(self.scores)
        self.assertGreater(n, 0)
        self.assertTrue(self.scores["profile_needs_sponsorship"])
        for r in self.scores["roles"]:
            for vote in r["trace"]["votes"]:
                if vote["factor"] == "sponsorship":
                    self.assertGreater(vote["weight"], 0, r["role_id"])

    def test_F6_scorer_is_never_called_with_profile(self):
        cmd = self.log["scorer_run"]["command"]["value"]
        self.assertTrue(cmd.startswith("npm run score -- "), cmd)
        self.assertNotIn("--profile", cmd)
        self.assertEqual(self.scores["_scorer"], "bayesian-role-scorer")

    # ── deliberate break per gate ────────────────────────────────────────────
    def test_G1_break_no_fuzzy_match_no_namesake_no_guessing_between_rows(self):
        self.assertEqual(self.by_id["g1-near-miss"]["g1_entity"]["status"]["value"], "not-found")
        self.assertEqual(self.by_id["g1-namesake"]["g1_entity"]["status"]["value"], "not-found",
                         "'Cohere' must not attach to 'COHERE HEALTH INC'")
        amb = self.by_id["g1-ambiguous"]
        self.assertEqual(amb["g1_entity"]["status"]["value"], "ambiguous")
        self.assertEqual(len(amb["g1_entity"]["matched_rows"]), 2)
        self.assertIsNone(self.sent["g1-ambiguous"]["sponsorship"]["p"])
        self.assertEqual(amb["decision"]["next_action"]["value"], "blocked: pick the right company row, then re-run")

    def test_G3_break_input_cannot_claim_liveness_was_checked(self):
        sent = self.sent["g3-tamper"]["liveness"]
        self.assertEqual(sent, {"factor": 1.0, "source": "your-input", "assumed": True, "checked": False})
        self.assertFalse(self.by_id["g3-tamper"]["g3_liveness"]["checked"]["value"])
        self.assertEqual(self.log["summary"]["g3_cleared"]["value"], 0)

    def test_G3_every_apply_or_tailor_is_shown_blocked(self):
        block = "blocked at G3 until npm run ats:liveness is run by a human"
        for e in self.log["roles"]:
            shown, action = e["decision"]["shown"]["value"], e["decision"]["next_action"]["value"]
            if shown.startswith("Apply") or action == "tailor an application":
                self.assertIn(block, shown, e["role_id"]["value"])
        for line in self.report.splitlines():
            if "tailor an application [" in line:
                self.assertIn(block, line)
        mappings = tso.load_mappings(tso.DEFAULTS["mappings"])
        self.assertEqual(tso.shown_decision("Apply", "tailor an application", mappings), f"Apply — {block}")

    # ── labels ───────────────────────────────────────────────────────────────
    def test_every_value_in_the_log_is_labelled(self):
        bad = unlabelled_leaves(self.log)
        self.assertEqual(bad, [], f"unlabelled values: {bad[:10]}")

    def test_every_term_sent_to_the_scorer_is_labelled(self):
        for rid, r in self.sent.items():
            for term in ("sponsorship", "fit", "liveness", "timeline"):
                self.assertIn(r[term]["source"], LABELS, f"{rid}.{term}")

    def test_report_opens_with_executive_summary(self):
        lines = [ln for ln in self.report.splitlines() if ln.strip()]
        self.assertTrue(lines[1].startswith("## Executive summary"), lines[:2])
        self.assertIn("not immigration advice", self.report)


class G2Boundaries(unittest.TestCase):
    """Deliberate break of G2: probe every band edge; no date gets a default."""

    def setUp(self):
        self.tl = tso.load_mappings(tso.DEFAULTS["mappings"])["timeline"]
        self.ead = tso.parse_iso_date("2027-01-22")

    def test_band_edges(self):
        import datetime as dt
        for days, factor in ((-30, 0.0), (-1, 0.0), (0, 1.0), (60, 1.0), (61, 0.6), (90, 0.6), (91, 0.0), (400, 0.0)):
            with self.subTest(days=days):
                start = (self.ead + dt.timedelta(days=days)).isoformat()
                self.assertEqual(tso.g2_timeline("r", start, self.ead, self.tl)["factor"], factor)

    def test_no_default_for_bad_dates(self):
        for bad in (None, "", "TBD", "2027-13-01", "2027/02/08", "20270208", 20270208):
            with self.subTest(bad=bad), self.assertRaises(tso.RoleInputError):
                tso.g2_timeline("r", bad, self.ead, self.tl)

    def test_persona_without_ead_start_stops_the_run(self):
        tmp = Path(tempfile.mkdtemp(prefix="tspo-test-"))
        try:
            p = tmp / "persona.json"
            p.write_text(json.dumps({"name": "x", "ead_start_date": "January"}))
            with self.assertRaises(tso.ConfigError):
                tso.load_persona(p)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class GuardUnit(unittest.TestCase):
    def test_zero_weight_trips_guard(self):
        scores = {"roles": [{"role_id": "x", "trace": {"votes": [{"factor": "sponsorship", "weight": 0, "value": 0.6}]}}]}
        with self.assertRaises(tso.GuardError):
            tso.check_sponsorship_weights(scores)

    def test_vacuous_output_trips_guard(self):
        with self.assertRaises(tso.GuardError):
            tso.check_sponsorship_weights({"roles": [{"role_id": "x", "trace": {"votes": []}}]})


class BrokenScorers(unittest.TestCase):
    """Each BROKEN-* mutant must be rejected by a guard (GuardError — not a crash, not a pass)."""

    def run_mutant(self, name):
        tmp = Path(tempfile.mkdtemp(prefix="tspo-mutant-"))
        try:
            with self.assertRaises(tso.GuardError) as cm:
                tso.build(fixture_args(tmp), scorer_cmd=["node", str(FIX / f"{name}.mjs")])
            return str(cm.exception)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mutants_are_not_stale(self):
        src = (tso.REPO / "scripts" / "score" / "role-scorer.mjs").read_text()
        for anchor in ("const needsSponsor = profile == null ? true",
                       "const timeline = num(role.timeline?.factor) ?? 1;", "gate_zero: 0.05,"):
            self.assertIn(anchor, src)

    def test_BROKEN_sponsorship_weight_zero_is_caught(self):
        self.assertIn("sponsorship weight is 0", self.run_mutant("BROKEN-sponsorship-weight-zero"))

    def test_BROKEN_timeline_ignored_is_caught(self):
        self.assertIn("scorer used gates", self.run_mutant("BROKEN-timeline-ignored"))

    def test_BROKEN_gate_zero_off_is_caught(self):
        self.assertIn("timeline factor 0 was sent", self.run_mutant("BROKEN-gate-zero-off"))


class SampleRunOnRealCsv(unittest.TestCase):
    """The shipped sample against the real 80 Days CSV, into a temp dir (regression, offline)."""

    def test_sample_run(self):
        tmp = Path(tempfile.mkdtemp(prefix="tspo-sample-"))
        try:
            res = tso.build(tso.parse_args(["--out-dir", str(tmp)]))
            s = res["log"]["summary"]
            self.assertEqual(s["roles_in"]["value"], 12)
            self.assertEqual(s["roles_not_scored"]["value"], 1)
            self.assertEqual(res["log"]["dataset_context"]["rows_with_h1b_fields"]["value"], 1557)
            self.assertEqual(unlabelled_leaves(res["log"]), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
