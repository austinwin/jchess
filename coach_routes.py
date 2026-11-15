"""Coach Hoang: private, parent-enabled coaching over verified chess exercises.

The assistant explains, evaluates trends and assembles training sessions.
It never writes a chess answer key or selects the game's legal moves.
"""
import base64
import hashlib
import json
import os
import random
import uuid
from cryptography.fernet import Fernet
import chess
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from db import (AIConfig, CoachAccess, CoachPlan, Family, Puzzle,
                Attempt, Training, now)
from content import CATEGORIES
from lessons import LESSONS

THEME_HINTS={
 "fork":"Find a single move that attacks two targets. Checks and knight jumps are worth checking.",
 "pin":"Look for an important piece behind the piece you want to pin.",
 "skewer":"Look for two pieces on one line. Can the valuable one be forced to move?",
 "back-rank":"Check the king's escape squares before looking for a rook check.",
 "center":"Look at d4, e4, d5 and e5. How could your pieces influence them?",
 "king-safety":"Before an attack, look at checks against your king and whether you can castle.",
 "development":"Try activating a knight or bishop without leaving a piece undefended.",
 "piece-activity":"Which piece is doing the least? Can you improve its activity safely?",
 "passed-pawn":"Look ahead for blockades and support from your king.",
 "open-file":"Where is the file with no pawn blocking your rook?",
 "remove-defender":"Which enemy piece is holding the position together?",
 "discovered-attack":"Move one piece to open a hidden attack by another.",
 "double-attack":"Can your move check one piece while threatening another?",
 "pawn-break":"Which pawn push would change the center in your favor?",
 "mate":"Check every king escape square before deciding.",
 "promotion":"Make sure your passed pawn is protected before advancing."
}

class MissionStart(BaseModel):
    plan_id:str=Field(min_length=32,max_length=36)
    puzzle_id:str=Field(min_length=2,max_length=80)

class ExplanationRequest(BaseModel):
    session_id:int=Field(ge=1)
    mode:str=Field(pattern="^(hint|explain)$")

def _parent_id(db,child_id):
    return db.scalar(select(Family.parent_id).where(Family.child_id==child_id).order_by(Family.parent_id).limit(1))

def _permission(db,parent_id):
    if not parent_id:return False,0,3
    settings=db.get(AIConfig,parent_id)
    a=db.get(CoachAccess,parent_id)
    used=a.used if a and a.day==now().date().isoformat() else 0
    limit=a.daily_limit if a else 3
    return bool(settings and settings.enabled and settings.key_cipher and a and a.enabled and used<limit),max(0,limit-used),limit

def _use_quota(db,parent_id):
    # Locked and committed before the call: concurrent child sessions cannot bypass it.
    a=db.scalar(select(CoachAccess).where(CoachAccess.parent_id==parent_id).with_for_update())
    settings=db.get(AIConfig,parent_id)
    if not a or not a.enabled or not settings or not settings.enabled or not settings.key_cipher:
        return None
    today=now().date().isoformat()
    if a.day!=today:a.day=today;a.used=0
    if a.used>=a.daily_limit:return None
    a.used+=1
    cipher_key=settings.key_cipher
    db.commit()
    return cipher_key

def _call_model(ciphertext,system,payload,max_tokens=320):
    secret=os.getenv("AI_ENCRYPTION_KEY","")
    if not secret:return None
    try:
        f=Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))
        key=f.decrypt(ciphertext.encode()).decode()
        with httpx.Client(timeout=16) as client:
            result=client.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization":"Bearer "+key},
                json={"model":"gpt-4.1-mini","temperature":0.3,"max_tokens":max_tokens,
                      "store":False,
                      "response_format":{"type":"json_schema","json_schema":{
                          "name":"coach_hoang_feedback","strict":True,
                          "schema":{"type":"object","properties":{
                              "opening":{"type":"string"},
                              "focus":{"type":"string"},
                              "tip":{"type":"string"}},
                              "required":["opening","focus","tip"],"additionalProperties":False}}},
                      "messages":[{"role":"system","content":system},
                                  {"role":"user","content":json.dumps(payload,ensure_ascii=True)}]})
            result.raise_for_status()
            model=json.loads(result.json()["choices"][0]["message"]["content"])
            if not isinstance(model,dict):return None
            return {k:v.strip()[:330] for k,v in model.items()
                    if k in ("opening","focus","tip") and isinstance(v,str) and v.strip()}
    except (ValueError,KeyError,TypeError,httpx.HTTPError,Exception):
        # Do not log the upstream response, key, chess position or child data.
        return None

def _summary(db,cid):
    """Use evidence thresholds; 'not yet practiced' is not a weakness."""
    rows=db.execute(select(Puzzle.category,Attempt.correct)
        .join(Attempt,Puzzle.id==Attempt.puzzle_id)
        .where(Attempt.child_id==cid).order_by(Attempt.id.desc()).limit(60)).all()
    counts={cat:{"attempts":0,"correct":0} for cat in CATEGORIES}
    for category,correct in rows:
        if category in counts:
            counts[category]["attempts"]+=1
            counts[category]["correct"]+=int(correct)
    for value in counts.values():
        value["accuracy"]=round(100*value["correct"]/value["attempts"]) if value["attempts"] else None
    supported=[(name,c) for name,c in counts.items() if c["attempts"]>=3]
    weak=sorted(supported,key=lambda pair:(pair[1]["accuracy"],-pair[1]["attempts"]))
    stronger=sorted(supported,key=lambda pair:(-pair[1]["accuracy"],-pair[1]["attempts"]))
    weakest=weak[0][0] if weak and weak[0][1]["accuracy"]<80 else None
    return counts,weakest,([x[0] for x in stronger[:2]] or [])

def _plan(db,cid):
    stats,weakest,stronger=_summary(db,cid)
    # Balanced session: calculation + safeguarding + strategy + endgame + revision.
    desired=[weakest or "tactics","safety","strategy","endgames","tactics","thinking"]
    attempted=set(db.scalars(select(Attempt.puzzle_id).where(Attempt.child_id==cid)).all())
    chosen=[];used=set()
    rng=random.Random(now().strftime("%Y%m%d")+":"+str(cid)+":"+uuid.uuid4().hex[:6])
    for i,cat in enumerate(desired):
        candidates=db.scalars(select(Puzzle).where(Puzzle.category==cat)).all()
        if not candidates:continue
        target=650+min(520,sum(v["attempts"] for v in stats.values())*9)
        unused=[p for p in candidates if p.id not in attempted and p.id not in used]
        pool=unused or [p for p in candidates if p.id not in used]
        if not pool:continue
        pool.sort(key=lambda p:(abs(p.rating-target),p.id))
        pick=rng.choice(pool[:min(8,len(pool))])
        used.add(pick.id)
        lesson=next((l for l in LESSONS if l["theme"]==pick.theme),None)
        chosen.append({"number":i+1,"puzzle_id":pick.id,
            "title":pick.title,"category":cat,"theme":pick.theme,
            "rating":pick.rating,"duration_minutes":3 if pick.kind=="spot" else 5,
            "goal":lesson["why"] if lesson else CATEGORIES[cat]["description"],
            "thinking_tip":THEME_HINTS.get(pick.theme,"Before moving, look for checks, captures and threats.")})
    if not chosen:raise HTTPException(404,"No verified practice positions available")
    weakest_note=("Your recent results suggest more practice with "+CATEGORIES[weakest]["label"].lower()+". "
                  "This is a practice signal, not a verdict about your ability.") if weakest else (
                  "There's not enough practice history yet to identify a reliable weak area. "
                  "This session helps establish your baseline.")
    return {"coach":"Hoang","source":"verified","created_at":now().isoformat()+"Z",
        "focus_category":weakest or "tactics",
        "evidence":stats,"strengths":stronger,
        "weakness_note":weakest_note,
        "message":"I prepared six short challenges to build your chess thinking.",
        "focus":"Find your opponent's threats before each move. Then check your candidate moves.",
        "tip":"Take time to explain one reason for each choice.",
        "missions":chosen}

def _plan_view(row):
    if not row:return None
    body=json.loads(row.body)
    return {"id":row.id,**body}

def setup_coach(app,session,child,parent,training_info):
    router=APIRouter(prefix="/api",tags=["coach-hoang"])

    @router.get("/child/coach/status")
    def child_status(db:Session=Depends(session),u=Depends(child)):
        pid=_parent_id(db,u.id)
        enabled,remaining,limit=_permission(db,pid)
        latest=db.scalar(select(CoachPlan).where(CoachPlan.child_id==u.id)
            .order_by(CoachPlan.created_at.desc(),CoachPlan.id.desc()).limit(1))
        return {"coach":"Hoang","ai_available":enabled,"remaining_today":remaining,
                "daily_limit":limit,"plan":_plan_view(latest)}

    @router.post("/child/coach/plan")
    def new_plan(db:Session=Depends(session),u=Depends(child)):
        pid=_parent_id(db,u.id)
        if not pid:raise HTTPException(403,"A parent must link this account")
        plan=_plan(db,u.id)
        # No names, full gameplay histories, user IDs or secret answer lines sent.
        encrypted=_use_quota(db,pid)
        if encrypted:
            data=_call_model(encrypted,
                "You are Coach Hoang, an experienced and kind educational chess tutor. "
                "Your student is elementary-school aged. Write three SHORT age-appropriate "
                "JSON strings: opening, focus and tip. Use only the supplied aggregated "
                "performance and verified lesson metadata. Never invent chess moves, puzzle "
                "solutions, ratings or diagnoses. Do not request personal information, "
                "promise prizes, or use pressure or shame. Encourage thinking habits.",
                {"performance":plan["evidence"],"identified_focus":plan["focus_category"],
                 "confidence_note":plan["weakness_note"],
                 "exercise_themes":[{"category":m["category"],"theme":m["theme"],
                                     "goal":m["goal"]} for m in plan["missions"]]},360)
            if data and len(data)==3:
                plan.update({"source":"ai-assisted",**data})
        row=CoachPlan(id=uuid.uuid4().hex,child_id=u.id,parent_id=pid,
                      body=json.dumps(plan,ensure_ascii=False))
        db.add(row);db.commit()
        return _plan_view(row)

    @router.post("/child/coach/mission/start")
    def start_mission(data:MissionStart,db:Session=Depends(session),u=Depends(child)):
        plan=db.get(CoachPlan,data.plan_id)
        if not plan or plan.child_id!=u.id:raise HTTPException(404,"Training plan not found")
        body=json.loads(plan.body)
        if data.puzzle_id not in {x["puzzle_id"] for x in body["missions"]}:
            raise HTTPException(403,"This exercise is not in your training plan")
        puzzle=db.get(Puzzle,data.puzzle_id)
        if not puzzle:raise HTTPException(404,"Training puzzle not found")
        t=Training(child_id=u.id,puzzle_id=puzzle.id,mode="puzzle",fen=puzzle.fen,moves="[]")
        db.add(t);db.commit()
        return training_info(db,t)

    @router.post("/child/coach/explain")
    def explain(data:ExplanationRequest,db:Session=Depends(session),u=Depends(child)):
        t=db.get(Training,data.session_id)
        if not t or t.child_id!=u.id or t.mode!="puzzle" or not t.puzzle_id:
            raise HTTPException(404,"Exercise not found")
        p=db.get(Puzzle,t.puzzle_id)
        hint=THEME_HINTS.get(p.theme,"Check your opponent's threats, then look for checks and captures.")
        if data.mode=="hint":
            # Always safe: no solution or target square is sent, no API cost.
            return {"coach":"Hoang","source":"verified","opening":"Try this thinking question:",
                    "focus":hint,"tip":"Take your time. You can do it."}
        if not t.solved and not t.revealed:
            raise HTTPException(403,"Finish this exercise or ask your parent to reveal the answer first")
        fallback={"coach":"Hoang","source":"verified",
            "opening":"Good effort. Let's understand what this position teaches.",
            "focus":p.explanation[:330],
            "tip":"Practice finding the idea again without moving pieces first."}
        pid=_parent_id(db,u.id)
        encrypted=_use_quota(db,pid) if pid else None
        if encrypted:
            played=[m.get("move") for m in json.loads(t.moves)
                    if m.get("move") and not m.get("auto")][:8]
            feedback=_call_model(encrypted,
                "You are Coach Hoang, a patient chess teacher for a young child. "
                "Explain a COMPLETED chess exercise in three short JSON strings: opening, "
                "focus, tip. Treat the supplied teaching explanation as authoritative. "
                "Do not invent chess sequences, optimality claims or moves, do not "
                "overstate the child's skill, and do not ask for private information. "
                "Write direct, supportive teaching advice.",
                {"category":p.category,"theme":p.theme,"exercise_title":p.title,
                 "teaching_explanation":p.explanation,"position_fen":p.fen,
                 "student_attempted_moves":played},280)
            if feedback and len(feedback)==3:
                fallback.update({"source":"ai-assisted",**feedback})
        return fallback

    @router.get("/parent/children/{child_id}/coach")
    def parent_view(child_id:int,db:Session=Depends(session),u=Depends(parent)):
        if not db.get(Family,(u.id,child_id)):raise HTTPException(404,"Child not found")
        row=db.scalar(select(CoachPlan).where(CoachPlan.child_id==child_id)
            .order_by(CoachPlan.created_at.desc(),CoachPlan.id.desc()).limit(1))
        return {"coach":"Hoang","plan":_plan_view(row)}

    app.include_router(router)
