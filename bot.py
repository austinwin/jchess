"""A free, deterministic-rule chess opponent; no API key or network needed."""
import random
import chess

VALUES={chess.PAWN:100,chess.KNIGHT:315,chess.BISHOP:330,chess.ROOK:510,chess.QUEEN:930,chess.KING:0}

def _score(board):
    """Position score from White's perspective; inexpensive enough for a free CPU."""
    score=0
    for sq,p in board.piece_map().items():
        file=chess.square_file(sq); rank=chess.square_rank(sq)
        center=3.5-abs(3.5-file)+3.5-abs(3.5-rank)
        bonus=(int(center*5) if p.piece_type in (chess.KNIGHT,chess.BISHOP) else
               (rank if p.color else 7-rank)*7 if p.piece_type==chess.PAWN else 0)
        score+=(VALUES[p.piece_type]+bonus)*(1 if p.color else -1)
    return score

def _moves(board):
    """Try forcing checks and captures first, improving alpha-beta pruning."""
    moves=list(board.legal_moves)
    def priority(m):
        score=(12*VALUES[board.piece_type_at(m.to_square)] if board.is_capture(m) and board.piece_type_at(m.to_square) else 0)
        if m.promotion:score+=900
        if board.gives_check(m):score+=100
        return score
    moves.sort(key=priority,reverse=True)
    return moves

def _search(board,depth,alpha,beta,nodes):
    nodes[0]+=1
    if board.is_checkmate():return -100000-depth
    if board.is_stalemate() or board.is_insufficient_material():return 0
    if depth<=0 or nodes[0]>7000:
        return _score(board)*(1 if board.turn else -1)
    best=-200000
    for move in _moves(board):
        board.push(move)
        value=-_search(board,depth-1,-beta,-alpha,nodes)
        board.pop()
        if value>best:best=value
        if value>alpha:alpha=value
        if alpha>=beta:break
    return best if best!=-200000 else 0

def choose_move(board,level="medium"):
    """Three visibly different strengths. Black or White supported."""
    moves=_moves(board)
    if not moves:return None
    if level=="easy":
        # Sometimes check or capture, often explore: friendly beginner bot.
        return random.choice(moves[:max(1,len(moves)//2)]) if random.random()<0.30 else random.choice(moves)
    depth=2 if level=="medium" else 3
    # Random small variation makes repeat games less predictable.
    best=-200000;found=[]
    nodes=[0]
    for move in moves:
        board.push(move)
        value=-_search(board,depth-1,-200000,200000,nodes)
        board.pop()
        if value>best:
            best=value;found=[move]
        elif value==best:found.append(move)
    return random.choice(found)
