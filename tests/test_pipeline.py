from gitskills import clean, reuse
from gitskills import features as F


def test_copies_and_strict(tiny_db):
    sk = clean.skills(with_content=True)
    assert len(sk) == 3
    a = sk.set_index("file_sha").loc["aaa"]
    assert a["copies"] == 2 and a["n_owners"] == 2
    strict = clean.strict(sk)
    assert set(strict["file_sha"]) == {"aaa", "bbb"}  # skill.md from 2019 dropped
    rep = clean.population_report(sk)
    assert rep.iloc[-1]["skills"] == 2


def test_concentration_and_drift(tiny_db):
    sk = clean.skills(with_content=True)
    feats = F.build_features(workers=1)
    sk = sk.merge(feats, on="file_sha")
    conc = reuse.concentration(sk["copies"])
    assert conc["occurrences"] == 4 and 0 <= conc["gini"] <= 1
    fam = reuse.name_families(clean.strict(sk))
    drift = reuse.variant_drift(fam, ["risk_pipe_to_shell", "risk_remote_fetch"])
    # bbb is the variant of aaa (2 copies) and *removes* pipe-to-shell
    assert len(drift) == 1 and drift.iloc[0]["removed_risk_pipe_to_shell"]
    assert not drift.iloc[0]["any_added"]


def test_gini():
    assert reuse.gini([1, 1, 1, 1]) == 0
    assert reuse.gini([0, 0, 0, 10]) > 0.7
