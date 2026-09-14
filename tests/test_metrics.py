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


def test_kalibrierung_bildet_eine_steigende_spalte_ab():
    from eval.metrics import kalibrierung
    paare = ([(0.55, False)] * 4 + [(0.55, True)] * 1      # low bin: 20% right
             + [(0.80, True)] * 3 + [(0.80, False)] * 1    # mid bin: 75% right
             + [(0.95, True)] * 5)                         # high bin: 100% right
    b = kalibrierung(paare)
    quoten = [z["trefferquote"] for z in b if z["n"]]
    assert quoten == [0.2, 0.75, 1.0]
    assert quoten == sorted(quoten)


def test_kalibrierung_meldet_leere_koerbe_als_none_statt_null():
    from eval.metrics import kalibrierung
    b = kalibrierung([(0.95, True)])
    leer = [z for z in b if z["n"] == 0]
    assert leer and all(z["trefferquote"] is None for z in leer)


def test_nie_vorhergesagte_klasse_hat_undefinierte_precision_nicht_null():
    # The agent decides two classes and never says FLAKE. Two real flakes get
    # called KAPUTTER_TEST. FLAKE recall is a real 0.0 -- it missed both. FLAKE
    # precision is undefined: it never claimed a flake, so there is nothing to
    # be right or wrong about.
    paare = [
        ("PRODUKTFEHLER", "PRODUKTFEHLER"),
        ("KAPUTTER_TEST", "KAPUTTER_TEST"),
        ("FLAKE", "KAPUTTER_TEST"),
        ("FLAKE", "KAPUTTER_TEST"),
    ]
    k = kennzahlen(paare)
    assert k["je_klasse"]["FLAKE"]["precision"] is None
    assert k["je_klasse"]["FLAKE"]["recall"] == 0.0
    assert "FLAKE" not in k["macro_basis_precision"]
    assert "FLAKE" in k["macro_basis_recall"]
    # macro precision averages only the two classes it actually predicted:
    # PRODUKTFEHLER is clean (1.0), KAPUTTER_TEST absorbed both flakes as false
    # positives (1 tp / 3 predicted = 0.333). FLAKE contributes nothing.
    assert k["je_klasse"]["PRODUKTFEHLER"]["precision"] == 1.0
    assert k["je_klasse"]["KAPUTTER_TEST"]["precision"] == round(1 / 3, 4)
    assert k["macro_precision"] == round((1.0 + round(1 / 3, 4)) / 2, 4)
    # macro recall still carries the miss
    assert k["macro_recall"] < 1.0


def test_hoehere_schwelle_senkt_die_macro_precision_nicht_kuenstlich():
    # Regression guard for the artefact this fix removed: a class dropping out
    # of the predictions must not drag macro precision down as a 0.0.
    vorsichtiger = [
        ("PRODUKTFEHLER", "PRODUKTFEHLER"),
        ("KAPUTTER_TEST", "KAPUTTER_TEST"),
        ("FLAKE", ESKALIERT),
    ]
    mutiger = vorsichtiger[:2] + [("FLAKE", "KAPUTTER_TEST")]
    assert kennzahlen(vorsichtiger)["macro_precision"] >= kennzahlen(mutiger)["macro_precision"]


def test_bedingte_trefferquote_trennt_nach_signal():
    from eval.metrics import bedingte_trefferquote
    # 3 cases carry the signal and are all caught; 4 lack it and none are.
    paare = [(True, True)] * 3 + [(False, False)] * 4
    b = bedingte_trefferquote(paare)
    assert b["mit_signal"]["n"] == 3 and b["mit_signal"]["quote"] == 1.0
    assert b["ohne_signal"]["n"] == 4 and b["ohne_signal"]["quote"] == 0.0
    # the point of the split: the pooled rate depends on the mix, the parts do not
    assert b["mit_signal"]["ci95"][0] > 0.0


def test_bedingte_trefferquote_meldet_leere_seite_als_none():
    from eval.metrics import bedingte_trefferquote
    b = bedingte_trefferquote([(True, True), (True, False)])
    assert b["ohne_signal"]["n"] == 0
    assert b["ohne_signal"]["quote"] is None


def test_gepoolte_quote_haengt_an_der_mischung_die_bedingte_nicht():
    from eval.metrics import bedingte_trefferquote
    wenig = [(True, True)] * 2 + [(False, False)] * 8     # pooled 20%
    viel = [(True, True)] * 8 + [(False, False)] * 2      # pooled 80%
    a, b = bedingte_trefferquote(wenig), bedingte_trefferquote(viel)
    assert a["mit_signal"]["quote"] == b["mit_signal"]["quote"] == 1.0
    assert a["ohne_signal"]["quote"] == b["ohne_signal"]["quote"] == 0.0
