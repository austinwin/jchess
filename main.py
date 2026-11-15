"""JChess Academy: QPyServe + FastAPI, family-private coaching and legal chess play."""
import base64, hashlib, json, os, secrets, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import timedelta
from urllib.parse import urlsplit
import chess
import httpx
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from db import DB, User, Family, Login, Puzzle, Training, Attempt, AIConfig, initialize, hash_pw, verify_pw, digest, is_parent, now
from content import CATEGORIES, seed

@asynccontextmanager
async def lifespan(app):
    initialize()
    with DB.begin() as db:
        if not db.scalar(select(Puzzle.id).limit(1)):
            for item in seed():
                item["solution"]=json.dumps(item["solution"])
                db.add(Puzzle(**item))
    yield

app=FastAPI(title="JChess Academy API",version="1.0.0",lifespan=lifespan)
failures=defaultdict(deque)

@app.middleware("http")
async def same_origin(request:Request,call_next):
    if request.method in ("POST","PUT","PATCH","DELETE"):
        origin=request.headers.get("origin","")
        if origin and urlsplit(origin).netloc!=request.headers.get("host",""):
            return Response(status_code=403,content="Cross-origin mutation blocked")
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"]="DENY"
    return response

def session():
    with DB() as db:yield db
def auth(request:Request,db:Session=Depends(session)):
    cookie=request.cookies.get("jchess_session","")
    if not cookie:return None
    ticket=db.get(Login,digest(cookie))
    if not ticket or ticket.expires_at<now():return None
    return db.get(User,ticket.user_id)
def require(user=Depends(auth)):
    if not user:raise HTTPException(401,"Please sign in")
    if user.must_reset:raise HTTPException(403,"change_password")
    return user
def parent(user=Depends(require)):
    if user.role!="parent":raise HTTPException(403,"Parent access required")
    return user
def child(user=Depends(require)):
    if user.role!="child":raise HTTPException(403,"Child access required")
    return user
def family_child(db,pid,cid):
    if not is_parent(db,pid,cid):raise HTTPException(404,"Child not found")
    result=db.get(User,cid)
    if not result:raise HTTPException(404,"Child not found")
    return result
def safe_user(u):
    return dict(id=u.id,username=u.username,name=u.name,role=u.role,must_reset=u.must_reset)
def puzzle_public(p,for_parent=False,revealed=False):
    val=dict(id=p.id,title=p.title,category=p.category,theme=p.theme,rating=p.rating,
             fen=p.fen,kind=p.kind,source=p.source)
    if for_parent or revealed:
        val.update(solution=json.loads(p.solution),target=p.target,explanation=p.explanation)
    return val
def training_info(db,s,parent_view=False):
    if not s:return None
    p=db.get(Puzzle,s.puzzle_id) if s.puzzle_id else None
    data=dict(id=s.id,child_id=s.child_id,mode=s.mode,fen=s.fen,moves=json.loads(s.moves),
              step=s.step,errors=s.errors,solved=s.solved,revealed=s.revealed,
              version=s.version,updated_at=s.updated_at.isoformat()+"Z")
    if p:data["puzzle"]=puzzle_public(p,parent_view,s.revealed)
    return data
def latest(db,child_id):
    return db.scalar(select(Training).where(Training.child_id==child_id).order_by(Training.id.desc()).limit(1))
def count_stats(db,cid):
    rows=db.execute(select(Puzzle.category,Attempt.correct).join(Attempt,Puzzle.id==Attempt.puzzle_id).where(Attempt.child_id==cid)).all()
    by={cat:dict(attempts=0,correct=0) for cat in CATEGORIES}
    for c,correct in rows:
        if c in by:
            by[c]["attempts"]+=1
            by[c]["correct"]+=int(correct)
    for obj in by.values():
        obj["accuracy"]=round(100*obj["correct"]/obj["attempts"]) if obj["attempts"] else None
    completed=sum(x["attempts"] for x in by.values())
    return dict(completed=completed,correct=sum(x["correct"] for x in by.values()),
                xp=sum(x["correct"]*15+(x["attempts"]-x["correct"])*5 for x in by.values()),
                by_category=by)
def bump(s):
    s.version+=1;s.updated_at=now()
def add_attempt(db,s):
    db.add(Attempt(child_id=s.child_id,puzzle_id=s.puzzle_id,correct=s.errors==0,errors=s.errors))
def require_current(db,cid):
    s=latest(db,cid)
    if not s:raise HTTPException(404,"Start an exercise first")
    return s

class Credentials(BaseModel):
    username:str=Field(min_length=1,max_length=40)
    password:str=Field(min_length=1,max_length=200)
class Signup(BaseModel):
    username:str=Field(min_length=3,max_length=40,pattern=r"^[a-zA-Z][a-zA-Z0-9_]{2,39}$")
    password:str=Field(min_length=10,max_length=200)
    name:str=Field(min_length=1,max_length=80)
class ChangePassword(BaseModel):
    current:str
    new:str=Field(min_length=10,max_length=200)
class NewChild(Signup):pass
class StartPuzzle(BaseModel):
    category:str|None=None
class MoveRequest(BaseModel):
    uci:str=Field(min_length=4,max_length=5)
class SquareRequest(BaseModel):
    square:str=Field(pattern=r"^[a-h][1-8]$")
class RevealRequest(BaseModel):
    reveal:bool
class AIOptions(BaseModel):
    enabled:bool
    api_key:str|None=Field(default=None,max_length=500)

@app.get("/api/health")
def health():
    return {"ok":True,"service":"jchess"}

@app.post("/api/auth/login")
def login(input:Credentials,response:Response,request:Request,db:Session=Depends(session)):
    key=(request.client.host if request.client else "unknown",input.username.lower())
    queue=failures[key];current=time.monotonic()
    while queue and current-queue[0]>600:queue.popleft()
    if len(queue)>=8:raise HTTPException(429,"Too many attempts. Try again later.")
    u=db.scalar(select(User).where(User.username==input.username.strip().lower()))
    if not u or not verify_pw(input.password,u.password_hash):
        queue.append(current);raise HTTPException(401,"Invalid username or password")
    queue.clear()
    token=secrets.token_urlsafe(40)
    db.add(Login(token_hash=digest(token),user_id=u.id,expires_at=now()+timedelta(days=7)))
    db.commit()
    response.set_cookie("jchess_session",token,httponly=True,secure=bool(os.getenv("RENDER") or request.url.scheme=="https"),
                        samesite="lax",max_age=604800,path="/")
    return safe_user(u)

@app.post("/api/auth/register")
def register(input:Signup,db:Session=Depends(session)):
    name=input.username.lower().strip()
    if db.scalar(select(User.id).where(User.username==name)):
        raise HTTPException(409,"Username is already taken")
    u=User(username=name,name=input.name.strip(),password_hash=hash_pw(input.password),role="parent")
    db.add(u);db.commit()
    return {"ok":True,"message":"Parent account created. Please sign in."}

@app.get("/api/auth/me")
def me(u=Depends(auth)):
    return safe_user(u) if u else None

@app.post("/api/auth/password")
def update_password(input:ChangePassword,response:Response,db:Session=Depends(session),u=Depends(auth)):
    if not u:raise HTTPException(401,"Sign in first")
    if not verify_pw(input.current,u.password_hash):raise HTTPException(400,"Current password is incorrect")
    if input.current==input.new:raise HTTPException(400,"Choose a new password")
    u.password_hash=hash_pw(input.new);u.must_reset=False
    db.commit();return {"ok":True}

@app.post("/api/auth/logout")
def logout(request:Request,response:Response,db:Session=Depends(session)):
    raw=request.cookies.get("jchess_session")
    if raw:
        t=db.get(Login,digest(raw))
        if t:db.delete(t);db.commit()
    response.delete_cookie("jchess_session",path="/")
    return {"ok":True}

@app.get("/api/catalog")
def catalog(db:Session=Depends(session),u=Depends(require)):
    counts=dict(db.execute(select(Puzzle.category,func.count(Puzzle.id)).group_by(Puzzle.category)).all())
    return {"categories":{k:{**v,"count":counts.get(k,0)} for k,v in CATEGORIES.items()},
            "total":sum(counts.values())}

@app.get("/api/child/dashboard")
def child_dashboard(db:Session=Depends(session),u=Depends(child)):
    return {"user":safe_user(u),"stats":count_stats(db,u.id),"active":training_info(db,latest(db,u.id))}

@app.post("/api/child/puzzle/start")
def start_puzzle(input:StartPuzzle,db:Session=Depends(session),u=Depends(child)):
    cat=input.category
    if cat and cat not in CATEGORIES:raise HTTPException(400,"Unknown exercise category")
    stats=count_stats(db,u.id)
    if not cat:
        by=stats["by_category"]
        cat=min(CATEGORIES,key=lambda k:(by[k]["accuracy"] if by[k]["accuracy"] is not None else 55,
                                         by[k]["attempts"]))
    attempted={r for r in db.scalars(select(Attempt.puzzle_id).where(Attempt.child_id==u.id)).all()}
    catalog=db.scalars(select(Puzzle).where(Puzzle.category==cat)).all()
    if not catalog:raise HTTPException(404,"No exercises in this category")
    target_rating=650+min(600,stats["completed"]*8)
    unseen=[p for p in catalog if p.id not in attempted]
    pool=unseen or catalog
    # Deterministic cycle, then increasingly challenging material.
    p=min(pool,key=lambda x:(abs(x.rating-target_rating),x.id))
    s=Training(child_id=u.id,puzzle_id=p.id,mode="puzzle",fen=p.fen,moves="[]")
    db.add(s);db.commit()
    return training_info(db,s)

@app.post("/api/child/sandbox/start")
def start_sandbox(db:Session=Depends(session),u=Depends(child)):
    s=Training(child_id=u.id,mode="sandbox",fen=chess.STARTING_FEN,moves="[]")
    db.add(s);db.commit()
    return training_info(db,s)

@app.get("/api/child/current")
def child_current(db:Session=Depends(session),u=Depends(child)):
    return training_info(db,latest(db,u.id))

@app.post("/api/child/puzzle/move")
def puzzle_move(data:MoveRequest,db:Session=Depends(session),u=Depends(child)):
    s=require_current(db,u.id)
    if s.mode!="puzzle" or s.solved:raise HTTPException(409,"Start a new puzzle")
    p=db.get(Puzzle,s.puzzle_id)
    if p.kind!="move":raise HTTPException(400,"Tap the threatened piece")
    try:m=chess.Move.from_uci(data.uci)
    except ValueError:raise HTTPException(400,"Invalid chess move")
    b=chess.Board(s.fen)
    if m not in b.legal_moves:raise HTTPException(400,"That move is not legal")
    line=json.loads(p.solution);correct=s.step<len(line) and data.uci==line[s.step]
    logs=json.loads(s.moves)
    logs.append(dict(move=data.uci,correct=correct,auto=False,at=now().isoformat()+"Z"))
    if correct:
        b.push(m);s.step+=1
        if s.step<len(line):
            reply=chess.Move.from_uci(line[s.step])
            if reply in b.legal_moves:
                b.push(reply);logs.append(dict(move=reply.uci(),correct=True,auto=True))
                s.step+=1
        s.fen=b.fen()
        if s.step>=len(line):
            s.solved=True;add_attempt(db,s)
    else:s.errors+=1
    s.moves=json.dumps(logs);bump(s);db.commit()
    return {"correct":correct,"state":training_info(db,s)}

@app.post("/api/child/puzzle/spot")
def spot(data:SquareRequest,db:Session=Depends(session),u=Depends(child)):
    s=require_current(db,u.id)
    if s.mode!="puzzle" or s.solved:raise HTTPException(409,"Start a new puzzle")
    p=db.get(Puzzle,s.puzzle_id)
    if p.kind!="spot":raise HTTPException(400,"Move a chess piece")
    correct=data.square==p.target
    logs=json.loads(s.moves);logs.append(dict(square=data.square,correct=correct,at=now().isoformat()+"Z"))
    s.moves=json.dumps(logs)
    if correct:s.solved=True;add_attempt(db,s)
    else:s.errors+=1
    bump(s);db.commit()
    return {"correct":correct,"state":training_info(db,s)}

@app.post("/api/child/sandbox/move")
def sandbox_move(data:MoveRequest,db:Session=Depends(session),u=Depends(child)):
    s=require_current(db,u.id)
    if s.mode!="sandbox":raise HTTPException(409,"Start free-play first")
    b=chess.Board(s.fen)
    try:m=chess.Move.from_uci(data.uci)
    except ValueError:raise HTTPException(400,"Invalid move")
    if m not in b.legal_moves:raise HTTPException(400,"Illegal move")
    san=b.san(m);b.push(m);s.fen=b.fen()
    logs=json.loads(s.moves);logs.append(dict(move=m.uci(),san=san,auto=False))
    s.moves=json.dumps(logs);bump(s);db.commit()
    return training_info(db,s)

@app.get("/api/parent/children")
def children(db:Session=Depends(session),u=Depends(parent)):
    ids=db.scalars(select(Family.child_id).where(Family.parent_id==u.id)).all()
    return [{"user":safe_user(k),"stats":count_stats(db,k.id),"active":training_info(db,latest(db,k.id),True)}
            for cid in ids if (k:=db.get(User,cid))]

@app.post("/api/parent/children")
def create_child(data:NewChild,db:Session=Depends(session),u=Depends(parent)):
    name=data.username.lower().strip()
    if db.scalar(select(User.id).where(User.username==name)):raise HTTPException(409,"Username already exists")
    kid=User(username=name,name=data.name.strip(),role="child",password_hash=hash_pw(data.password))
    db.add(kid);db.flush();db.add(Family(parent_id=u.id,child_id=kid.id));db.commit()
    return safe_user(kid)

@app.get("/api/parent/children/{cid}/live")
def live(cid:int,db:Session=Depends(session),u=Depends(parent)):
    kid=family_child(db,u.id,cid)
    return {"child":safe_user(kid),"stats":count_stats(db,cid),
            "active":training_info(db,latest(db,cid),True)}

@app.get("/api/parent/puzzles")
def parent_puzzles(category:str|None=None,skip:int=0,limit:int=20,db:Session=Depends(session),u=Depends(parent)):
    query=select(Puzzle)
    if category:query=query.where(Puzzle.category==category)
    items=db.scalars(query.order_by(Puzzle.rating,Puzzle.id).offset(max(0,skip)).limit(min(max(1,limit),80))).all()
    return [puzzle_public(p,True) for p in items]

@app.post("/api/parent/sessions/{sid}/reveal")
def reveal(sid:int,data:RevealRequest,db:Session=Depends(session),u=Depends(parent)):
    s=db.get(Training,sid)
    if not s or not is_parent(db,u.id,s.child_id):raise HTTPException(404,"Session not found")
    if s.mode!="puzzle":raise HTTPException(400,"No solution for free play")
    s.revealed=data.reveal;bump(s);db.commit()
    return training_info(db,s,True)

def cipher():
    raw=os.getenv("AI_ENCRYPTION_KEY","")
    if not raw:raise HTTPException(503,"AI encryption secret is not configured on the server")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest()))

@app.get("/api/parent/ai")
def ai_status(db:Session=Depends(session),u=Depends(parent)):
    s=db.get(AIConfig,u.id)
    return {"enabled":bool(s and s.enabled),"has_key":bool(s and s.key_cipher)}

@app.post("/api/parent/ai")
def ai_settings(data:AIOptions,db:Session=Depends(session),u=Depends(parent)):
    s=db.get(AIConfig,u.id)
    if not s:s=AIConfig(parent_id=u.id);db.add(s)
    if data.api_key is not None:
        s.key_cipher=cipher().encrypt(data.api_key.encode()).decode() if data.api_key.strip() else ""
    if data.enabled and not s.key_cipher:raise HTTPException(400,"Enter an API key first")
    s.enabled=data.enabled;db.commit()
    return {"enabled":s.enabled,"has_key":bool(s.key_cipher)}

@app.post("/api/parent/children/{cid}/coach")
def ai_coach(cid:int,db:Session=Depends(session),u=Depends(parent)):
    family_child(db,u.id,cid)
    settings=db.get(AIConfig,u.id)
    if not settings or not settings.enabled or not settings.key_cipher:
        raise HTTPException(400,"Enable AI coaching and save your API key first")
    info=count_stats(db,cid)
    categories={cat:v for cat,v in info["by_category"].items()}
    # Only aggregated exercise performance is sent; no names, usernames or game histories.
    msg="A parent wants coaching for an elementary chess student. From these aggregated stats, "
    msg+="give 3 specific, encouraging practice recommendations, each with a reason. "
    msg+="Do not claim diagnostic certainty. No personally identifying details. Stats: "+json.dumps(categories)
    try:
        key=cipher().decrypt(settings.key_cipher.encode()).decode()
        with httpx.Client(timeout=22) as client:
            r=client.post("https://api.openai.com/v1/chat/completions",
               headers={"Authorization":"Bearer "+key},
               json={"model":"gpt-4.1-mini","temperature":0.3,"max_tokens":450,
                     "messages":[{"role":"system","content":"You are a careful chess coach for children. Never invent validated puzzle solutions."},
                                 {"role":"user","content":msg}]})
            r.raise_for_status()
            reply=r.json()["choices"][0]["message"]["content"]
        return {"feedback":reply,"stats":info}
    except Exception:
        raise HTTPException(502,"AI request failed. Check the key, account credits, and provider availability.")

if __name__=="__main__":
    from qpyserve import run
    run(app,frontend="frontend",port=int(os.getenv("PORT","1111")),host="0.0.0.0" if os.getenv("RENDER") or os.getenv("PORT") else "127.0.0.1")
