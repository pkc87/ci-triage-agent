import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.metrics import kennzahlen, konfusionsmatrix, versenkte_produktfehler, ESKALIERT


def test_perfekte_vorhersage():
    paare = [("PRODUKTFEHLER", "PRODUKTFEHLER")] * 3 + [("FLAKE", "FLAKE")] * 2
    k = kennzahlen(paare)
    assert k["macro_precision"] == 1.0
    assert k["macro_recall"] == 1.0
    assert k["abdeckung"] == 1.0
    assert k["je_klasse"]["KAPUTTER_TEST"]["support_gesamt"] == 0


def test_precision_und_recall_von_hand_nachgerechnet():
    # 2 true PRODUKTFEHLER: one hit, one called FLAKE.
    # 1 true FLAKE called PRODUKTFEHLER.
    paare = [
        ("PRODUKTFEHLER", "PRODUKTFEHLER"),
        ("PRODUKTFEHLER", "FLAKE"),
        ("FLAKE", "PRODUKTFEHLER"),
    ]
    k = kennzahlen(paare)["je_klasse"]
    # PRODUKTFEHLER: tp=1, fp=1 (the flake called product), fn=1
    assert k["PRODUKTFEHLER"]["precision"] == 0.5
    assert k["PRODUKTFEHLER"]["recall"] == 0.5
    # FLAKE: tp=0, fp=1, fn=1
    assert k["FLAKE"]["precision"] == 0.0
    assert k["FLAKE"]["recall"] == 0.0


def test_eskalation_zaehlt_nicht_gegen_precision_aber_gegen_abdeckung():
    paare = [
        ("PRODUKTFEHLER", "PRODUKTFEHLER"),
        ("PRODUKTFEHLER", ESKALIERT),
        ("FLAKE", ESKALIERT),
    ]
    k = kennzahlen(paare)
    assert k["faelle_eskaliert"] == 2
    assert k["abdeckung"] == round(1 / 3, 4)
    # The one decision it made was right.
    assert k["je_klasse"]["PRODUKTFEHLER"]["precision"] == 1.0
    assert k["je_klasse"]["PRODUKTFEHLER"]["recall"] == 1.0
    # FLAKE was never decided -> excluded from the macro basis, not scored as 0.
    assert "FLAKE" not in k["macro_basis"]
    assert k["macro_precision"] == 1.0


def test_alles_eskaliert_ergibt_null_abdeckung_und_leere_basis():
    paare = [("PRODUKTFEHLER", ESKALIERT), ("FLAKE", ESKALIERT)]
    k = kennzahlen(paare)
    assert k["abdeckung"] == 0.0
    assert k["macro_basis"] == []
    assert k["macro_f1"] == 0.0


def test_konfusionsmatrix_summiert_auf_fallzahl():
    paare = [("PRODUKTFEHLER", "FLAKE"), ("FLAKE", ESKALIERT), ("KAPUTTER_TEST", "KAPUTTER_TEST")]
    m = konfusionsmatrix(paare)
    assert sum(sum(z.values()) for z in m.values()) == 3
    assert m["PRODUKTFEHLER"]["FLAKE"] == 1
    assert m["FLAKE"][ESKALIERT] == 1


def test_versenkte_produktfehler_zaehlt_nur_rerun():
    paare = [
        ("PRODUKTFEHLER", "RERUN"),          # buried
        ("PRODUKTFEHLER", "TICKET"),         # wrong class maybe, but visible
        ("PRODUKTFEHLER", "ESKALATION_MENSCH"),  # safe
        ("FLAKE", "RERUN"),                  # correct
    ]
    assert versenkte_produktfehler(paare) == 1


def test_unbekannte_klasse_fliegt_auf():
    import pytest
    with pytest.raises(ValueError):
        konfusionsmatrix([("QUATSCH", "FLAKE")])


def test_wilson_ist_bei_kleinem_n_ehrlich_breit():
    from eval.metrics import wilson
    lo, hi = wilson(12, 15)          # recall 0.80 over 15 cases
    assert lo < 0.60 and hi > 0.90, (lo, hi)
    assert 0.0 <= lo <= hi <= 1.0


def test_wilson_bleibt_in_den_grenzen_bei_perfekt_und_null():
    from eval.metrics import wilson
    assert wilson(5, 5)[1] == 1.0 and wilson(5, 5)[0] < 1.0
    assert wilson(0, 5)[0] == 0.0 and wilson(0, 5)[1] > 0.0
    assert wilson(0, 0) == (0.0, 0.0)
