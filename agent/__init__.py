"""CI triage: classify a failing Playwright test, and know when not to.

    from agent.backends import baue_backend
    from agent.triage import triagiere

    ergebnis = triagiere("eval/cases/syn-001", baue_backend("api"), schwelle=0.70)
    print(ergebnis.verdict.klasse, ergebnis.aktion)

The model produces a class and a confidence; the action is policy, derived in
`schema.entscheide`. See docs/entscheidungen.md for why those are separate.
"""

__version__ = "0.1.0"
