"""Drop files from case diffs that should not be in a public repo.

The historical cases come from a private monorepo, and `diff.patch` is the real
diff of the commit under test -- which means it carries every file that commit
touched, not only the ones relevant to the failing kc-web test.

`.claude/launch.json` is one of those: a dev-server config listing every app in
that monorepo by name. It has no bearing on why a Playwright assertion failed,
and publishing it would leak the shape of unrelated private projects. Removing
it makes the evidence *better* as well as safer -- it is noise in the prompt.

Idempotent, and it reports exactly what it removed so the change is auditable.

  python eval/scrubbe_diffs.py --trocken
  python eval/scrubbe_diffs.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

HIER = Path(__file__).resolve().parent

# Paths whose hunks are stripped from every case diff, with the reason, which is
# printed and belongs in eval/cases/HERKUNFT.md.
RAUS = {
    ".claude/launch.json": "dev-server config naming unrelated private projects",
}

KOPF = re.compile(r"^diff --git a/(\S+) b/\S+$", re.M)


def entferne(patch: str, pfade: set[str]) -> tuple[str, list[str]]:
    """Remove whole file sections from a unified diff."""
    treffer = list(KOPF.finditer(patch))
    if not treffer:
        return patch, []
    behalten: list[str] = []
    entfernt: list[str] = []
    for i, m in enumerate(treffer):
        start = m.start()
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(patch)
        datei = m.group(1)
        if datei in pfade:
            entfernt.append(datei)
        else:
            behalten.append(patch[start:ende])
    # Anything before the first `diff --git` is a preamble (commit context or a
    # truncation marker) and is kept as-is.
    preamble = patch[:treffer[0].start()]
    return preamble + "".join(behalten), entfernt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--trocken", action="store_true", help="report, change nothing")
    args = p.parse_args()

    gesamt = 0
    for patch_pfad in sorted((HIER / "cases").glob("*/diff.patch")):
        alt = patch_pfad.read_text(encoding="utf-8", errors="replace")
        neu, entfernt = entferne(alt, set(RAUS))
        if not entfernt:
            continue
        gesamt += 1
        vorher, nachher = len(alt), len(neu)
        print(f"  {patch_pfad.parent.name}: removed {', '.join(entfernt)} "
              f"({vorher - nachher} chars, {vorher // 1024}k -> {nachher // 1024}k)")
        if not args.trocken:
            patch_pfad.write_text(neu, encoding="utf-8")

    for pfad, grund in RAUS.items():
        print(f"\nrule: {pfad} -- {grund}")
    print(f"{gesamt} diff(s) {'would change' if args.trocken else 'changed'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
