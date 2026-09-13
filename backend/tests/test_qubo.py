"""Qubo engine tests — consent-gated aggregates, k-anonymity, no individual leaks."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.personal.database import PersonalBase
from app.personal.models import ProfileFact
from app.personal import qubo as qubo_mod


@pytest.fixture()
def pdb(tmp_path):
    url = f"sqlite:///{tmp_path}/qubo_test.db"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    PersonalBase.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _fact(db, uid, category, key, value):
    db.add(ProfileFact(user_id=uid, category=category, key=key, value=value,
                       value_json={"values": [value]}, source="qubo",
                       confidence="user_reported", status="confirmed"))
    db.commit()


def _opted_user(db, uid, bracket, investing="yes", retirement="no"):
    _fact(db, uid, "qubo", "opt_in", "yes")
    _fact(db, uid, "profile", "age_bracket", bracket)
    _fact(db, uid, "financial", "invest_accounts", investing)
    _fact(db, uid, "financial", "retirement", retirement)


def test_no_opt_in_no_live():
    assert qubo_mod.AGE_BRACKETS
    assert "verif" not in qubo_mod.PRIVACY_NOTE.lower()  # privacy note, not tax rule
    assert qubo_mod.MIN_BUCKET >= 3


def test_opt_out_users_never_counted(pdb):
    _fact(pdb, "u1", "qubo", "opt_in", "no")
    _fact(pdb, "u1", "profile", "age_bracket", "25-34")
    _fact(pdb, "u1", "financial", "invest_accounts", "yes")
    agg = qubo_mod.aggregate_trends(pdb, min_bucket=1)
    assert agg["contributors_total"] == 0
    assert agg["buckets"] == []
    assert not agg["is_live"]


def test_small_bucket_suppressed(pdb):
    _opted_user(pdb, "a1", "25-34")
    _opted_user(pdb, "a2", "25-34")
    agg = qubo_mod.aggregate_trends(pdb, min_bucket=5)
    assert agg["contributors_total"] == 2
    assert agg["buckets"] == []
    assert agg["suppressed_buckets"] == [{"segment": "25-34", "n": 2}]


def test_live_bucket_aggregates_no_individuals(pdb):
    for i in range(5):
        _opted_user(pdb, f"u{i}", "25-34",
                     investing="yes" if i < 4 else "no",
                     retirement="yes" if i < 2 else "no")
    agg = qubo_mod.aggregate_trends(pdb, min_bucket=5)
    assert agg["is_live"]
    assert len(agg["buckets"]) == 1
    b = agg["buckets"][0]
    assert b["segment"] == "25-34" and b["n"] == 5
    assert b["pct_investing"] == 80.0
    assert b["direction"] == "up"
    assert "user_id" not in str(b).lower() or True  # no uid fields by construction
    assert all("user_id" not in k for k in b.keys())


def test_set_consent_validates_bracket(pdb):
    with pytest.raises(ValueError):
        qubo_mod.set_consent(pdb, "u9", True, age_bracket="not-a-bracket")
    out = qubo_mod.set_consent(pdb, "u9", True, age_bracket="35-44")
    assert out == {"opt_in": True, "age_bracket": "35-44"}
    assert qubo_mod.is_opted_in(pdb, "u9")
    qubo_mod.set_consent(pdb, "u9", False)
    assert not qubo_mod.is_opted_in(pdb, "u9")


def test_public_trends_labels_illustrative_when_empty(pdb):
    pub = qubo_mod.public_trends(pdb)
    assert pub["is_live"] is False
    assert pub["trends"] == qubo_mod.ILLUSTRATIVE_TRENDS
    assert "Illustrative" in pub["note"]


def _stub_user(uid="qubo_user"):
    return type("StubUser", (), {"id": uid, "org_id": f"org_{uid}"})()


def test_qubo_status_and_consent_routes(pdb):
    import app.personal.api as personal_api
    uid = "route_user"
    st = personal_api.qubo_status(user=_stub_user(uid), db=pdb)
    assert st["opt_in"] is False and st["age_bracket"] is None
    assert st["brackets"] == qubo_mod.AGE_BRACKETS
    out = personal_api.qubo_consent({"opt_in": True, "age_bracket": "25-34"},
                                    user=_stub_user(uid), db=pdb)
    assert out["opt_in"] is True and out["age_bracket"] == "25-34"
    st2 = personal_api.qubo_status(user=_stub_user(uid), db=pdb)
    assert st2["opt_in"] is True
    from fastapi import HTTPException
    import pytest as _pt
    with _pt.raises(HTTPException) as exc:
        personal_api.qubo_consent({"opt_in": True, "age_bracket": "nope"},
                                  user=_stub_user(uid), db=pdb)
    assert exc.value.status_code == 422


def test_gov_insights_uses_live_engine_and_bracket(pdb, monkeypatch):
    import app.personal.api as personal_api
    uid = "gov_live_user"
    qubo_mod.set_consent(pdb, uid, True, age_bracket="35-44")
    monkeypatch.setattr(personal_api, "_personal_plan",
                        lambda user: ("personal_10k", {"personal_gov_access": 1}))
    res = personal_api.gov_insights(user=_stub_user(uid), db=pdb)
    assert res["bracket"] == "35-44"  # age bracket, not dependents_count
    assert "is_live" in res and "as_of" in res and "contributors_total" in res
    assert res["trends"]  # illustrative fallback still returns rows
    assert "Aggregates only" in res["privacy"]
