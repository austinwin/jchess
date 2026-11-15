"""Family-scoped online games and a free 3-level chess bot.
No guest registration; the unguessable friend invite is an opponent-seat capability.
"""
import json
import re
import secrets
import uuid
from datetime import datetime
import chess
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from bot import choose_move
from db import Game, Family, CloudPlay, AIConfig, digest, now

router=APIRouter(prefix="/api",tags=["games"])

class StartGame(BaseModel):
    mode:str=Field(pattern="^(bot|local|parent|friend)$")
    level:str=Field(default="easy",pattern="^(easy|medium|hard)$")
    provider:str=Field(default="builtin",pattern="^(builtin|cloud)$")

class GameMove(BaseModel):
    game_id:str=Field(min_length=32,max_length=36)
    uci:str=Field(min_length=4,max_length=5)

class FriendCode(BaseModel):
    token:str=Field(min_length=25,max_length=100)

class FriendMove(FriendCode):
    uci:str=Field(min_length=4,max_length=5)

def game_info(g):
    if g is None:return None
    return {"id":g.id,"mode":g.mode,"provider":g.provider,"level":g.level,
            "fen":g.fen,"moves":json.loads(g.moves),"status":g.status,
            "turn":"white" if chess.Board(g.fen).turn else "black",
            "version":g.version,"updated_at":g.updated_at.isoformat()+"Z"}

def _board(g):
    # Keep complete history for 3-fold-repetition and the 50-move rule.
    board=chess.Board()
    for item in json.loads(g.moves):board.push_uci(item["uci"])
    return board

def _record(board,history,move,actor):
    san=board.san(move)
    color="white" if board.turn else "black"
    board.push(move)
    history.append({"uci":move.uci(),"san":san,"color":color,"actor":actor})

def _finish(board,g):
    outcome=board.outcome(claim_draw=True)
    if outcome:
        g.status="draw" if outcome.winner is None else ("white_wins" if outcome.winner else "black_wins")

def _apply(g,uci,actor,db):
    if g.status!="active":raise HTTPException(409,"This game has ended. Start a new game.")
    board=_board(g)
    try:move=chess.Move.from_uci(uci)
    except ValueError:raise HTTPException(400,"Invalid move")
    if move not in board.legal_moves:raise HTTPException(400,"This move is not legal")
    expected="white" if board.turn else "black"
    if g.mode!="local" and expected!=actor:
        raise HTTPException(409,"Wait for your turn")
    hist=json.loads(g.moves)
    _record(board,hist,move,actor)
    _finish(board,g)
    if g.mode=="bot" and g.status=="active":
        source="builtin"
        reply=None
        if g.provider=="cloud":
            reply=_cloud_reply(board,g,db)
            if reply:source="cloud"
            else:source="fallback"
        if reply is None:reply=choose_move(board,g.level)
        if reply is not None:_record(board,hist,reply,source)
        _finish(board,g)
    g.fen=board.fen()
    g.moves=json.dumps(hist)
    g.version+=1
    g.updated_at=now()
    db.commit()
    return game_info(g)

def _cloud_permission(db,parent_id):
    settings=db.get(AIConfig,parent_id)
    permission=db.get(CloudPlay,parent_id)
    day=now().date().isoformat()
    remaining=(permission.daily_limit-(permission.used if permission.day==day else 0)) if permission else 0
    return bool(settings and settings.enabled and settings.key_cipher and permission and permission.enabled and remaining>0),max(0,remaining)

def _cloud_reply(board,g,db):
    allowed,_=_cloud_permission(db,g.parent_id)
    if not allowed:return None
    # The cap is checked under a database row lock, before any provider request.
    permission=db.scalar(select(CloudPlay).where(CloudPlay.parent_id==g.parent_id).with_for_update())
    today=now().date().isoformat()
    if permission.day!=today:permission.day=today;permission.used=0
    if permission.used>=permission.daily_limit:return None
    permission.used+=1
    settings=db.get(AIConfig,g.parent_id)
    db.flush()
    try:
        # Import only here: the key never enters the web bundle or game response.
        from main import cipher
        key=cipher().decrypt(settings.key_cipher.encode()).decode()
        legal=[m.uci() for m in board.legal_moves]
        instructions={"easy":"Choose varied, simple moves; allow occasional mistakes.",
                      "medium":"Prefer a safe tactical move while keeping the game fun.",
                      "hard":"Look for strong tactics and avoid dropping material."}
        with httpx.Client(timeout=10) as client:
            r=client.post("https://api.openai.com/v1/chat/completions",
              headers={"Authorization":"Bearer "+key},
              json={"model":"gpt-4.1-mini","max_tokens":40,"temperature":0.25,"store":False,
                    "messages":[{"role":"system","content":"You play Black in a chess game. Return exactly one legal UCI move from the list and nothing else. "+instructions[g.level]},
                                {"role":"user","content":"FEN: "+board.fen()+"\nLegal moves: "+", ".join(legal)}]})
            r.raise_for_status()
            answer=str(r.json()["choices"][0]["message"]["content"]).strip().lower()
        match=re.fullmatch(r"([a-h][1-8])([a-h][1-8])([qrbn])?",answer)
        if match and answer in legal:return chess.Move.from_uci(answer)
    except Exception:
        # Do not log API key or upstream error body. Builtin bot is always available.
        pass
    return None

def setup_games(app,session,child,parent):
    @router.get("/child/game/options")
    def game_options(db:Session=Depends(session),u=Depends(child)):
        pid=db.scalar(select(Family.parent_id).where(Family.child_id==u.id))
        allowed,remaining=_cloud_permission(db,pid) if pid else (False,0)
        return {"offline_available":True,"cloud_available":allowed,"cloud_moves_remaining":remaining,
                "parent_available":bool(pid)}

    @router.post("/child/game/start")
    def start(data:StartGame,db:Session=Depends(session),u=Depends(child)):
        pid=db.scalar(select(Family.parent_id).where(Family.child_id==u.id).order_by(Family.parent_id))
        if not pid:raise HTTPException(403,"A parent needs to link this account first")
        if data.provider=="cloud":
            available,_=_cloud_permission(db,pid)
            if data.mode!="bot" or not available:raise HTTPException(403,"Parent has not enabled cloud AI play")
        token=secrets.token_urlsafe(32) if data.mode=="friend" else None
        g=Game(id=uuid.uuid4().hex,child_id=u.id,parent_id=pid,mode=data.mode,
               provider=data.provider if data.mode=="bot" else "builtin",
               level=data.level,fen=chess.STARTING_FEN,moves="[]",
               status="active",invite_hash=digest(token) if token else None)
        db.add(g);db.commit()
        result=game_info(g)
        if token:result["invite_token"]=token
        return result

    @router.get("/child/game/current")
    def child_current_game(db:Session=Depends(session),u=Depends(child)):
        g=db.scalar(select(Game).where(Game.child_id==u.id).order_by(Game.created_at.desc(),Game.id.desc()).limit(1))
        return game_info(g)

    @router.post("/child/game/move")
    def child_game_move(data:GameMove,db:Session=Depends(session),u=Depends(child)):
        g=db.scalar(select(Game).where(Game.id==data.game_id,Game.child_id==u.id).with_for_update())
        if not g:raise HTTPException(404,"Game not found")
        if g.mode!="local" and _board(g).turn!=chess.WHITE:
            raise HTTPException(409,"Your opponent is thinking or it is their turn")
        return _apply(g,data.uci,"white" if g.mode!="local" or _board(g).turn else "black",db)

    @router.get("/parent/game/current")
    def parent_current_game(child_id:int,db:Session=Depends(session),u=Depends(parent)):
        link=db.get(Family,(u.id,child_id))
        if not link:raise HTTPException(404,"Child not found")
        g=db.scalar(select(Game).where(Game.child_id==child_id).order_by(Game.created_at.desc(),Game.id.desc()).limit(1))
        return game_info(g)

    @router.post("/parent/game/move")
    def parent_game_move(data:GameMove,db:Session=Depends(session),u=Depends(parent)):
        g=db.scalar(select(Game).where(Game.id==data.game_id,Game.parent_id==u.id).with_for_update())
        if not g or not db.get(Family,(u.id,g.child_id)):raise HTTPException(404,"Game not found")
        if g.mode!="parent":raise HTTPException(403,"This game does not have a parent seat")
        return _apply(g,data.uci,"black",db)

    @router.post("/guest/game/current")
    def guest_current(data:FriendCode,db:Session=Depends(session)):
        g=db.scalar(select(Game).where(Game.mode=="friend",Game.invite_hash==digest(data.token)))
        if not g:raise HTTPException(404,"Invite not found")
        return game_info(g)

    @router.post("/guest/game/move")
    def guest_move(data:FriendMove,db:Session=Depends(session)):
        g=db.scalar(select(Game).where(Game.mode=="friend",Game.invite_hash==digest(data.token)).with_for_update())
        if not g:raise HTTPException(404,"Invite not found")
        return _apply(g,data.uci,"black",db)

    app.include_router(router)
