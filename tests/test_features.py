from gitskills import features
from tests.conftest import SKILL_A, SKILL_B


def test_front_matter_and_spec():
    f = features.extract(SKILL_A)
    assert f["name_spec_ok"] and f["desc_spec_ok"] and f["desc_has_trigger"]
    assert f["risk_pipe_to_shell"] and f["risk_remote_fetch"]
    assert "claude" not in f["tools_named"]


def test_directives_and_no_trigger():
    f = features.extract(SKILL_B)
    assert not f["desc_has_trigger"]
    assert f["n_directives"] == 1 and not f["risk_pipe_to_shell"]


def test_no_front_matter():
    f = features.extract("just text")
    assert f["desc_chars"] == 0 and not f["name_spec_ok"]


def test_ai_coauthor():
    assert features.ai_coauthor("x\n\nCo-Authored-By: Claude Opus <a@b>") == "claude"
    assert features.ai_coauthor("plain") is None
