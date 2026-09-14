"""`python -m agent <case-dir>` -- triage a single failure and print the verdict."""

from __future__ import annotations

import argparse
import json
import sys

from .backends import baue_backend
from .evidence import lade_fall
from .triage import triagiere


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agent", description="Triage one failing CI test.")
    p.add_argument("fall", help="path to a case directory containing fall.json")
    p.add_argument("--backend", default="cli", choices=("api", "cli", "stub"))
    p.add_argument("--modell", default=None)
    p.add_argument("--schwelle", type=float, default=0.70)
    p.add_argument("--mit-screenshot", action="store_true")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--zeige-prompt", action="store_true",
                   help="print the evidence bundle instead of calling a model")
    args = p.parse_args(argv)

    fall = lade_fall(args.fall)

    if args.zeige_prompt:
        from .evidence import als_prompt
        print(als_prompt(fall, mit_screenshot=args.mit_screenshot))
        return 0

    ergebnis = triagiere(fall, baue_backend(args.backend, args.modell),
                         schwelle=args.schwelle, mit_screenshot=args.mit_screenshot)

    if args.json:
        print(json.dumps(ergebnis.as_dict(), ensure_ascii=False, indent=2))
        return 0 if ergebnis.verdict else 1

    if ergebnis.verdict is None:
        print(f"fall:        {ergebnis.fall_id}")
        print(f"FEHLER:      {ergebnis.fehler}")
        print(f"aktion:      {ergebnis.aktion}")
        return 1

    v = ergebnis.verdict
    print(f"fall:        {ergebnis.fall_id}")
    print(f"klasse:      {v.klasse}")
    print(f"konfidenz:   {v.konfidenz:.2f}")
    print(f"begruendung: {v.begruendung}")
    print(f"beleg:       {v.beleg}")
    print(f"aktion:      {ergebnis.aktion}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
