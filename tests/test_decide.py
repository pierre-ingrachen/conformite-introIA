import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
import _core as c


def facts(**kw):
    f = {k: {"v": None, "e": None} for k in c.FACTS}
    for k, v in kw.items(): f[k] = {"v": v, "e": "x.py: preuve"}
    return f


def run(**kw):
    f = facts(is_ai_system=True, placed_on_eu_market=True, roles=["provider"], **kw)
    ai = c.decide_ai(f); rg, _ = c.decide_rgpd(f, ai)
    return ai, rg, c.verdict(ai, rg, f)


class T(unittest.TestCase):
    def test_out_of_scope(self):
        f = facts(is_ai_system=False)
        self.assertEqual(c.decide_ai(f)["status"], "out_of_scope")
        f["is_ai_system"]["e"] = None                       # « non » sans preuve ne suffit pas
        self.assertNotEqual(c.decide_ai(f)["status"], "out_of_scope")
        self.assertEqual(c.decide_ai(facts(is_ai_system=True, placed_on_eu_market=False, established_in_eu=False, output_used_in_eu=False))["status"], "out_of_scope")

    def test_exclusion_never_blocks(self):
        ai, _, _ = run(annex3=["employment"], exclusions=["third_country_public_authority"])
        self.assertEqual(ai["status"], "high_risk"); self.assertTrue(any("Exclusion" in n for n in ai["notes"]))

    def test_prohibited(self):
        ai, _, v = run(prohibited_practices=["social_scoring"])
        self.assertEqual((ai["status"], v), ("prohibited", "interdit"))

    def test_high_risk_recruitment_profiling(self):
        ai, rg, v = run(annex3=["employment"], profiling_of_persons=True, hr5_exceptions=["preparatory_task"],
                        automated_decision_legal_effect=True, human_review_before_decision=False, personal_data_categories=["employment_cv"])
        self.assertEqual(ai["status"], "high_risk")             # le profilage écrase l'exception art. 6(3)
        refs = {o["ref"] for o in ai["obligations"]}
        self.assertTrue({"art. 16", "art. 4"} <= refs)
        self.assertNotIn("art. 6(4), 49(2)", refs)              # Notify NCA seulement si non haut risque
        self.assertEqual(v, "non_conforme_probable")            # art. 22 sans revue humaine
        self.assertTrue(rg["aipd_required"])

    def test_art_6_3_exception(self):
        ai, _, _ = run(annex3=["employment"], profiling_of_persons=False, hr5_exceptions=["narrow_procedural"])
        self.assertEqual(ai["status"], "not_high_risk_registered")
        self.assertIn("art. 6(4), 49(2)", {o["ref"] for o in ai["obligations"]})

    def test_transparency_and_minimal(self):
        ai, _, _ = run(annex3=[], annex1="none", transparency_triggers=["interacts_with_people"])
        self.assertEqual(ai["status"], "minimal")
        self.assertIn("art. 50(1)", {o["ref"] for o in ai["obligations"]})

    def test_rgpd_transfer_and_no_personal_data(self):
        _, rg, _ = run(annex3=[], personal_data_categories=["identity_contact"], transfers_outside_eu=True)
        self.assertTrue(any("art. 44-46" in x["ref"] for x in rg["findings"]))
        _, rg, _ = run(annex3=[], personal_data_categories=[])
        self.assertFalse(rg["applicable"])

    def test_evidence_validation(self):
        raw = {"facts": {"is_ai_system": {"v": True, "e": "ghost.py: x"}, "roles": {"v": ["provider"], "e": "app/a.py: y"}}, "maturity": {}}
        f, _, unsup, _ = c.validate(raw, ["app/a.py"])
        self.assertIsNone(f["is_ai_system"]["v"]); self.assertIn("is_ai_system", unsup)
        self.assertEqual(f["roles"]["v"], ["provider"])

    def test_schema_strict_shape(self):
        s = c.response_schema()
        self.assertEqual(set(s["properties"]["facts"]["required"]), set(c.FACTS))


if __name__ == "__main__":
    unittest.main()
