import sys, pathlib
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from agent.schema import parse_verdict, entscheide, VerdictError


def test_parst_sauberes_json():
    v = parse_verdict('{"klasse":"FLAKE","konfidenz":0.81,"begruendung":"a. b.","beleg":"x:1"}')
    assert v.klasse == "FLAKE" and v.konfidenz == 0.81 and v.beleg == "x:1"


def test_parst_json_in_code_fence_und_mit_vorgeplapper():
    roh = 'Sure, here you go:\n```json\n{"klasse":"flake","konfidenz":0.5,"begruendung":"x"}\n```'
    assert parse_verdict(roh).klasse == "FLAKE"


@pytest.mark.parametrize("roh", [
    "",
    "no json here",
    '{"klasse":"WEISSNICHT","konfidenz":0.5,"begruendung":"x"}',
    '{"klasse":"FLAKE","konfidenz":1.4,"begruendung":"x"}',
    '{"klasse":"FLAKE","konfidenz":"hoch","begruendung":"x"}',
    '{"klasse":"FLAKE","konfidenz":0.5}',
])
def test_muell_wird_nicht_stillschweigend_repariert(roh):
    with pytest.raises(VerdictError):
        parse_verdict(roh)


def test_unter_schwelle_wird_eskaliert():
    assert entscheide("PRODUKTFEHLER", 0.60, 0.70) == "ESKALATION_MENSCH"
    assert entscheide("PRODUKTFEHLER", 0.70, 0.70) == "TICKET"


def test_flake_braucht_den_aufschlag():
    # Same confidence, same threshold: a product bug is actioned, a flake is not.
    assert entscheide("KAPUTTER_TEST", 0.75, 0.70) == "TICKET"
    assert entscheide("FLAKE", 0.75, 0.70) == "ESKALATION_MENSCH"
    assert entscheide("FLAKE", 0.80, 0.70) == "RERUN"


def test_aufschlag_abschaltbar_fuer_die_ablation():
    assert entscheide("FLAKE", 0.75, 0.70, flake_aufschlag=0.0) == "RERUN"
