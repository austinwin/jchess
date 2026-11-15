"""Structured, original chess lessons. Solutions remain in the parent-gated puzzle library."""
import chess

LESSONS = [
 {"id":"fork","category":"tactics","theme":"fork","title":"Fork two targets","level":"Beginner","emoji":"♞","time":"5 min","why":"One move attacks two pieces at once. Your opponent often cannot save both.","steps":["Find a knight jump with two valuable targets.","Check if the landing square is safe.","Jump, then look for the opponent's best reply."],"question":"Which single knight move attacks two targets?"},
 {"id":"pin","category":"tactics","theme":"pin","title":"Pin a defender","level":"Intermediate","emoji":"📌","time":"6 min","why":"A pinned piece cannot move without exposing something more valuable behind it.","steps":["Find two enemy pieces lined up.","Bring a bishop or rook onto their line.","Ask what happens if the front piece moves."],"question":"Where can your bishop or rook create a pin?"},
 {"id":"skewer","category":"tactics","theme":"skewer","title":"Skewer the king","level":"Intermediate","emoji":"⚡","time":"6 min","why":"Attack a valuable piece in front so it must move, exposing a piece behind.","steps":["Look for a king and queen in one line.","Find a rook or bishop that can attack the front target.","After the king moves, spot the exposed piece."],"question":"Can you attack the king and uncover another target?"},
 {"id":"discovered-attack","category":"tactics","theme":"discovered-attack","title":"Uncover a hidden attack","level":"Intermediate","emoji":"🌟","time":"6 min","why":"Move one piece away and uncover the power of another piece behind it.","steps":["Find a rook or bishop blocked by a friendly piece.","Move the blocking piece to a useful square.","Check which enemy piece is now attacked."],"question":"What happens when the blocking piece moves?"},
 {"id":"double-attack","category":"tactics","theme":"double-attack","title":"Queen double attack","level":"Intermediate","emoji":"👑","time":"6 min","why":"A check can come with a second threat. The opponent has to answer the check first.","steps":["Scan for checks your queen can give.","For each check, see whether a second target is attacked.","Compare the risks before choosing."],"question":"Find a checking queen move with a second target."},
 {"id":"remove-defender","category":"tactics","theme":"remove-defender","title":"Remove the guard","level":"Intermediate","emoji":"🎯","time":"6 min","why":"A valuable piece may look safe because another piece protects it. Capture the guard first.","steps":["Identify a well-defended target.","Locate the piece defending it.","See whether you can capture that defender safely."],"question":"Which defender is the key to the position?"},
 {"id":"back-rank","category":"tactics","theme":"back-rank","title":"Back-rank checkmate","level":"Intermediate","emoji":"🏰","time":"5 min","why":"A king boxed in by its own pawns may be trapped by a rook on the back rank.","steps":["Check the king's escape squares.","Look for an open file or rank for your rook.","Play a forcing check and verify every escape."],"question":"Can a rook reach the last rank with checkmate?"},
 {"id":"center","category":"strategy","theme":"center","title":"Fight for the center","level":"Beginner","emoji":"🎯","time":"5 min","why":"Central pawns and pieces influence more squares and create room for your army.","steps":["Look at the central squares d4, e4, d5 and e5.","Develop a move that claims or pressures them.","Check whether your move leaves a piece hanging."],"question":"Which move strengthens your central control?"},
 {"id":"development","category":"strategy","theme":"development","title":"Develop with a purpose","level":"Beginner","emoji":"🚀","time":"5 min","why":"Active knights and bishops join the game, create threats and prepare castling.","steps":["Count the pieces still on their starting squares.","Choose a useful active square for a minor piece.","Avoid moving the same piece repeatedly without a reason."],"question":"Which piece should join the game?"},
 {"id":"king-safety","category":"strategy","theme":"king-safety","title":"Castle before trouble","level":"Beginner","emoji":"🛡️","time":"5 min","why":"Castling usually protects the king and activates a rook.","steps":["Check that the path is clear and not under attack.","Castle while the center may soon open.","After castling, watch for attacks on the king's pawns."],"question":"Can you make your king safer now?"},
 {"id":"pawn-break","category":"strategy","theme":"pawn-break","title":"Open a path for your pieces","level":"Intermediate","emoji":"🌱","time":"7 min","why":"A timely pawn push can challenge an enemy center and open lines for your bishops and rooks.","steps":["Find a pawn that can challenge the center.","Imagine how the pawns may capture each other.","Check which pieces gain activity after the exchange."],"question":"Which pawn push challenges the center?"},
 {"id":"passed-pawn","category":"strategy","theme":"passed-pawn","title":"Make your passed pawn count","level":"Intermediate","emoji":"♙","time":"6 min","why":"A passed pawn has no enemy pawns ahead on its file or the neighboring files and may become a queen.","steps":["Identify the pawn with a clear path.","Check for enemy king or piece attacks.","Advance when safe and support it with your king."],"question":"Which pawn can safely advance toward promotion?"},
 {"id":"open-file","category":"strategy","theme":"open-file","title":"Bring a rook to an open file","level":"Intermediate","emoji":"♜","time":"6 min","why":"Rooks become more useful on files without pawns blocking them.","steps":["Find a file with no pawns.","Look for a safe square for your rook.","Move there to pressure the opponent's position."],"question":"Where can a rook claim an open file?"},
 {"id":"piece-activity","category":"strategy","theme":"piece-activity","title":"Improve your worst piece","level":"Intermediate","emoji":"♗","time":"6 min","why":"Before attacking, improve the piece doing the least work.","steps":["Look for a knight or bishop with few useful squares.","Find a strong square it can reach safely.","Improve it while keeping your king protected."],"question":"Which move makes your least active piece stronger?"}
]
LESSON_BY_ID={lesson["id"]:lesson for lesson in LESSONS}


def guided_positions(make, board):
    """Original model-move exercises. Every FEN and continuation is checked by make()."""
    out=[]
    sq=chess.parse_square
    def position(slug,title,category,theme,white_king,black_king,white,black,uci,explanation,rating=850):
        b=board(sq(white_king),sq(black_king),[(sq(s),p) for s,p in white],[(sq(s),p) for s,p in black])
        p=make("guided-"+slug,title,category,theme,b,[uci],explanation,rating=rating)
        if p:out.append(p)
    def opening(slug,title,theme,history,answer,explanation,rating=750):
        b=chess.Board()
        try:
            for san in history:b.push_san(san)
            m=b.parse_san(answer)
            p=make("guided-"+slug,title,"strategy",theme,b,[m.uci()],explanation,rating=rating)
            if p:out.append(p)
        except ValueError:pass
    B=chess.BISHOP;R=chess.ROOK;N=chess.KNIGHT;Q=chess.QUEEN;P=chess.PAWN
    position("pin-1","Pin the knight to the king","tactics","pin","a1","e8",[("c4",B)],[("c6",N)],"c4b5","The knight on c6 cannot leave the diagonal without exposing its king.")
    position("pin-2","Bring your bishop into the pin","tactics","pin","g1","e8",[("d3",B)],[("c6",N),("g7",P)],"d3b5","The bishop pins the knight on c6 against the king.")
    position("pin-3","Rook pin on the d-file","tactics","pin","a1","d8",[("a5",R)],[("d6",N)],"a5d5","The rook lines up the knight and king on the d-file.")
    position("skewer-1","Rook skewer through a pawn","tactics","skewer","a1","e5",[("a5",R)],[("c5",P),("f5",Q)],"a5c5","The rook captures with check. After the king moves, the queen behind it is exposed.",950)
    position("skewer-2","Reveal the queen behind the king","tactics","skewer","a1","e4",[("a4",R)],[("c4",P),("f4",Q)],"a4c4","A checking rook attacks the king first, then threatens the queen.",960)
    position("discover-1","Open the d-file","tactics","discovered-attack","h1","h8",[("d1",R),("d5",B)],[("d8",Q)],"d5e4","Moving the bishop exposes your rook's attack on the queen.",980)
    position("discover-2","Uncover your rook","tactics","discovered-attack","a1","h8",[("e1",R),("e4",B)],[("e8",Q)],"e4f3","The bishop moves away and the rook attacks the queen on e8.",980)
    position("double-1","Queen check and rook attack","tactics","double-attack","e1","e8",[("d1",Q)],[("h8",R)],"d1h5","Queen to h5 checks the king and eyes the rook on h8.",950)
    position("double-2","Find a second target","tactics","double-attack","g1","e8",[("d1",Q)],[("a8",R)],"d1a4","Queen to a4 checks the king and attacks the rook on a8.",980)
    position("guard-1","Capture the piece guarding a rook","tactics","remove-defender","a1","e8",[("c4",B)],[("f7",N),("h8",R)],"c4f7","The knight on f7 protected the rook on h8. Capturing it removes that defender.",940)
    position("guard-2","Take the guard","tactics","remove-defender","h1","h8",[("g2",B)],[("b7",N),("a5",R)],"g2b7","The knight on b7 protected the rook on a5. Capture the defender.",990)
    position("backrank-1","Find a back-rank mate","tactics","back-rank","f1","g8",[("e1",R)],[("f7",P),("g7",P),("h7",P)],"e1e8","The rook checks along the back rank; the king's own pawns block the exits.",850)
    position("backrank-2","Rook to the eighth rank","tactics","back-rank","a1","b8",[("h1",R)],[("a7",P),("b7",P),("c7",P)],"h1h8","The rook checks across the eighth rank and the king is boxed in.",880)
    strategy=[
      ("center-1","Claim e4","center",[],"e4","A central pawn controls d5 and f5."),
      ("center-2","Claim d4","center",[],"d4","A central pawn controls c5 and e5."),
      ("center-3","Challenge the center","center",["d4","d5"],"c4","The c-pawn challenges Black's d5 pawn."),
      ("center-4","Build the pawn center","center",["e4","e6"],"d4","Two central pawns claim room."),
      ("center-5","Strike in the middle","center",["e4","e5","Nf3","Nc6"],"d4","A central pawn break makes Black react."),
      ("dev-1","Bring out your knight","development",["e4","e5"],"Nf3","The knight develops while attacking e5."),
      ("dev-2","Help your queen's knight","development",["d4","d5"],"Nc3","The knight develops toward the center."),
      ("dev-3","Activate your bishop","development",["e4","e5","Nf3","Nc6"],"Bc4","The bishop joins the game and eyes f7."),
      ("dev-4","Develop the bishop beyond the pawn chain","development",["d4","d5","Nf3","Nf6"],"Bf4","The bishop gets active before e3 closes its diagonal."),
      ("king-1","Time to castle","king-safety",["e4","e5","Nf3","Nc6","Bc4","Bc5","d3","Nf6"],"O-O","Castling puts the king behind pawns and connects a rook to the game."),
      ("king-2","Castle the quiet position","king-safety",["d4","d5","Nf3","Nf6","e3","e6","Bd3","Bd6"],"O-O","Both knights and bishops have opened the route to castling."),
      ("king-3","Secure the king","king-safety",["e4","e5","Nf3","Nc6","Bc4","Nf6","d3","Bc5"],"O-O","Before attacking, make your king safer."),
      ("break-1","Open the central diagonal","pawn-break",["e4","e5","Nf3","Nc6","Bc4","Bc5","c3","Nf6"],"d4","The d-pawn challenges Black's center and opens lines for your pieces."),
      ("break-2","Strike at the d5 pawn","pawn-break",["d4","d5"],"c4","A central pawn break demands a response."),
      ("break-3","Build a strong central challenge","pawn-break",["e4","e5","Nf3","Nc6"],"d4","A pawn break changes the central structure."),
      ("activity-1","Bring a bishop into the game","piece-activity",["d4","d5","Nf3","Nf6"],"Bf4","Develop the bishop actively instead of leaving it on c1."),
      ("activity-2","A useful bishop square","piece-activity",["e4","e5","Nf3","Nc6"],"Bc4","Activity matters more than keeping every piece at home."),
      ("activity-3","Put the knight where it influences the center","piece-activity",["d4","Nf6"],"Nf3","A centralizing knight supports the position."),
    ]
    for slug,title,theme,history,move,why in strategy:
        opening(slug,title,theme,history,move,why,740)
    for i in range(8):
        file=chr(ord("a")+i)
        if file=="e":continue
        wk="e1" if i!=4 else "a1"
        bk="b8" if i>=4 else "h8"
        position("passed-"+str(i),"Push the passed "+file+"-pawn","strategy","passed-pawn",wk,bk,[(file+"6",P)],[("g4",P) if i<4 else ("a4",P)],file+"6"+file+"7","With no enemy pawn blocking its path, the passed pawn advances toward promotion.",790+i*18)
    position("file-1","Claim the open d-file","strategy","open-file","e1","h8",[("a1",R)],[("g7",P)],"a1d1","The d-file is open, so the rook belongs on d1.",820)
    position("file-2","Use the open e-file","strategy","open-file","g1","g8",[("a2",R)],[("h7",P)],"a2e2","The e-file has no pawns; the rook can pressure it.",850)
    position("outpost-1","Bring the knight toward a protected outpost","strategy","piece-activity","e1","h8",[("e3",N),("c4",P)],[("h7",P)],"e3d5","The c4 pawn supports a knight on d5.",890)
    return out
