"""Coach Hoang: family-scoped personalized training without leaking answer keys."""
import json
import uuid
from fastapi.testclient import TestClient
from main import app
from db import DB,Puzzle,CoachAccess,CoachPlan
from sqlalchemy import select

def setup_family(parent,student):
    tag=uuid.uuid4().hex[:9]
    user="coachp"+tag;child="coachc"+tag
    password="parentTestingPassword2026"
    assert parent.post("/api/auth/register",json={"username":user,"name":"Parent","password":password}).status_code==200
    assert parent.post("/api/auth/login",json={"username":user,"password":password}).status_code==200
    r=parent.post("/api/parent/children",json={"username":child,"name":"Student","password":"strongChildPassword2026"})
    assert r.status_code==200,r.text
    cid=r.json()["id"]
    assert student.post("/api/auth/login",json={"username":child,"password":"strongChildPassword2026"}).status_code==200
    return cid

def test_offline_coach_uses_verified_positions_and_guards_answers():
    with TestClient(app) as p,TestClient(app) as c,TestClient(app) as stranger:
        cid=setup_family(p,c)
        status=c.get("/api/child/coach/status")
        assert status.status_code==200
        assert status.json()["coach"]=="Hoang"
        assert not status.json()["ai_available"]
        plan_resp=c.post("/api/child/coach/plan",json={})
        assert plan_resp.status_code==200,plan_resp.text
        plan=plan_resp.json()
        assert plan["source"]=="verified" and len(plan["missions"])>=5
        assert "solution" not in json.dumps(plan)
        assert '"target":' not in json.dumps(plan)
        for task in plan["missions"]:
            with DB() as db:
                puzzle=db.get(Puzzle,task["puzzle_id"])
                assert puzzle is not None and puzzle.category==task["category"]
            assert task["thinking_tip"] and task["goal"]
        parent_view=p.get("/api/parent/children/"+str(cid)+"/coach")
        assert parent_view.status_code==200
        assert parent_view.json()["plan"]["id"]==plan["id"]
        assert stranger.get("/api/parent/children/"+str(cid)+"/coach").status_code==401
        wrong=c.post("/api/child/coach/mission/start",json={"plan_id":plan["id"],"puzzle_id":"not_in_plan"})
        assert wrong.status_code==403
        first=plan["missions"][0]
        exercise=c.post("/api/child/coach/mission/start",json={"plan_id":plan["id"],"puzzle_id":first["puzzle_id"]})
        assert exercise.status_code==200,exercise.text
        assert "solution" not in exercise.json().get("puzzle",{})
        sess=exercise.json()["id"]
        hint=c.post("/api/child/coach/explain",json={"session_id":sess,"mode":"hint"})
        assert hint.status_code==200 and hint.json()["source"]=="verified"
        assert "solution" not in hint.text
        blocked=c.post("/api/child/coach/explain",json={"session_id":sess,"mode":"explain"})
        assert blocked.status_code==403
        live=p.get("/api/parent/children/"+str(cid)+"/live").json()["active"]["puzzle"]
        if live["kind"]=="spot":
            result=c.post("/api/child/puzzle/spot",json={"square":live["target"]})
            assert result.status_code==200
        else:
            for index,move in enumerate(live["solution"]):
                if index%2==0:
                    r=c.post("/api/child/puzzle/move",json={"uci":move})
                    assert r.status_code==200,r.text
        assert c.get("/api/child/current").json()["solved"]
        explanation=c.post("/api/child/coach/explain",json={"session_id":sess,"mode":"explain"})
        assert explanation.status_code==200,explanation.text
        assert "solution" not in explanation.text
        assert explanation.json()["coach"]=="Hoang"

def test_parent_opt_in_quota_and_structured_coach_output(monkeypatch):
    calls=[]
    class StubReply:
        def raise_for_status(self):pass
        def json(self):return {"choices":[{"message":{"content":json.dumps({
            "opening":"We will build your tactical vision.",
            "focus":"Take extra care to notice threats before attacking.",
            "tip":"Ask what your opponent could capture after every move."})}}]}
    class FakeClient:
        def __init__(self,timeout):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            calls.append({"url":url,"body":json,"auth":headers.get("Authorization")})
            return StubReply()
    monkeypatch.setattr("coach_routes.httpx.Client",FakeClient)
    with TestClient(app) as p,TestClient(app) as c:
        cid=setup_family(p,c)
        key="sk-test-coach-key-not-for-production-123456789"
        # Supplying a key alone must not enable student-facing coaching.
        saved=p.post("/api/parent/ai",json={"enabled":True,"api_key":key,"coach_daily_limit":1})
        assert saved.status_code==200
        assert not saved.json()["coach_enabled"]
        ordinary=c.post("/api/child/coach/plan",json={})
        assert ordinary.status_code==200 and ordinary.json()["source"]=="verified"
        assert len(calls)==0
        allowed=p.post("/api/parent/ai",json={"enabled":True,"coach_enabled":True,"coach_daily_limit":1})
        assert allowed.status_code==200,allowed.text
        assert allowed.json()["coach_enabled"]
        assert key not in allowed.text
        first=c.post("/api/child/coach/plan",json={})
        assert first.status_code==200,first.text
        assert first.json()["source"]=="ai-assisted"
        assert first.json()["message"]=="We will build your tactical vision."
        assert len(calls)==1
        assert calls[0]["body"]["store"] is False
        assert calls[0]["body"]["response_format"]["type"]=="json_schema"
        assert key not in json.dumps(calls[0]["body"])
        assert "username" not in json.dumps(calls[0]["body"])
        assert "solution" not in json.dumps(calls[0]["body"])
        assert c.get("/api/parent/ai").status_code==403
        exhausted=c.post("/api/child/coach/plan",json={})
        assert exhausted.status_code==200
        assert exhausted.json()["source"]=="verified"
        assert len(calls)==1
        assert c.get("/api/child/coach/status").json()["remaining_today"]==0
        disabled=p.post("/api/parent/ai",json={"enabled":False,"api_key":""})
        assert disabled.status_code==200 and not disabled.json()["coach_enabled"]
        with DB() as db:
            assert db.scalar(select(CoachPlan).where(CoachPlan.child_id==cid)) is not None
            access=db.scalar(select(CoachAccess).where(CoachAccess.parent_id==p.get("/api/auth/me").json()["id"]))
            assert access and not access.enabled
