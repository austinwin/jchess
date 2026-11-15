"""Integration coverage for privacy, seeded exercises and parent-controlled answers."""
import os
os.environ["DATABASE_URL"]="sqlite:///./jchess_test_ci.db"
os.environ["DEMO_USERS"]="true"
os.environ["AI_ENCRYPTION_KEY"]="test-only-fernet-encryption-secret"
os.environ.pop("RENDER",None)
os.environ.pop("RENDER_SERVICE_ID",None)
from fastapi.testclient import TestClient
from main import app
from db import DB, Puzzle, AIConfig
from sqlalchemy import select
from lessons import LESSONS
import chess, json

def sign_in(client,username,password,newpassword):
    response=client.post("/api/auth/login",json={"username":username,"password":password})
    assert response.status_code==200,response.text
    if response.json()["must_reset"]:
        response=client.post("/api/auth/password",json={"current":password,"new":newpassword})
        assert response.status_code==200,response.text

def test_parent_child_reveal_and_training_flow():
    with TestClient(app) as child_client,TestClient(app) as parent_client:
        sign_in(child_client,"justin","justin","justinStrongPassword2026")
        sign_in(parent_client,"hoang","hoang","hoangStrongPassword2026")
        r=child_client.get("/api/catalog")
        assert r.status_code==200
        assert r.json()["total"]>100
        r=child_client.post("/api/child/puzzle/start",json={"category":"openings"})
        assert r.status_code==200,r.text
        exercise=r.json()
        assert "solution" not in exercise["puzzle"]
        family=parent_client.get("/api/parent/children").json()
        assert len(family)==1
        cid=family[0]["user"]["id"]
        live=parent_client.get("/api/parent/children/"+str(cid)+"/live").json()
        answer=live["active"]["puzzle"]["solution"][0]
        assert len(answer)>=4
        failed=child_client.post("/api/child/puzzle/move",json={"uci":"h1h8"})
        assert failed.status_code==400
        played=child_client.post("/api/child/puzzle/move",json={"uci":answer})
        assert played.status_code==200,played.text
        assert played.json()["correct"] is True
        assert played.json()["state"]["solved"] is True
        assert "solution" not in child_client.get("/api/child/current").json()["puzzle"]
        reveal=parent_client.post("/api/parent/sessions/"+str(exercise["id"])+"/reveal",json={"reveal":True})
        assert reveal.status_code==200
        assert child_client.get("/api/child/current").json()["puzzle"]["solution"][0]==answer
        assert child_client.get("/api/parent/children").status_code==403
        lessons=child_client.get("/api/lessons").json()
        assert len(lessons)==len(LESSONS)>=14
        assert all(l["puzzles"]>0 for l in lessons), [(l["id"],l["puzzles"]) for l in lessons if not l["puzzles"]]
        for lesson in lessons:
            drill=child_client.post("/api/child/puzzle/start",json={"lesson_id":lesson["id"]})
            assert drill.status_code==200,(lesson["id"],drill.text)
            assert drill.json()["puzzle"]["theme"]==lesson["theme"]
            assert "solution" not in drill.json()["puzzle"]
        bad=child_client.post("/api/child/puzzle/start",json={"lesson_id":"unknown"})
        assert bad.status_code==400
        # Strategic model moves are not the only sensible chess plans.
        strategy=child_client.post("/api/child/puzzle/start",json={"lesson_id":"center"}).json()
        b=chess.Board(strategy["fen"])
        model=parent_client.get("/api/parent/children/"+str(cid)+"/live").json()["active"]["puzzle"]["solution"][0]
        alternative=next(m.uci() for m in b.legal_moves if m.uci()!=model)
        res=child_client.post("/api/child/puzzle/move",json={"uci":alternative})
        assert res.status_code==200
        assert not res.json()["correct"] and res.json()["model_move"]
        assert res.json()["state"]["errors"]==0
        # Parent-owned encrypted keys never leak through status or child endpoints.
        key="sk-test-for-unit-test-only-1234567890"
        saved=parent_client.post("/api/parent/ai",json={"enabled":True,"api_key":key,"daily_limit":2})
        assert saved.status_code==200,saved.text
        assert saved.json()["has_key"] and saved.json()["daily_limit"]==2
        assert key not in saved.text
        assert child_client.get("/api/parent/ai").status_code==403
        with DB() as db:
            stored=db.get(AIConfig,parent_client.get("/api/auth/me").json()["id"])
            assert stored.key_cipher and key not in stored.key_cipher
        deleted=parent_client.post("/api/parent/ai",json={"enabled":False,"api_key":""})
        assert deleted.status_code==200 and not deleted.json()["has_key"]

def test_unrelated_parent_cannot_view_family():
    with TestClient(app) as c:
        assert c.post("/api/auth/register",json={"username":"otherparent","name":"Another Parent","password":"secureParentPassword1"}).status_code in (200,409)
        assert c.post("/api/auth/login",json={"username":"otherparent","password":"secureParentPassword1"}).status_code==200
        with DB() as db:
            kid=db.scalar(select(Puzzle.id).limit(1))
        assert c.get("/api/parent/children/2/live").status_code==404

def test_generated_puzzles_are_legal_and_cover_categories():
    with TestClient(app):
        with DB() as db:
            puzzles=db.scalars(select(Puzzle)).all()
            assert len(puzzles)>100
            assert {p.category for p in puzzles}=={"safety","tactics","thinking","endgames","openings","strategy"}
            assert {l["theme"] for l in LESSONS} <= {p.theme for p in puzzles}
            for p in puzzles:
                b=chess.Board(p.fen)
                assert b.is_valid(),p.id
                if p.kind=="spot":
                    assert chess.parse_square(p.target) in chess.SQUARES
                else:
                    for uci in json.loads(p.solution):
                        m=chess.Move.from_uci(uci)
                        assert m in b.legal_moves,p.id
                        b.push(m)
