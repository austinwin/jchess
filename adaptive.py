"""Adaptive chess strength and grounded post-game feedback.

Stockfish evaluates chess. An optional language model can explain the
engine's analysis, but is never allowed to invent or select a board move.
"""
import os
import random
import shutil
from pathlib import Path
import chess
import chess.engine
from sqlalchemy import select
from db import Attempt, Game
from bot import choose_move as legacy_bot

SEARCH_SECONDS={"easy":0.07,"medium":0.11,"hard":0.18}
DEFAULT_PATH="/usr/games/stockfish"

def engine_path():
    configured=os.getenv("STOCKFISH_PATH",DEFAULT_PATH)
    return configured if Path(configured).is_file() else shutil.which("stockfish")

def learner_profile(db,child_id):
    """Transparent practice indicator, NOT an official or calibrated Elo."""
    attempts=db.scalars(select(Attempt).where(Attempt.child_id==child_id)
                        .order_by(Attempt.id.desc()).limit(40)).all()
    total=len(attempts)
    correct=sum(1 for a in attempts if a.correct)
    accuracy=correct/total if total else None
    games=db.scalars(select(Game).where(Game.child_id==child_id,
                         Game.mode=="bot",Game.status.in_(["white_wins","black_wins","draw"]))
                         .order_by(Game.created_at.desc()).limit(15)).all()
    wins=sum(g.status=="white_wins" for g in games)
    losses=sum(g.status=="black_wins" for g in games)
    # Begin at 45. Only move the estimate substantially after multiple
    # recorded attempts; recent results gradually outweigh the default.
    confidence=min(1.0,total/16)
    practice=(accuracy-0.55)*50*confidence if accuracy is not None else 0
    matches=max(-12,min(12,(wins-losses)*3))
    score=max(15,min(95,round(45+practice+matches)))
    band="Learning" if score<43 else "Developing" if score<65 else "Advancing"
    recommendation="easy" if score<44 else "medium" if score<72 else "hard"
    return {"practice_score":score,"band":band,"recommended_level":recommendation,
            "puzzles_reviewed":total,"puzzle_accuracy":round(accuracy*100) if accuracy is not None else None,
            "completed_bot_games":len(games),"wins":wins,"losses":losses,
            "description":"A practice estimate based on recent verified results, not an Elo rating."}

def skill_setting(level,practice_score):
    """Conservative learning-oriented settings; selected tier remains meaningful."""
    level=(level if level in SEARCH_SECONDS else "medium")
    offset=max(-2,min(4,round((practice_score-50)/11)))
    base={"easy":0,"medium":4,"hard":10}[level]
    lower,upper={"easy":(0,4),"medium":(2,9),"hard":(6,17)}[level]
    return max(lower,min(upper,base+offset))

def _engine():
    path=engine_path()
    if not path:return None
    return chess.engine.SimpleEngine.popen_uci(path,timeout=5.0)

def play(board,level="medium",practice_score=45):
    """Legal adaptive move, with transparent source for fallback monitoring."""
    if board.is_game_over(claim_draw=True):return None,"none"
    engine=None
    try:
        engine=_engine()
        if engine is not None:
            options={"Threads":1,"Hash":8,"UCI_LimitStrength":False,
                     "Skill Level":skill_setting(level,practice_score)}
            engine.configure({k:v for k,v in options.items() if k in engine.options})
            if level=="easy":
                # Select among a few engine-evaluated alternatives for
                # approachable, not intentionally nonsensical, beginner play.
                lines=engine.analyse(board,chess.engine.Limit(time=0.10),multipv=4)
                if isinstance(lines,dict):lines=[lines]
                candidates=[row["pv"][0] for row in lines if row.get("pv") and row["pv"][0] in board.legal_moves]
                if candidates:
                    weights=[4,4,3,2][:len(candidates)]
                    return random.choices(candidates,weights=weights,k=1)[0],"stockfish"
            result=engine.play(board,chess.engine.Limit(time=SEARCH_SECONDS.get(level,0.11)))
            if result.move in board.legal_moves:return result.move,"stockfish"
    except (OSError,chess.engine.EngineError,chess.engine.EngineTerminatedError,TimeoutError,ValueError):
        pass
    finally:
        if engine:
            try:engine.quit()
            except Exception:pass
    # Fallback still validates chess moves and never calls a paid API.
    return legacy_bot(board,level),"builtin"

def _evaluate(engine,board,seconds=0.055):
    analysis=engine.analyse(board,chess.engine.Limit(time=seconds))
    pv=analysis.get("pv") or []
    score=analysis.get("score")
    cp=score.white().score(mate_score=10000) if score else None
    return (pv[0].uci() if pv else None),cp

def evaluate_student_move(board,move):
    """Assess White's move using before/after Stockfish evaluations."""
    if board.turn!=chess.WHITE or move not in board.legal_moves:return None
    engine=None
    try:
        engine=_engine()
        if engine is None:return None
        engine.configure({k:v for k,v in {"Threads":1,"Hash":8}.items() if k in engine.options})
        best,before=_evaluate(engine,board)
        after_board=board.copy(stack=True)
        after_board.push(move)
        _,after=_evaluate(engine,after_board)
        if before is None or after is None:return None
        loss=max(0,min(1500,before-after))
        if loss>=250:
            label="Big opportunity"
            guidance="Before moving, check for forcing moves and whether a piece becomes undefended."
            theme="safety"
        elif loss>=110:
            label="Worth another look"
            guidance="Compare your candidate move with checks, captures and immediate threats."
            theme="tactics"
        else:
            label="Sound thinking"
            guidance="Keep checking your opponent's threats before choosing a move."
            theme="thinking"
        return {"played":move.uci(),"best":best,"loss_cp":loss,"label":label,
                "guidance":guidance,"suggested_category":theme}
    except (OSError,chess.engine.EngineError,chess.engine.EngineTerminatedError,TimeoutError,ValueError):
        return None
    finally:
        if engine:
            try:engine.quit()
            except Exception:pass

def review_game(game,max_moves=12):
    """Return actionable moments without revealing a fabricated Elo rating."""
    board=chess.Board()
    moments=[]
    white_moves=0
    for item in __import__("json").loads(game.moves):
        move=chess.Move.from_uci(item["uci"])
        if board.turn==chess.WHITE and white_moves<max_moves and item["actor"]=="white":
            assessment=evaluate_student_move(board,move)
            if assessment:
                assessment["move_number"]=board.fullmove_number
                moments.append(assessment)
            white_moves+=1
        board.push(move)
    moments.sort(key=lambda m:m["loss_cp"],reverse=True)
    return {"analysed_white_moves":len(moments),"moments":moments[:3],
            "summary":"Review your three most instructive moments. A single move does not define your skill.",
            "engine_available":bool(engine_path())}
