"""End-to-end: a case directory on disk -> verdict -> action -> scored result.

Uses the stub backend, so this runs anywhere with no key and no network.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from agent.backends import baue_backend
from agent.evidence import kuerze, lade_fall
from agent.triage import triagiere
from eval.run_eval import sweep, werte_aus


def _fall_schreiben(wurzel, fall_id, fehler, versuche, diff="--- a\n+++ b\n"):
    d = wurzel / fall_id
    d.mkdir(parents=True)
    (d / "fall.json").write_text(json.dumps({
        "id": fall_id, "quelle": "synthetisch", "repo": "fixtures/shop",
        "test_titel": "t", "test_datei": "tests/a.spec.ts", "test_zeile": 1,
        "fehlermeldung": fehler, "stack": "", "dauer_ms": 10,
        "versuche": versuche, "artefakte": {"diff": "diff.patch"}, "kontext": {},
    }), encoding="utf-8")
    (d / "diff.patch").write_text(diff, encoding="utf-8")
    return d


def test_fall_laden_meldet_fehlende_artefakte(tmp_path):
    d = _fall_schreiben(tmp_path, "x-1", "boom", [{"nr": 1, "status": "failed"}])
    fall = lade_fall(d)
    assert "trace" in fall.fehlend and "screenshot" in fall.fehlend
    assert "diff" not in fall.fehlend


def test_retry_pass_erscheint_im_prompt(tmp_path):
    d = _fall_schreiben(tmp_path, "x-2", "timeout",
                        [{"nr": 1, "status": "failed"}, {"nr": 2, "status": "passed"}])
    from agent.evidence import als_prompt
    assert "failed and then passed without changing" in als_prompt(lade_fall(d))


def test_ende_zu_ende_mit_stub(tmp_path):
    d = _fall_schreiben(tmp_path, "x-3", "Executable doesn't exist at /x/chrome",
                        [{"nr": 1, "status": "failed"}])
    e = triagiere(d, baue_backend("stub"), schwelle=0.70)
    assert e.verdict is not None
    assert e.verdict.klasse == "KAPUTTER_TEST"
    assert e.aktion == "TICKET"


def test_unparsebare_antwort_eskaliert_statt_zu_raten(tmp_path):
    class Kaputt:
        name, modell = "kaputt", "-"
        def frage(self, nachricht, screenshot=None):
            return "I think it's probably a flake, hard to say."

    d = _fall_schreiben(tmp_path, "x-4", "boom", [{"nr": 1, "status": "failed"}])
    e = triagiere(d, Kaputt(), schwelle=0.70)
    assert e.verdict is None
    assert e.aktion == "ESKALATION_MENSCH"
    assert "unparseable" in e.fehler


def test_sweep_ist_monoton_in_der_eskalationsquote():
    vorhersagen = [
        {"fall_id": "a", "klasse": "PRODUKTFEHLER", "konfidenz": 0.55, "label": "PRODUKTFEHLER"},
        {"fall_id": "b", "klasse": "FLAKE", "konfidenz": 0.72, "label": "FLAKE"},
        {"fall_id": "c", "klasse": "KAPUTTER_TEST", "konfidenz": 0.93, "label": "KAPUTTER_TEST"},
    ]
    quoten = [r["eskalationsquote"] for r in sweep(vorhersagen)]
    assert quoten == sorted(quoten), "raising the threshold must never escalate fewer cases"
    assert quoten[-1] >= quoten[0]


def test_parse_fehler_zaehlen_als_eskalation_nicht_als_klasse():
    vorhersagen = [{"fall_id": "a", "klasse": None, "konfidenz": None, "label": "FLAKE"}]
    k = werte_aus(vorhersagen, 0.70)
    assert k["parse_fehler"] == 1
    assert k["faelle_eskaliert"] == 1
    assert k["abdeckung"] == 0.0


def test_kuerzen_behaelt_kopf_und_schwanz():
    text = "A" * 100 + "MITTE" + "B" * 100
    gekuerzt = kuerze(text, 60, "diff")
    assert gekuerzt.startswith("AAAA") and gekuerzt.endswith("BBBB")
    assert "omitted" in gekuerzt and "MITTE" not in gekuerzt
