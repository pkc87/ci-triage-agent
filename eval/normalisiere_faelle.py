"""Normalise case files after generation: types, encodings, stray ANSI.

Two producers wrote this corpus (a historical extractor and a mutation runner)
and they disagreed about small things -- line numbers as strings, a literal
"None" where a null was meant, mojibake from reading Windows CI logs as cp1252.
None of that changes a label, all of it ends up in the model's prompt, and a
prompt with "dauer_ms: None" in it is a prompt that teaches the model the
evidence is sloppy.

Idempotent. Safe to re-run.

  python eval/normalisiere_faelle.py [--trocken]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HIER = Path(__file__).resolve().parent
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# UTF-8 bytes read as cp1252. The historical cases come from Windows-captured
# CI logs whose test titles are German, so this is a real risk -- though as it
# turned out, the corpus in this repo is clean, so this pass is a guard rather
# than a repair. Verified with --trocken: it changes nothing.
MOJIBAKE = {
    "â€”": "—",   # em dash
    "â€“": "–",   # en dash
    "â€™": "’",   # right single quote
    "Ã¤": "ä", "Ã¶": "ö", "Ã¼": "ü",
    "Ã„": "Ä", "Ã–": "Ö", "Ãœ": "Ü",
    "ÃŸ": "ß",
}


def saeubere_text(wert: str) -> str:
    wert = ANSI.sub("", wert)
    for kaputt, heil in MOJIBAKE.items():
        wert = wert.replace(kaputt, heil)
    return wert


def als_int(wert) -> int | None:
    if wert in (None, "", "None", "null"):
        return None
    try:
        return int(str(wert).strip())
    except ValueError:
        return None


def normalisiere(fall: dict) -> dict:
    fall["test_zeile"] = als_int(fall.get("test_zeile"))
    fall["dauer_ms"] = als_int(fall.get("dauer_ms"))

    for feld in ("test_titel", "test_datei", "fehlermeldung", "stack", "repo"):
        if isinstance(fall.get(feld), str):
            fall[feld] = saeubere_text(fall[feld])

    versuche = fall.get("versuche") or []
    sauber = []
    for i, v in enumerate(versuche, 1):
        if not isinstance(v, dict):
            continue
        sauber.append({"nr": als_int(v.get("nr")) or i,
                       "status": str(v.get("status", "failed"))})
    fall["versuche"] = sauber

    artefakte = fall.get("artefakte") or {}
    fall["artefakte"] = {k: v for k, v in artefakte.items() if v}
    return fall


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--trocken", action="store_true", help="report, change nothing")
    args = p.parse_args()

    geaendert = 0
    for fj in sorted((HIER / "cases").glob("*/fall.json")):
        vorher = fj.read_text(encoding="utf-8")
        fall = normalisiere(json.loads(vorher))
        nachher = json.dumps(fall, ensure_ascii=False, indent=2) + "\n"
        if nachher != vorher:
            geaendert += 1
            print(f"  {'would fix' if args.trocken else 'fixed'} {fj.parent.name}")
            if not args.trocken:
                fj.write_text(nachher, encoding="utf-8")

        for name in ("log_excerpt.txt", "trace.txt"):
            d = fj.parent / name
            if d.exists():
                roh = d.read_text(encoding="utf-8", errors="replace")
                sauber = saeubere_text(roh)
                if sauber != roh and not args.trocken:
                    d.write_text(sauber, encoding="utf-8")

    print(f"{geaendert} case file(s) {'would change' if args.trocken else 'changed'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
