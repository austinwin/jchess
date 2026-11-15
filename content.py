"""Generated, legally checked teaching exercises plus optional Lichess CC0 import."""
import random
import chess

CATEGORIES={
 "safety":dict(label="Protect your pieces",icon="shield",description="Spot valuable hanging pieces"),
 "tactics":dict(label="Tactics treasure",icon="zap",description="Forks and tactical attacks"),
 "thinking":dict(label="Think like a champion",icon="brain",description="See your opponent's threats"),
 "endgames":dict(label="Endgame hero",icon="crown",description="Promotion and checkmate"),
 "openings":dict(label="Opening explorer",icon="compass",description="Develop pieces and control the center"),
 "strategy":dict(label="Strategy studio",icon="target",description="Make plans: center, king safety, activity, pawns and open files")
}
def make(pid,title,category,theme,b,moves,why,rating=800,kind="move",target=""):
    try:
        if not b.is_valid():return None
        g=b.copy()
        for u in moves:
            move=chess.Move.from_uci(u)
            if move not in g.legal_moves:return None
            g.push(move)
        return dict(id=pid,title=title,category=category,theme=theme,rating=rating,
                    fen=b.fen(),solution=moves,explanation=why,kind=kind,target=target,source="built-in")
    except (ValueError,AssertionError):return None
def board(wk,bk,wp,bp):
    b=chess.Board(None);b.turn=chess.WHITE
    b.set_piece_at(wk,chess.Piece(chess.KING,True))
    b.set_piece_at(bk,chess.Piece(chess.KING,False))
    for s,p in wp:b.set_piece_at(s,chess.Piece(p,True))
    for s,p in bp:b.set_piece_at(s,chess.Piece(p,False))
    return b

def seed():
    rng=random.Random(20261115);out=[];seen=set()
    def add(p):
        if p and (p["fen"],p["category"]) not in seen:
            seen.add((p["fen"],p["category"]));out.append(p)
    openings=[
      ([], "e4","Claim the center with a pawn"),([],"d4","Claim the center with a pawn"),
      (["e4","e5"],"Nf3","Develop your knight and attack e5"),
      (["d4","d5"],"Nc3","Develop a knight toward the center"),
      (["e4","e5","Nf3","Nc6"],"Bc4","Bring your bishop toward f7"),
      (["e4","e5","Nf3","Nc6","Bc4","Bc5","d3","Nf6"],"O-O","Castle to protect your king"),
      (["e4","c5"],"Nf3","Develop a knight"),(["e4","e6"],"d4","Build a pawn center"),
      (["d4","Nf6"],"c4","Challenge the center"),
      (["e4","e5","Nf3","Nc6","Bb5","a6"],"Ba4","Save your bishop"),
      (["d4","d5","Nf3","Nf6"],"e3","Protect and develop"),
      (["e4","e5","Nf3","Nc6","Bc4","Bc5","c3","Nf6"],"d4","Strike in the center")
    ]
    for i,(line,answer,why) in enumerate(openings):
        b=chess.Board()
        try:
            for san in line:b.push_san(san)
            if b.turn!=chess.WHITE:continue
            m=b.parse_san(answer)
            add(make("opening-%03d"%i,"Play "+answer+" · "+why,"openings","development",b,[m.uci()],why+". Watch the opponent's next threat.",650+i*20))
        except ValueError: pass
    # Promote a pawn on a wide variety of files and king placements.
    for i in range(350):
        f=i%8;p=chess.square(f,6);q=chess.square(f,7)
        wk=rng.choice(list(chess.SQUARES));bk=rng.choice(list(chess.SQUARES))
        if len({wk,bk,p,q})!=4 or chess.square_distance(wk,bk)<3:continue
        b=board(wk,bk,[(p,chess.PAWN)],[])
        m=chess.Move(p,q,promotion=chess.QUEEN)
        if m in b.legal_moves:
            add(make("promotion-%03d"%i,"Promote your pawn!","endgames","promotion",b,[m.uci()],
                     "When a pawn reaches the last rank, you can turn it into a queen.",680+(i%8)*25))
    squares=list(chess.SQUARES)
    # A piece is left unprotected: capture it and collect material.
    for i in range(900):
        wk,bk,f,t=rng.sample(squares,4)
        if chess.square_distance(wk,bk)<3:continue
        attacker=rng.choice([chess.QUEEN,chess.ROOK,chess.BISHOP,chess.KNIGHT])
        victim=rng.choice([chess.QUEEN,chess.ROOK,chess.BISHOP,chess.KNIGHT])
        b=board(wk,bk,[(f,attacker)],[(t,victim)])
        move=chess.Move(f,t)
        if b.is_valid() and move in b.legal_moves and not b.is_attacked_by(chess.BLACK,t):
            add(make("capture-%04d"%i,"Capture the hanging "+chess.piece_name(victim)+"!","safety","hanging-piece",b,[move.uci()],
                     "Notice which pieces are undefended before you move.",650+(i%10)*30))
    # A knight jumps to attack the opponent's queen and rook simultaneously.
    fork_count=0
    for i in range(7000):
        wk,bk,f,t=rng.sample(squares,4)
        if chess.square_distance(wk,bk)<3 or t not in chess.SquareSet(chess.BB_KNIGHT_ATTACKS[f]):continue
        victim_squares=[s for s in chess.SquareSet(chess.BB_KNIGHT_ATTACKS[t]) if s not in (wk,bk,f,t)]
        if len(victim_squares)<2:continue
        q,r=rng.sample(victim_squares,2)
        b=board(wk,bk,[(f,chess.KNIGHT)],[(q,chess.QUEEN),(r,chess.ROOK)])
        m=chess.Move(f,t)
        if b.is_valid() and m in b.legal_moves and not b.is_attacked_by(chess.BLACK,t):
            old=len(out)
            add(make("fork-%04d"%i,"Make a knight fork!","tactics","fork",b,[m.uci()],
                     "The knight attacks two valuable pieces with one move.",720+(i%10)*30))
            if len(out)>old:fork_count+=1
            if fork_count>=170:break
    # The child taps the threatened piece instead of guessing a chess move.
    spot_count=0
    for i in range(2500):
        wk,bk,t,f=rng.sample(squares,4)
        if chess.square_distance(wk,bk)<3:continue
        valuable=rng.choice([chess.QUEEN,chess.ROOK,chess.BISHOP])
        attacker=rng.choice([chess.ROOK,chess.BISHOP,chess.KNIGHT])
        b=board(wk,bk,[(t,valuable)],[(f,attacker)])
        if b.is_valid() and not b.is_check() and b.is_attacked_by(chess.BLACK,t):
            old=len(out)
            add(make("threat-%04d"%i,"Which piece is in danger?","thinking","threat",b,[],
                     "Look at what the opponent attacks before making your move.",700+(i%8)*25,
                     "spot",chess.square_name(t)))
            if len(out)>old:spot_count+=1
            if spot_count>=190:break
    # Unique, rules-verified mate-in-one puzzles.
    mates=0
    for i in range(6000):
        wk,bk,q=rng.sample(squares,3)
        if chess.square_distance(wk,bk)<2:continue
        b=board(wk,bk,[(q,chess.QUEEN)],[])
        if not b.is_valid() or b.is_check():continue
        found=[]
        for m in list(b.legal_moves):
            b.push(m)
            if b.is_checkmate():found.append(m.uci())
            b.pop()
            if len(found)>1:break
        if len(found)==1:
            old=len(out)
            add(make("mate-%04d"%i,"Checkmate in one!","endgames","mate-in-one",b,found,
                     "The king is checked and has no legal escape.",750+(i%8)*25))
            if len(out)>old:mates+=1
            if mates>=120:break
    from lessons import guided_positions
    for item in guided_positions(make,board):add(item)
    return out

def from_lichess(record):
    """Lichess FEN is before an opponent move; the first move must be applied."""
    try:
        row=record;g=chess.Board(row["FEN"]);line=str(row["Moves"]).split()
        if len(line)<2 or len(line)>9:return None
        first=chess.Move.from_uci(line[0])
        if first not in g.legal_moves:return None
        g.push(first)
        sol=line[1:]
        for_validate=g.copy()
        for u in sol:
            m=chess.Move.from_uci(u)
            if m not in for_validate.legal_moves:return None
            for_validate.push(m)
        themes=set(str(row.get("Themes","")).split())
        theme=next((s for s in ("fork","pin","skewer","discoveredAttack","mateIn1","mateIn2","hangingPiece","defensiveMove","promotion") if s in themes),"tactics")
        cat="endgames" if any(s in themes for s in ("endgame","mateIn1","mateIn2")) else "safety" if "hangingPiece" in themes else "tactics"
        p=make("lichess-"+str(row["PuzzleId"]),theme.replace("In"," in ").title()+" challenge",cat,theme,g,sol,
               "Look for checks, captures and threats, then replay the solution.",int(row["Rating"]))
        if p:p["source"]="Lichess CC0"
        return p
    except (ValueError,KeyError,AssertionError):return None
