"""The README generator must degrade, not crash or silently drop sections.

A block was once inserted in the middle of another block's `if`, so the
data-provenance heading only rendered when a stability file happened to exist,
and an empty calibration list raised NameError. Output was correct only because
every optional input was present. These tests remove the optional inputs.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import eval.readme_zahlen as rz  # noqa: E402

ERGEBNIS = pathlib.Path(__file__).resolve().parents[1] / "eval" / "ergebnis.json"


def _minimal(tmp_path, monkeypatch, **ueberschreiben):
    e = json.loads(ERGEBNIS.read_text(encoding="utf-8"))
    e.update(ueberschreiben)
    # point the generator at an empty directory: no stability, no second run, no stub
    monkeypatch.setattr(rz, "HIER", tmp_path)
    monkeypatch.setattr(rz, "WURZEL", tmp_path)
    return rz.zahlen_block(e)


def test_ohne_optionale_dateien_bleibt_die_datenherkunft(tmp_path, monkeypatch):
    text = _minimal(tmp_path, monkeypatch)
    assert "### Where the data comes from" in text
    assert "### Does the confidence mean anything?" in text
    assert "### How much of this is the dice?" not in text


def test_leere_kalibrierung_und_kein_flake_split_crashen_nicht(tmp_path, monkeypatch):
    text = _minimal(tmp_path, monkeypatch, kalibrierung=[], flake_nach_retry_signal=None)
    assert "### Where the data comes from" in text
    assert "### Does the confidence mean anything?" not in text
    assert "### The `FLAKE` row, taken apart" not in text
