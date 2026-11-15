"""Human multiplayer and three offline/cloud robot levels; real HTTP integration tests."""
import os,uuid
os.environ.setdefault("DATABASE_URL","sqlite:///./jchess_test_ci.db")
os.environ.setdefault("DEMO_USERS","true")
os.environ.setdefault("AI_ENCRYPTION_KEY","test-only-encryption-key")
from fastapi.testclient import TestClient
from main import app
import chess

def parent_account(client):
    tag=uuid.uuid4().hex[:9]
    name="par"+tag
    pw="strongParentPassword2026"
    assert client.post("/api/auth/register",json={"username":name,"name":"Test Parent","password":pw}).status_code==200
    r=client.post("/api/auth/login",json={"username":name,"password":pw})
    assert r.status_code==200,r.text
    kid="kid"+tag
    child=client.post("/api/parent/children",json={"username":kid,"name":"Student","password":"strongChildPassword2026"})
    assert child.status_code==200,child.text
    return kid,child.json()["id"]

def child_login(client,kid):
    r=client.post("/api/auth/login",json={"username":kid,"password":"strongChildPassword2026"})
    assert r.status_code==200,r.text

def check_game(game):
    board=chess.Board()
    for item in game["moves"]:
        m=chess.Move.from_uci(item["uci"])
        assert m in board.legal_moves
        assert item["san"]==board.san(m)
        board.push(m)
    assert board.fen()==game["fen"]

def test_robot_and_human_games():
    with TestClient(app) as p,TestClient(app) as kid,TestClient(app) as friend,TestClient(app) as other:
        username,cid=parent_account(p);child_login(kid,username)
        options=kid.get("/api/child/game/options").json()
        assert options["offline_available"] is True
        assert not options["cloud_available"]
        for level in ("easy","medium","hard"):
            r=kid.post("/api/child/game/start",json={"mode":"bot","level":level})
            assert r.status_code==200,r.text
            start=r.json()
            assert start["turn"]=="white" and start["level"]==level
            assert not start.get("invite_token")
            reply=kid.post("/api/child/game/move",json={"game_id":start["id"],"uci":"e2e4"})
            assert reply.status_code==200,reply.text
            state=reply.json();check_game(state)
            assert len(state["moves"])==2 and state["moves"][1]["actor"]=="builtin"
            assert state["turn"]=="white"
            assert kid.post("/api/child/game/move",json={"game_id":start["id"],"uci":"e7e5"}).status_code==400
        local=kid.post("/api/child/game/start",json={"mode":"local"}).json()
        first=kid.post("/api/child/game/move",json={"game_id":local["id"],"uci":"e2e4"})
        assert first.status_code==200 and first.json()["turn"]=="black"
        second=kid.post("/api/child/game/move",json={"game_id":local["id"],"uci":"e7e5"})
        assert second.status_code==200 and second.json()["turn"]=="white"
        check_game(second.json())
        versus=p.get("/api/parent/game/current?child_id="+str(cid)).json()
        assert versus["mode"]=="local"
        parent_game=kid.post("/api/child/game/start",json={"mode":"parent"}).json()
        assert kid.post("/api/child/game/move",json={"game_id":parent_game["id"],"uci":"e2e4"}).status_code==200
        assert kid.post("/api/child/game/move",json={"game_id":parent_game["id"],"uci":"d2d4"}).status_code==409
        reply=p.post("/api/parent/game/move",json={"game_id":parent_game["id"],"uci":"e7e5"})
        assert reply.status_code==200,reply.text
        check_game(reply.json())
        assert p.post("/api/parent/game/move",json={"game_id":local["id"],"uci":"e7e5"}).status_code==403
        assert other.get("/api/parent/game/current?child_id="+str(cid)).status_code==401
        friend_game=kid.post("/api/child/game/start",json={"mode":"friend"}).json()
        token=friend_game["invite_token"]
        assert len(token)>=35
        assert token not in str(kid.get("/api/child/game/current").json())
        assert friend.post("/api/guest/game/current",json={"token":"x"*43}).status_code==404
        guest=friend.post("/api/guest/game/current",json={"token":token})
        assert guest.status_code==200 and "invite_token" not in guest.text
        assert friend.post("/api/guest/game/move",json={"token":token,"uci":"e7e5"}).status_code==409
        assert kid.post("/api/child/game/move",json={"game_id":friend_game["id"],"uci":"e2e4"}).status_code==200
        guest=friend.post("/api/guest/game/move",json={"token":token,"uci":"e7e5"})
        assert guest.status_code==200,guest.text
        check_game(guest.json())

def test_parent_controlled_cloud_game_with_quota(monkeypatch):
    calls=[]
    class MockResponse:
        def raise_for_status(self):return None
        def json(self):return {"choices":[{"message":{"content":"e7e5"}}]}
    class FakeHTTP:
        def __init__(self,timeout):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            calls.append((url,json))
            return MockResponse()
    monkeypatch.setattr("game_routes.httpx.Client",FakeHTTP)
    with TestClient(app) as p,TestClient(app) as kid:
        username,cid=parent_account(p);child_login(kid,username)
        assert kid.post("/api/child/game/start",json={"mode":"bot","provider":"cloud","level":"easy"}).status_code==403
        key="sk-test-mock-key-for-cloud-1234567890"
        r=p.post("/api/parent/ai",json={"enabled":True,"api_key":key,"cloud_enabled":True,"cloud_daily_limit":1})
        assert r.status_code==200,r.text
        assert r.json()["cloud_enabled"] and "key" not in str(r.json().get("api_key"))
        opts=kid.get("/api/child/game/options").json()
        assert opts["cloud_available"] and opts["cloud_moves_remaining"]==1
        g=kid.post("/api/child/game/start",json={"mode":"bot","provider":"cloud","level":"medium"}).json()
        move=kid.post("/api/child/game/move",json={"game_id":g["id"],"uci":"e2e4"})
        assert move.status_code==200,move.text
        assert move.json()["moves"][1]["uci"]=="e7e5"
        assert move.json()["moves"][1]["actor"]=="cloud"
        assert len(calls)==1 and "FEN:" in calls[0][1]["messages"][1]["content"]
        assert not opts.get("api_key")
        assert not kid.get("/api/child/game/options").json()["cloud_available"]
        # Already started games can still continue using the local bot when quota runs out.
        assert kid.post("/api/child/game/start",json={"mode":"bot","provider":"cloud"}).status_code==403
        p.post("/api/parent/ai",json={"enabled":False,"api_key":"","cloud_enabled":False})
        assert kid.get("/api/child/game/options").json()["cloud_available"] is False
