"""
engine/bot.py  ~1700 ELO
Pin tactics, check detection, threat awareness, smart castling, trade evaluation.
Difficulty levels: Easy (Green - blunders often), Normal (Yellow - blunders sometimes), Hard (Red - no blunders)
"""
import time, sys, os, random
try:
    from piece import Pawn, Knight, Bishop, Rook, Queen, King
    from const import ROWS, COLS
except ModuleNotFoundError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from piece import Pawn, Knight, Bishop, Rook, Queen, King
    from const import ROWS, COLS

# ── Piece-square tables ─────────────────────────────────────────────────────

PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
KNIGHT_TABLE = [
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -30,  0, 15, 20, 20, 15,  0,-30,
   -30,  5, 15, 20, 20, 15,  5,-30,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50,
]
BISHOP_TABLE = [
   -20,-10,-10,-10,-10,-10,-10,-20,
   -10,  5,  0,  0,  0,  0,  5,-10,
   -10, 10, 10, 10, 10, 10, 10,-10,
   -10,  0, 10, 10, 10, 10,  0,-10,
   -10,  5,  5, 10, 10,  5,  5,-10,
   -10,  0,  5, 10, 10,  5,  0,-10,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -20,-10,-10,-10,-10,-10,-10,-20,
]
ROOK_TABLE = [
     0,  0,  0,  5,  5,  0,  0,  0,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     5, 10, 10, 10, 10, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
QUEEN_TABLE = [
   -20,-10,-10, -5, -5,-10,-10,-20,
   -10,  0,  5,  0,  0,  0,  0,-10,
   -10,  5,  5,  5,  5,  5,  0,-10,
     0,  0,  5,  5,  5,  5,  0, -5,
    -5,  0,  5,  5,  5,  5,  0, -5,
   -10,  0,  5,  5,  5,  5,  0,-10,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -20,-10,-10, -5, -5,-10,-10,-20,
]
KING_MID = [
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -20,-30,-30,-40,-40,-30,-30,-20,
   -10,-20,-20,-30,-30,-20,-20,-10,
    20, 20,  0,-10,-10,  0, 20, 20,
    20, 30, 10,-10,  0,-10, 30, 20,
]
KING_END = [
   -50,-40,-30,-20,-20,-30,-40,-50,
   -30,-20,-10,  0,  0,-10,-20,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-30,  0,  0,  0,  0,-30,-30,
   -50,-30,-30,-30,-30,-30,-30,-50,
]

PV = {Pawn:100, Knight:320, Bishop:330, Rook:500, Queen:900, King:20000}
TT_EXACT, TT_UPPER, TT_LOWER = 0, 1, 2

# ── Difficulty Colors ───────────────────────────────────────────────────────

DIFFICULTY_COLORS = {
    'easy': (76, 175, 80),     # Green
    'normal': (255, 193, 7),   # Amber/Yellow
    'hard': (244, 67, 54),      # Red
}

DIFFICULTY_NAMES = {
    'easy': 'Easy',
    'normal': 'Normal',
    'hard': 'Hard',
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _pst(r, c, color, tbl):
    return tbl[r*8+c] if color == 'white' else tbl[(7-r)*8+c]

def _pc(board):
    return sum(1 for r in range(8) for c in range(8)
               if board.squares[r][c].piece is not None)

def _endgame(board):
    q = wm = bm = tot = 0
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c].piece
            if not p: continue
            tot += 1
            if isinstance(p, Queen): q += 1
            elif isinstance(p, (Rook, Knight, Bishop)):
                if p.color=='white': wm+=1
                else: bm+=1
    return q==0 or tot<=14 or wm==0 or bm==0

def _hash(board):
    h = 0
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c].piece
            if p:
                h ^= hash((r,c,type(p).__name__,p.color,
                            getattr(p,'moved',False),
                            getattr(p,'en_passant',False)))
    return h

def _copy(board):
    new = object.__new__(board.__class__)
    new.squares = [[None]*8 for _ in range(8)]
    new.last_move = board.last_move
    pm = {}
    for r in range(8):
        for c in range(8):
            os_ = board.squares[r][c]
            ns  = object.__new__(os_.__class__)
            ns.row=os_.row; ns.col=os_.col; ns.alphacol=os_.alphacol
            if os_.piece is None:
                ns.piece = None
            else:
                op=os_.piece
                np_=object.__new__(op.__class__)
                np_.name=op.name; np_.color=op.color; np_.value=op.value
                np_.moved=op.moved; np_.texture=op.texture
                np_.texture_rect=op.texture_rect; np_.moves=[]
                if isinstance(op,Pawn):
                    np_.dir=op.dir; np_.en_passant=op.en_passant
                if isinstance(op,King):
                    np_.left_rook=None; np_.right_rook=None
                pm[id(op)]=np_; ns.piece=np_
            new.squares[r][c]=ns
    for r in range(8):
        for c in range(8):
            p=new.squares[r][c].piece
            if isinstance(p,King):
                ok=board.squares[r][c].piece
                if ok and ok.left_rook:  p.left_rook  = pm.get(id(ok.left_rook))
                if ok and ok.right_rook: p.right_rook = pm.get(id(ok.right_rook))
    return new

def _apply(board, piece, move):
    nb  = _copy(board)
    np_ = nb.squares[move.initial.row][move.initial.col].piece
    is2 = isinstance(np_,Pawn) and abs(move.final.row-move.initial.row)==2
    nb.move(np_, move, testing=True)
    if isinstance(np_,Pawn) and move.final.row in (0,7):
        nb.squares[move.final.row][move.final.col].piece = Queen(np_.color)
    for _r in range(8):
        for _c in range(8):
            _p=nb.squares[_r][_c].piece
            if isinstance(_p,Pawn): _p.en_passant=False
    if is2:
        mp=nb.squares[move.final.row][move.final.col].piece
        if mp: mp.en_passant=True
    return nb

def _moves(board, color):
    result = []
    for r in range(ROWS):
        for c in range(COLS):
            p=board.squares[r][c].piece
            if p and p.color==color:
                board.calc_moves(p,r,c,bool=True)
                for m in p.moves:
                    if board.squares[m.initial.row][m.initial.col].piece is p:
                        result.append((p,m,r,c))
    return result

def _clear(board):
    for r in range(ROWS):
        for c in range(COLS):
            p=board.squares[r][c].piece
            if p: p.clear_moves()

# ── Pin and threat detection ───────────────────────────────────────────────

def _is_pinned(board, row, col, color):
    """Check if piece at (row,col) is pinned to king."""
    king_r = king_c = None
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c].piece
            if isinstance(p, King) and p.color == color:
                king_r, king_c = r, c
                break
        if king_r is not None:
            break
    
    if king_r is None:
        return False, None
    
    enemy = 'black' if color == 'white' else 'white'
    
    dr = 0 if king_r == row else (1 if king_r > row else -1)
    dc = 0 if king_c == col else (1 if king_c > col else -1)
    
    if dr == 0 and dc == 0:
        return False, None
    
    is_aligned = False
    if dr == 0 and dc != 0:
        is_aligned = True
    elif dc == 0 and dr != 0:
        is_aligned = True
    elif abs(dr) == abs(dc) and dr != 0:
        is_aligned = True
    
    if not is_aligned:
        return False, None
    
    nr, nc = king_r - dr, king_c - dc
    while 0 <= nr < 8 and 0 <= nc < 8:
        p = board.squares[nr][nc].piece
        if p:
            if p.color == enemy:
                if (dr == 0 or dc == 0) and isinstance(p, (Rook, Queen)):
                    return True, (nr, nc)
                if abs(dr) == abs(dc) and isinstance(p, (Bishop, Queen)):
                    return True, (nr, nc)
            break
        nr -= dr
        nc -= dc
    
    return False, None

def _find_pins(board, color):
    """Find all pieces of given color that are pinned."""
    pins = []
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c].piece
            if p and p.color == color and not isinstance(p, King):
                pinned, attacker = _is_pinned(board, r, c, color)
                if pinned:
                    pins.append((p, r, c, attacker))
    return pins

def _find_our_pins(board, color):
    """Find enemy pieces we're pinning."""
    enemy = 'black' if color == 'white' else 'white'
    return _find_pins(board, enemy)

# ── Castle evaluation ──────────────────────────────────────────────────────

def _evaluate_castle_side(board, color):
    enemy = 'black' if color == 'white' else 'white'
    back_rank = 7 if color == 'white' else 0
    
    ks_score = 0
    qs_score = 0
    
    ks_squares = [(back_rank, 5), (back_rank, 6)]
    for r, c in ks_squares:
        if _attacked(board, r, c, enemy):
            ks_score -= 50
        pawn_r = back_rank + (-1 if color == 'white' else 1)
        for pc_ in [c-1, c, c+1]:
            if 0 <= pawn_r < 8 and 0 <= pc_ < 8:
                p = board.squares[pawn_r][pc_].piece
                if isinstance(p, Pawn) and p.color == color:
                    ks_score += 15
    
    qs_squares = [(back_rank, 3), (back_rank, 2), (back_rank, 1)]
    for r, c in qs_squares:
        if _attacked(board, r, c, enemy):
            qs_score -= 50
        pawn_r = back_rank + (-1 if color == 'white' else 1)
        for pc_ in [c-1, c, c+1]:
            if 0 <= pawn_r < 8 and 0 <= pc_ < 8:
                p = board.squares[pawn_r][pc_].piece
                if isinstance(p, Pawn) and p.color == color:
                    qs_score += 12
    
    if board.squares[back_rank][7].piece and isinstance(board.squares[back_rank][7].piece, Rook):
        if board.squares[back_rank][7].piece.color == color:
            ks_score += 20
    if board.squares[back_rank][0].piece and isinstance(board.squares[back_rank][0].piece, Rook):
        if board.squares[back_rank][0].piece.color == color:
            qs_score += 20
    
    return ks_score, qs_score

def _can_castle(board, color):
    """Find king dynamically — never assume starting square."""
    back_rank = 7 if color == 'white' else 0
    enemy     = 'black' if color == 'white' else 'white'

    # Find king on back rank
    kr = kc = None
    for c in range(8):
        p = board.squares[back_rank][c].piece
        if isinstance(p, King) and p.color == color and not p.moved:
            kr, kc = back_rank, c
            break
    if kr is None:
        return False, False

    ks_ok = False
    # Kingside rook must be on h-file (col 7)
    rook_ks = board.squares[back_rank][7].piece
    if isinstance(rook_ks, Rook) and not rook_ks.moved and rook_ks.color == color:
        squares_clear = all(board.squares[back_rank][c].piece is None
                            for c in range(kc+1, 7))
        not_through_check = all(not _attacked(board, back_rank, c, enemy)
                                for c in range(kc, kc+3))
        if squares_clear and not_through_check:
            ks_ok = True

    qs_ok = False
    # Queenside rook must be on a-file (col 0)
    rook_qs = board.squares[back_rank][0].piece
    if isinstance(rook_qs, Rook) and not rook_qs.moved and rook_qs.color == color:
        squares_clear = all(board.squares[back_rank][c].piece is None
                            for c in range(1, kc))
        not_through_check = all(not _attacked(board, back_rank, c, enemy)
                                for c in range(kc-2, kc+1))
        if squares_clear and not_through_check:
            qs_ok = True

    return ks_ok, qs_ok

def _legal_moves(board, color):
    """Return all legal moves. No pre-filtering — let search + ordering handle it."""
    return _moves(board, color)

# ── Fast attack geometry ───────────────────────────────────────────────────────

def _atk(board, row, col, color):
    res = []
    for dr,dc in [(-2,1),(-1,2),(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1)]:
        r,c=row+dr,col+dc
        if 0<=r<8 and 0<=c<8:
            p=board.squares[r][c].piece
            if isinstance(p,Knight) and p.color==color: res.append((p,r,c))
    for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        r,c=row+dr,col+dc
        while 0<=r<8 and 0<=c<8:
            p=board.squares[r][c].piece
            if p:
                if p.color==color and isinstance(p,(Bishop,Queen)): res.append((p,r,c))
                break
            r+=dr; c+=dc
    for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        r,c=row+dr,col+dc
        while 0<=r<8 and 0<=c<8:
            p=board.squares[r][c].piece
            if p:
                if p.color==color and isinstance(p,(Rook,Queen)): res.append((p,r,c))
                break
            r+=dr; c+=dc
    pr = row+1 if color=='white' else row-1
    for dc in [-1,1]:
        r,c=pr,col+dc
        if 0<=r<8 and 0<=c<8:
            p=board.squares[r][c].piece
            if isinstance(p,Pawn) and p.color==color: res.append((p,r,c))
    for dr,dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
        r,c=row+dr,col+dc
        if 0<=r<8 and 0<=c<8:
            p=board.squares[r][c].piece
            if isinstance(p,King) and p.color==color: res.append((p,r,c))
    return res

def _attacked(board, row, col, by):
    return bool(_atk(board,row,col,by))

def _in_check(board, color):
    enemy='black' if color=='white' else 'white'
    for r in range(8):
        for c in range(8):
            p=board.squares[r][c].piece
            if isinstance(p,King) and p.color==color:
                return _attacked(board,r,c,enemy)
    return False

def _gives_check(board, piece, move):
    """Check if this move delivers check (direct or discovered) to enemy king."""
    nb    = _apply(board, piece, move)
    enemy = 'black' if piece.color == 'white' else 'white'
    return _in_check(nb, enemy)

def _gives_discovered_check(board, piece, move):
    """
    True if moving this piece reveals an attack on the enemy king
    from a friendly slider behind it (discovered check).
    """
    color  = piece.color
    enemy  = 'black' if color == 'white' else 'white'
    fr, fc = move.initial.row, move.initial.col

    # Find enemy king
    king_r = king_c = None
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c].piece
            if isinstance(p, King) and p.color == enemy:
                king_r, king_c = r, c
                break
        if king_r is not None: break
    if king_r is None: return False

    # Direction from moving piece to enemy king
    dr = 0 if king_r == fr else (1 if king_r > fr else -1)
    dc = 0 if king_c == fc else (1 if king_c > fc else -1)

    # Must be aligned (diagonal or orthogonal)
    if dr == 0 and dc == 0: return False
    if not (dr == 0 or dc == 0 or abs(dr) == abs(dc)): return False

    # Walk FROM the moving piece AWAY from the king — find a friendly slider
    nr, nc = fr - dr, fc - dc
    while 0 <= nr < 8 and 0 <= nc < 8:
        p = board.squares[nr][nc].piece
        if p:
            if p.color == color:
                # Is it a slider that can attack along this ray?
                if dr == 0 or dc == 0:  # orthogonal
                    if isinstance(p, (Rook, Queen)): return True
                else:                    # diagonal
                    if isinstance(p, (Bishop, Queen)): return True
            break
        nr -= dr; nc -= dc

    return False

# ── SEE ────────────────────────────────────────────────────────────────────────

def _see(board, row, col, by_color):
    target=board.squares[row][col].piece
    if not target: return 0
    atts=_atk(board,row,col,by_color)
    if not atts: return 0
    best_p,br,bc = min(atts, key=lambda a:PV.get(type(a[0]),0))
    tv = PV.get(type(target),0)
    nb=_copy(board)
    np_=nb.squares[br][bc].piece
    nb.squares[row][col].piece=np_
    nb.squares[br][bc].piece=None
    if np_:
        np_.moved=True
        if isinstance(np_,Pawn) and row in (0,7):
            nb.squares[row][col].piece=Queen(np_.color)
    nc='black' if by_color=='white' else 'white'
    return max(0, tv - _see(nb, row, col, nc))

def _see_ok_promo(board, piece, move):
    """True if promoting this pawn doesn't immediately lose the queen."""
    nb   = _apply(board, piece, move)   # pawn becomes queen in _apply
    opp  = 'black' if piece.color=='white' else 'white'
    tr, tc = move.final.row, move.final.col
    # The new queen on the promotion square — is it immediately captured for free?
    loss = _see(nb, tr, tc, opp)
    return loss < 800   # tolerate losing up to a rook (queen still promoted)

def _see_ok(board, move, threshold=0):
    tr,tc=move.final.row,move.final.col
    tgt=board.squares[tr][tc].piece
    att=board.squares[move.initial.row][move.initial.col].piece
    if not tgt or not att: return False
    tv=PV.get(type(tgt),0)
    nb=_copy(board)
    np_=nb.squares[move.initial.row][move.initial.col].piece
    nb.squares[tr][tc].piece=np_
    nb.squares[move.initial.row][move.initial.col].piece=None
    if np_:
        np_.moved=True
        if isinstance(np_,Pawn) and tr in (0,7):
            nb.squares[tr][tc].piece=Queen(np_.color)
    opp='black' if att.color=='white' else 'white'
    return (tv - _see(nb,tr,tc,opp)) >= threshold

def _hanging(board, row, col):
    p=board.squares[row][col].piece
    if not p or isinstance(p,King): return False
    enemy='black' if p.color=='white' else 'white'
    atts=_atk(board,row,col,enemy)
    if not atts: return False
    return _see(board,row,col,enemy) > 0

def _see_sequence(board, row, col, color, depth=0, max_depth=3):
    """Evaluate a sequence of captures on a square."""
    if depth >= max_depth:
        return 0
    
    target = board.squares[row][col].piece
    if not target:
        return 0
    
    attackers = _atk(board, row, col, color)
    if not attackers:
        return 0
    
    best_attacker = min(attackers, key=lambda a: PV.get(type(a[0]), 0))
    att_piece, att_row, att_col = best_attacker
    
    gained = PV.get(type(target), 0)
    
    nb = _copy(board)
    np_ = nb.squares[att_row][att_col].piece
    nb.squares[row][col].piece = np_
    nb.squares[att_row][att_col].piece = None
    if np_:
        np_.moved = True
        if isinstance(np_, Pawn) and row in (0, 7):
            nb.squares[row][col].piece = Queen(np_.color)
    
    next_color = 'black' if color == 'white' else 'white'
    opponent_gain = _see_sequence(nb, row, col, next_color, depth+1, max_depth)
    
    net_gain = gained - opponent_gain
    return max(0, net_gain)

def _evaluate_trade(board, move, color):
    """Evaluate if a trade/capture sequence is favorable."""
    att = board.squares[move.initial.row][move.initial.col].piece
    tgt = board.squares[move.final.row][move.final.col].piece
    if not att or not tgt:
        return 0
    
    att_val = PV.get(type(att), 0)
    tgt_val = PV.get(type(tgt), 0)
    
    immediate_gain = tgt_val - att_val if att_val < tgt_val else 0
    see_gain = _see(board, move.final.row, move.final.col, color)
    
    trade_score = max(immediate_gain, see_gain)
    
    if see_gain > 0:
        trade_score += see_gain * 2
    elif see_gain == 0 and tgt_val >= att_val:
        trade_score += 50
    
    if att_val < tgt_val:
        trade_score += (tgt_val - att_val) * 3
    
    return trade_score

# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(board):
    score = 0
    eg    = _endgame(board)
    wb=bb = 0

    for r in range(8):
        for c in range(8):
            p=board.squares[r][c].piece
            if not p: continue
            pt=type(p)
            base=PV.get(pt,0)
            if pt==Pawn and eg: base=160

            if   pt==Pawn:   pst=_pst(r,c,p.color,PAWN_TABLE)
            elif pt==Knight: pst=_pst(r,c,p.color,KNIGHT_TABLE)
            elif pt==Bishop:
                pst=_pst(r,c,p.color,BISHOP_TABLE)
                if p.color=='white': wb+=1
                else: bb+=1
            elif pt==Rook:   pst=_pst(r,c,p.color,ROOK_TABLE)
            elif pt==Queen:  pst=_pst(r,c,p.color,QUEEN_TABLE)
            elif pt==King:   pst=_pst(r,c,p.color,KING_END if eg else KING_MID)
            else: pst=0
            score += (base+pst) if p.color=='white' else -(base+pst)

    if wb>=2: score+=40
    if bb>=2: score-=40

    total_material = 0
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c].piece
            if p:
                val = PV.get(type(p), 0)
                if p.color == 'white':
                    total_material += val
                else:
                    total_material -= val

    if abs(total_material) > 300:
        advantage_side = 1 if total_material > 0 else -1
        piece_count = _pc(board)
        simplification_bonus = (32 - piece_count) * 15
        score += advantage_side * simplification_bonus

    for r in range(8):
        for c in range(8):
            p=board.squares[r][c].piece
            if not p or isinstance(p,King): continue
            enemy='black' if p.color=='white' else 'white'
            loss=_see(board,r,c,enemy)
            if loss>0:
                if p.color=='white': score-=loss
                else: score+=loss

    for color, sign in [('white', 1), ('black', -1)]:
        pins = _find_our_pins(board, color)
        for pinned_piece, r, c, attacker in pins:
            bonus = PV.get(type(pinned_piece), 0) // 4
            score += sign * bonus

    if not eg:
        for color,sign in [('white',1),('black',-1)]:
            enemy='black' if color=='white' else 'white'
            kp=None
            for r in range(8):
                for c in range(8):
                    p=board.squares[r][c].piece
                    if isinstance(p,King) and p.color==color:
                        kp=(r,c); break
                if kp: break
            if not kp: continue
            kr,kc=kp
            kp_=board.squares[kr][kc].piece
            saf=0
            pc = _pc(board)
            expected_rank = 7 if color=='white' else 0
            
            if kr != expected_rank and pc > 20:
                saf -= 250
            
            if kc in (3,4) and pc > 20:
                saf -= 150
            
            attackers = 0
            for r in range(max(0, kr-2), min(8, kr+3)):
                for c in range(max(0, kc-2), min(8, kc+3)):
                    p = board.squares[r][c].piece
                    if p and p.color == enemy:
                        attackers += 1
            
            if attackers >= 3: saf -= 150
            elif attackers >= 2: saf -= 80
            
            enemy_moves = _moves(board, enemy)
            check_threats = 0
            for ep, em, er, ec in enemy_moves:
                if _gives_check(board, ep, em):
                    check_threats += 1
            if check_threats >= 2:
                saf -= 80
            elif check_threats >= 1:
                saf -= 40
            
            ks_ok, qs_ok = _can_castle(board, color)
            
            if kp_.moved:
                if (color=='white' and kr==7 and kc in (6,2)) or \
                   (color=='black' and kr==0 and kc in (6,2)):
                    saf += 100
                elif (color=='white' and kr==7 and kc==4) or \
                     (color=='black' and kr==0 and kc==4):
                    if ks_ok or qs_ok:
                        saf -= 150
                    else:
                        saf -= 60
                else:
                    saf -= 50
            else:
                if ks_ok or qs_ok:
                    saf -= 180 if pc > 24 else 80
            
            pd=-1 if color=='white' else 1
            for dc in [-1,0,1]:
                pr,pc=kr+pd,kc+dc
                if 0<=pr<8 and 0<=pc<8:
                    p=board.squares[pr][pc].piece
                    if isinstance(p,Pawn) and p.color==color: saf+=15
                pr2,pc2=kr+pd*2,kc+dc
                if 0<=pr2<8 and 0<=pc2<8:
                    p=board.squares[pr2][pc2].piece
                    if isinstance(p,Pawn) and p.color==color: saf+=5
            
            for dc in [-1,0,1]:
                fc=kc+dc
                if not 0<=fc<8: continue
                own_p=any(isinstance(board.squares[rr][fc].piece,Pawn) and
                          board.squares[rr][fc].piece.color==color for rr in range(8))
                ebat=any(isinstance(board.squares[rr][fc].piece,(Rook,Queen)) and
                         board.squares[rr][fc].piece.color==enemy for rr in range(8))
                if not own_p: saf-=25
                if ebat and not own_p: saf-=40
            
            for r in range(8):
                for c in range(8):
                    p=board.squares[r][c].piece
                    if p and p.color==enemy:
                        dist=max(abs(r-kr),abs(c-kc))
                        if dist<=2: saf-=PV.get(type(p),0)//25
            
            score+=sign*saf

    for c in range(8):
        wp=bp=False
        for r in range(8):
            p=board.squares[r][c].piece
            if isinstance(p,Pawn):
                if p.color=='white': wp=True
                else: bp=True
        for r in range(8):
            p=board.squares[r][c].piece
            if isinstance(p,Rook):
                bonus=30 if not wp and not bp else (15 if (p.color=='white' and not wp) or (p.color=='black' and not bp) else 0)
                score+=bonus if p.color=='white' else -bonus

    for c in range(8):
        p=board.squares[1][c].piece
        if isinstance(p,Rook) and p.color=='white': score+=30
        p=board.squares[6][c].piece
        if isinstance(p,Rook) and p.color=='black': score-=30

    for c in range(8):
        wp=bp=0
        for r in range(8):
            p=board.squares[r][c].piece
            if isinstance(p,Pawn):
                if p.color=='white': wp+=1
                else: bp+=1
        if wp>1: score-=(wp-1)*25
        if bp>1: score+=(bp-1)*25

    # Track kings for endgame escort bonus
    wk_pos = bk_pos = None
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c].piece
            if isinstance(p, King):
                if p.color == 'white': wk_pos = (r, c)
                else: bk_pos = (r, c)

    for r in range(8):
        for c in range(8):
            p=board.squares[r][c].piece
            if not isinstance(p,Pawn): continue
            passed=True
            if p.color=='white':
                for rr in range(r-1,-1,-1):
                    for cc in [c-1,c,c+1]:
                        if 0<=cc<8:
                            q=board.squares[rr][cc].piece
                            if isinstance(q,Pawn) and q.color=='black':
                                passed=False
                                break
                    if not passed:
                        break
                if passed:
                    adv = 6-r   # 0 at start rank, 6 at promotion rank
                    if not eg:
                        score += 20 + adv*18
                    else:
                        # Exponential bonus — pawn on 7th rank (adv=6) = 30+360=390cp
                        score += 30 + adv*adv*10
                        # Promotion imminent: extra bonus on 7th rank
                        if r == 1:
                            score += 400   # about to promote — massive incentive
                        elif r == 2:
                            score += 200
                        # King escorts passer
                        if wk_pos:
                            kd = abs(wk_pos[0]-r) + abs(wk_pos[1]-c)
                            score -= kd * 4   # king close to passer = bonus
                        # Enemy king far from passer = bonus
                        if bk_pos:
                            ekd = abs(bk_pos[0]-r) + abs(bk_pos[1]-c)
                            score += ekd * 3
            else:
                for rr in range(r+1,8):
                    for cc in [c-1,c,c+1]:
                        if 0<=cc<8:
                            q=board.squares[rr][cc].piece
                            if isinstance(q,Pawn) and q.color=='white':
                                passed=False
                                break
                    if not passed:
                        break
                if passed:
                    adv = r-1
                    if not eg:
                        score -= 20 + adv*18
                    else:
                        score -= 30 + adv*adv*10
                        if r == 6:
                            score -= 400
                        elif r == 5:
                            score -= 200
                        if bk_pos:
                            kd = abs(bk_pos[0]-r) + abs(bk_pos[1]-c)
                            score += kd * 4
                        if wk_pos:
                            ekd = abs(wk_pos[0]-r) + abs(wk_pos[1]-c)
                            score -= ekd * 3

    KM=[(-2,1),(-1,2),(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1)]
    BD=[(-1,-1),(-1,1),(1,-1),(1,1)]
    for r in range(8):
        for c in range(8):
            p=board.squares[r][c].piece
            if not p: continue
            sign=1 if p.color=='white' else -1
            enemy='black' if p.color=='white' else 'white'
            if isinstance(p,Knight):
                mob=sum(1 for dr,dc in KM if 0<=r+dr<8 and 0<=c+dc<8 and
                        (not board.squares[r+dr][c+dc].piece or
                         board.squares[r+dr][c+dc].piece.color==enemy))
                score+=sign*(mob-4)*5
            elif isinstance(p,Bishop):
                mob=0
                for dr,dc in BD:
                    nr,nc=r+dr,c+dc
                    while 0<=nr<8 and 0<=nc<8:
                        t=board.squares[nr][nc].piece
                        if not t: mob+=1
                        elif t.color==enemy: mob+=1; break
                        else: break
                        nr+=dr; nc+=dc
                score+=sign*(mob-5)*4

    # ── Endgame knowledge ─────────────────────────────────────────────────
    if eg and wk_pos and bk_pos:
        wmat = sum(PV.get(type(board.squares[r][c].piece),0)
                   for r in range(8) for c in range(8)
                   if board.squares[r][c].piece
                   and board.squares[r][c].piece.color=='white'
                   and not isinstance(board.squares[r][c].piece,(King,Pawn)))
        bmat = sum(PV.get(type(board.squares[r][c].piece),0)
                   for r in range(8) for c in range(8)
                   if board.squares[r][c].piece
                   and board.squares[r][c].piece.color=='black'
                   and not isinstance(board.squares[r][c].piece,(King,Pawn)))

        def corner(pos):
            r,c=pos; return max(3-r,r-4)+max(3-c,c-4)
        def kd(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
        def cd(pos): r,c=pos; return abs(r-3.5)+abs(c-3.5)

        # King centralization (both sides should centralize in endgame)
        score -= int(cd(wk_pos)*10)
        score += int(cd(bk_pos)*10)

        if wmat > bmat + 150:
            # White winning: drive black king to corner, approach with white king
            score += corner(bk_pos)*30 - kd(wk_pos,bk_pos)*10
        elif bmat > wmat + 150:
            # Black winning: drive white king to corner
            score -= corner(wk_pos)*30 - kd(bk_pos,wk_pos)*10

        # King opposition bonus (key endgame concept)
        if kd(wk_pos,bk_pos)==2 and (wk_pos[0]==bk_pos[0] or wk_pos[1]==bk_pos[1]):
            score += 20

        # Rook endgame: rook on 7th rank is extremely powerful
        for c2 in range(8):
            p = board.squares[1][c2].piece
            if isinstance(p, Rook) and p.color=='white': score += 40
            p = board.squares[6][c2].piece
            if isinstance(p, Rook) and p.color=='black': score -= 40

        # When way ahead: swap pieces (not pawns) to simplify
        # Bonus for each piece traded when winning
        total_pieces = sum(1 for r in range(8) for c in range(8)
                          if board.squares[r][c].piece
                          and not isinstance(board.squares[r][c].piece,(King,Pawn)))
        if wmat > bmat + 400:
            # White far ahead: prefer fewer pieces on board
            score += (16 - total_pieces) * 8
        elif bmat > wmat + 400:
            # Black far ahead: prefer fewer pieces
            score -= (16 - total_pieces) * 8

    return score

# ── Move ordering ──────────────────────────────────────────────────────────────

def _mvv(move, board):
    v=board.squares[move.final.row][move.final.col].piece
    a=board.squares[move.initial.row][move.initial.col].piece
    if not v or not a: return 0
    return PV.get(type(v),0)*10 - PV.get(type(a),0)

def _mscore(move, board, k1=None, k2=None, ttm=None, bot=None):
    if ttm and move==ttm: return 20000
    att=board.squares[move.initial.row][move.initial.col].piece
    vic=board.squares[move.final.row][move.final.col].piece

    if bot:
        tactical_mult = bot._tactical_bonus
        castle_mult = bot._castle_priority
        dev_mult = bot._development_bonus
        ks_mult = bot._king_safety_weight
        see_thresh = bot._see_threshold
        block_king = bot._block_king_moves
        use_pins = bot._use_pins
        use_checks = bot._use_checks
        trade_mult = getattr(bot, '_trade_awareness', 1.0)
    else:
        tactical_mult = 1.0
        castle_mult = 1.0
        dev_mult = 1.0
        ks_mult = 1.0
        see_thresh = -200
        block_king = True
        use_pins = True
        use_checks = True
        trade_mult = 1.0

    # PAWN PROMOTION — highest priority of all (beats even captures)
    if isinstance(att, Pawn) and move.final.row in (0, 7):
        return 50000   # always promote immediately

    # CAPTURES — always use real SEE, never filtered by difficulty
    if vic:
        mv  = _mvv(move, board)
        # Bonus for capturing hanging piece
        if _hanging(board, move.final.row, move.final.col):
            mv += 1000
        if isinstance(att, Pawn):
            mv += 800
        # Winning capture: high priority
        if _see_ok(board, move, -50):
            return 30000 + mv
        # Losing capture: still searchable but low priority
        return 2000 + mv

    if (k1 and move==k1) or (k2 and move==k2): return 9000

    if not att: return 0
    
    pc = _pc(board)
    enemy='black' if att.color=='white' else 'white'
    
    if use_checks:
        is_check     = _gives_check(board, att, move)
        is_disc      = _gives_discovered_check(board, att, move)
        if is_check or is_disc:
            nb2    = _apply(board, att, move)
            enemy2 = 'black' if att.color == 'white' else 'white'
            # Count checkers for bonus (double check = very powerful)
            king_r2 = king_c2 = None
            for r2 in range(8):
                for c2 in range(8):
                    pp = nb2.squares[r2][c2].piece
                    if isinstance(pp, King) and pp.color == enemy2:
                        king_r2, king_c2 = r2, c2; break
                if king_r2 is not None: break
            n_checkers = len(_atk(nb2, king_r2, king_c2, att.color)) if king_r2 is not None else 1
            base_score = 5000 if is_disc else 4000
            base_score += n_checkers * 800   # double check massively boosted
            return int(base_score * tactical_mult)
    
    if isinstance(att, King):
        diff = move.final.col - move.initial.col
        if abs(diff) == 2:
            # This IS a castling move generated by board.calc_moves
            # Always score it highly — board already validated legality
            pc_now  = _pc(board)
            enemy_c = 'black' if att.color=='white' else 'white'
            urgency = 0
            if pc_now > 24:   urgency += 3000
            elif pc_now > 16: urgency += 1500
            else:             urgency += 800
            if _attacked(board, move.initial.row, move.initial.col, enemy_c):
                urgency += 4000
            ks_score, qs_score = _evaluate_castle_side(board, att.color)
            side_score = ks_score if diff > 0 else qs_score
            base_castle = 10000 + urgency
            return int(base_castle * max(castle_mult, 0.6)) + side_score
        # Non-castling king move
        if block_king:
            return -100000
    
    if isinstance(att, Queen) and pc > 28 and not att.moved:
        return int(-5000 * ks_mult)
    
    if use_pins:
        our_pins = _find_our_pins(board, att.color)
        for pinned_piece, pr, pc_, attacker_pos in our_pins:
            if (move.initial.row, move.initial.col) == attacker_pos:
                nb = _apply(board, att, move)
                still_pinning = False
                for r in range(8):
                    for c in range(8):
                        p2 = nb.squares[r][c].piece
                        if p2 and p2 == pinned_piece:
                            pinned2, _ = _is_pinned(nb, r, c, enemy)
                            if pinned2:
                                still_pinning = True
                if not still_pinning:
                    return int(-2000 * tactical_mult)
    
    if isinstance(att, Bishop):
        if not _attacked(board, move.initial.row, move.initial.col, enemy):
            if att.color == 'white' and move.final.row > move.initial.row:
                return int(-1000 * dev_mult)
            if att.color == 'black' and move.final.row < move.initial.row:
                return int(-1000 * dev_mult)
    
    pt = type(att)
    if pt in (Knight, Bishop) and pc > 24:
        if not att.moved:
            target_row = 4 if att.color == 'white' else 3
            if move.final.row in (target_row-1, target_row, target_row+1):
                if move.final.col in (2,3,4,5):
                    return int(2000 * dev_mult)

    if _hanging(board,move.initial.row,move.initial.col):
        pv=PV.get(type(att),0)
        safe=not _attacked(board,move.final.row,move.final.col,enemy)
        return (int(8500+pv//10) if safe else int(6500+pv//10))

    tbl={Pawn:PAWN_TABLE,Knight:KNIGHT_TABLE,Bishop:BISHOP_TABLE,
         Rook:ROOK_TABLE,Queen:QUEEN_TABLE,King:KING_MID}.get(pt)
    base=0
    if tbl:
        base=(_pst(move.final.row,move.final.col,att.color,tbl)-
              _pst(move.initial.row,move.initial.col,att.color,tbl))
    
    if _attacked(board,move.final.row,move.final.col,enemy):
        base-=PV.get(pt,0)//6
    
    if pt == Pawn and pc > 28:
        if move.final.col in (3,4) and not att.moved:
            base += int(30 * dev_mult)
    
    return base

# ── Quiescence search ─────────────────────────────────────────────────────

def _qsearch(board, alpha, beta, color, depth=0, max_depth=4, bot=None):
    raw=evaluate(board)
    sp=raw if color=='white' else -raw
    if sp>=beta: return beta
    if depth>=max_depth: return sp
    if sp>alpha: alpha=sp

    moves = _moves(board, color)
    caps_and_checks = []
    
    use_checks = bot._use_checks if bot else True
    
    for (p,m,r,c) in moves:
        if board.squares[m.final.row][m.final.col].piece:
            caps_and_checks.append((p,m,r,c))
        elif use_checks and _gives_check(board, p, m):
            caps_and_checks.append((p,m,r,c))
    
    caps_and_checks.sort(key=lambda x:_mvv(x[1],board) if board.squares[x[1].final.row][x[1].final.col].piece else 500, reverse=True)

    nc='black' if color=='white' else 'white'
    
    if bot and bot.difficulty == 'hard' and depth < 3:
        for (piece, move, r, c) in caps_and_checks:
            v = board.squares[move.final.row][move.final.col].piece
            if not v:
                continue
            if sp + PV.get(type(v), 0) + 500 < alpha and depth > 0:
                continue
            score = -_qsearch(_apply(board, piece, move), -beta, -alpha, nc, depth+1, max_depth, bot)
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha
    
    for (piece,move,r,c) in caps_and_checks:
        v=board.squares[move.final.row][move.final.col].piece
        if v:
            if sp+PV.get(type(v),0)+300<alpha: continue
            see_thresh = bot._see_threshold if bot else -200
            if not _see_ok(board,move,see_thresh): continue
        score=-_qsearch(_apply(board,piece,move),-beta,-alpha,nc,depth+1,max_depth,bot)
        if score>=beta: return beta
        if score>alpha: alpha=score
    return alpha

# ── SAN generator ─────────────────────────────────────────────────────────────

def _san(board, piece, move):
    F = 'abcdefgh'
    L = {Knight:'N', Bishop:'B', Rook:'R', Queen:'Q', King:'K'}
    pt = type(piece)
    fr, fc = move.initial.row, move.initial.col
    tr, tc = move.final.row, move.final.col
    dest = F[tc] + str(8-tr)
    
    if pt == King and abs(fc-tc) == 2:
        s = 'O-O' if tc > fc else 'O-O-O'
        nb = _apply(board, piece, move)
        enemy = 'black' if piece.color == 'white' else 'white'
        if _in_check(nb, enemy):
            if not _moves(nb, enemy): s += '#'
            else: s += '+'
        return s
    
    is_capture = board.squares[tr][tc].piece is not None
    if isinstance(piece, Pawn) and fc != tc and not is_capture:
        is_capture = True
    
    if pt == Pawn:
        if is_capture: s = F[fc] + 'x' + dest
        else: s = dest
        if tr in (0, 7): s += '=Q'
        nb = _apply(board, piece, move)
        enemy = 'black' if piece.color == 'white' else 'white'
        if _in_check(nb, enemy):
            if not _moves(nb, enemy): s += '#'
            else: s += '+'
        return s
    
    letter = L.get(pt, '')
    same_file = False
    same_rank = False
    for r in range(8):
        for c in range(8):
            if (r, c) == (fr, fc): continue
            other = board.squares[r][c].piece
            if other and type(other) == pt and other.color == piece.color:
                board.calc_moves(other, r, c, bool=True)
                for m in other.moves:
                    if m.final.row == tr and m.final.col == tc:
                        if c == fc: same_rank = True
                        else: same_file = True
    
    dis = ''
    if same_file and same_rank: dis = F[fc] + str(8-fr)
    elif same_file: dis = str(8-fr)
    elif same_rank: dis = F[fc]
    
    s = letter + dis + ('x' if is_capture else '') + dest
    
    nb = _apply(board, piece, move)
    enemy = 'black' if piece.color == 'white' else 'white'
    if _in_check(nb, enemy):
        if not _moves(nb, enemy): s += '#'
        else: s += '+'
    
    return s

def _move_to_san(board, piece, move):
    return _san(board, piece, move)

# ── Opening book ───────────────────────────────────────────────────────────────

try:
    from .opening_book import get_book
except ImportError:
    try:
        from opening_book import get_book
    except ImportError:
        def get_book():
            class _Dummy:
                def get_move(self, *a): return None
            return _Dummy()

# ── Bot ────────────────────────────────────────────────────────────────────────

class Bot:
    def __init__(self, color, max_depth=5, time_limit=1.5, difficulty='normal'):
        self.color        = color
        self.max_depth    = max_depth
        self.time_limit   = time_limit
        self.difficulty   = difficulty
        self.killers      = [[None,None] for _ in range(64)]
        self.history      = {}
        self.tt           = {}
        self.nodes        = 0
        self.start_time   = 0.0
        self.timeout      = False
        self._tl          = time_limit
        self.move_history = []
        self.book         = get_book()
        
        self._configure_difficulty()

    def _configure_difficulty(self):
        """Set parameters based on difficulty level."""
        if self.difficulty == 'easy':
            self._max_depth_override  = 1
            self._qs_depth            = 0
            self._time_factor         = 0.15
            self._king_safety_weight  = 0.1
            self._tactical_bonus      = 0.1
            self._random_factor       = 0.40
            self._use_pins            = False
            self._use_checks          = False
            self._block_king_moves    = False
            self._castle_priority     = 0.4   # min 0.6 enforced in _mscore
            self._development_bonus   = 0.05
            self._see_threshold       = 9999
            self._trade_awareness     = 0.05
            self._null_move           = False
            self._blunder_rate        = 0.50
            self._hang_piece_chance   = 0.25
            self._ignore_mate_chance  = 0.60
            self._bad_king_move_chance = 0.30

        elif self.difficulty == 'normal':
            self._max_depth_override  = 3
            self._qs_depth            = 3
            self._time_factor         = 0.45
            self._king_safety_weight  = 0.6
            self._tactical_bonus      = 0.6
            self._random_factor       = 0.0   # no random for normal
            self._use_pins            = True
            self._use_checks          = True
            self._block_king_moves    = True
            self._castle_priority     = 0.9
            self._development_bonus   = 0.6
            self._see_threshold       = 0
            self._trade_awareness     = 0.6
            self._null_move           = True
            self._blunder_rate        = 0.22  # post-search blunder only
            self._hang_piece_chance   = 0.0   # never hang on purpose
            self._ignore_mate_chance  = 0.10
            self._bad_king_move_chance = 0.0  # never bad king on purpose
            
        else:  # 'hard'
            self._max_depth_override = 5
            self._qs_depth = 8
            self._time_factor = 1.0
            self._king_safety_weight = 1.0
            self._tactical_bonus = 1.0
            self._random_factor = 0.0
            self._use_pins = True
            self._use_checks = True
            self._block_king_moves = True
            self._castle_priority = 1.0
            self._development_bonus = 1.0
            self._see_threshold = -200
            self._trade_awareness = 1.0
            self._null_move = True
            self._blunder_rate = 0.0
            self._hang_piece_chance = 0.0
            self._ignore_mate_chance = 0.0
            self._bad_king_move_chance = 0.0

    def get_difficulty_color(self):
        """Return RGB color for difficulty level."""
        return DIFFICULTY_COLORS.get(self.difficulty, (255, 255, 255))

    def get_difficulty_name(self):
        """Return display name for difficulty level."""
        return DIFFICULTY_NAMES.get(self.difficulty, 'Normal')

    def set_difficulty(self, difficulty):
        """Change difficulty level."""
        if difficulty in ['easy', 'normal', 'hard']:
            self.difficulty = difficulty
            self._configure_difficulty()

    def record_move(self, s): self.move_history.append(s)

    def play(self, board):
        self.nodes      = 0
        self.start_time = time.time()
        self.timeout    = False
        self.killers    = [[None,None] for _ in range(64)]

        pc=_pc(board); mn=len(self.move_history); eg=_endgame(board)

        if mn<10:      self._tl=0.3  * self._time_factor
        elif pc>24:    self._tl=0.5  * self._time_factor
        elif pc>18:    self._tl=0.8  * self._time_factor
        elif pc>10:    self._tl=1.1  * self._time_factor
        else:          self._tl=1.8  * self._time_factor

        if self.difficulty == 'easy':
            max_d = 1
        elif self.difficulty == 'normal':
            max_d = 3 if not eg else 4
        else:
            max_d = 4 if not eg else 6

        opp  = 'black' if self.color=='white' else 'white'
        anow = _legal_moves(board, self.color)

        # ── Mate in 1 ──────────────────────────────────────────────────────
        mate_thr = 0.0 if self.difficulty=='hard' else                    0.10 if self.difficulty=='normal' else 0.60
        if random.random() > mate_thr:
            for (piece,move,r,c) in anow:
                nb=_apply(board,piece,move)
                if not _moves(nb,opp) and _in_check(nb,opp):
                    live=board.squares[move.initial.row][move.initial.col].piece
                    _clear(board); print("[Mate in 1]")
                    return {'piece':live,'move':move}

        # ── Castling: prioritize castling in opening/middlegame (hard/normal) ──
        if self.difficulty != 'easy' and mn < 20 and pc > 16:
            for (piece, move, r, c) in anow:
                if isinstance(piece, King) and abs(move.initial.col - move.final.col) == 2:
                    # Verify king not currently in check
                    if not _in_check(board, self.color):
                        live = board.squares[move.initial.row][move.initial.col].piece
                        _clear(board)
                        print("[Castle priority]")
                        return {'piece': live, 'move': move}

        # ── Pawn promotion: always promote when possible (all difficulties) ──
        for (piece, move, r, c) in anow:
            if isinstance(piece, Pawn) and move.final.row in (0, 7):
                # Confirm it's not immediately losing (SEE check)
                if _see_ok_promo(board, piece, move):
                    live = board.squares[move.initial.row][move.initial.col].piece
                    _clear(board)
                    print("[Promote to Queen]")
                    return {'piece': live, 'move': move}

        # ── Mate in 2 (hard only) — catches Bxa6+ Qxc7# type sequences ────
        if self.difficulty == 'hard':
            for (piece, move, r, c) in anow:
                nb = _apply(board, piece, move)
                # After our move, does opponent have any reply that escapes mate?
                if _in_check(nb, opp):
                    opp_replies = _moves(nb, opp)
                    all_mated   = True
                    for (op2, om2, r2, c2) in opp_replies:
                        nb2 = _apply(nb, op2, om2)
                        our_replies = _moves(nb2, self.color)
                        found_mate  = False
                        for (p3, m3, r3, c3) in our_replies:
                            nb3 = _apply(nb2, p3, m3)
                            if not _moves(nb3, opp) and _in_check(nb3, opp):
                                found_mate = True; break
                        if not found_mate:
                            all_mated = False; break
                    if all_mated and opp_replies:
                        live = board.squares[move.initial.row][move.initial.col].piece
                        _clear(board); print("[Mate in 2]")
                        return {'piece': live, 'move': move}

        # ── EASY only: deliberate blunders before search ───────────────────
        if self.difficulty == 'easy' and len(anow) > 1:

            # 1. Random move from bottom half
            if random.random() < self._random_factor:
                k = self.killers[0]
                scored = sorted(anow,
                    key=lambda x: _mscore(x[1], board,
                                          k[0] if k else None,
                                          k[1] if k else None,
                                          None, self))
                cutoff = max(1, len(scored) // 2)
                piece, move, r, c = random.choice(scored[:cutoff])
                _clear(board)
                print("[Random easy]")
                return {'piece': piece, 'move': move}

            # 2. Hang a piece (move valuable piece to attacked square)
            if random.random() < self._hang_piece_chance:
                hang_moves = [
                    (p,m,r,c) for p,m,r,c in anow
                    if PV.get(type(p),0) >= 330
                    and _attacked(board, m.final.row, m.final.col, opp)
                ]
                if hang_moves:
                    piece, move, r, c = random.choice(hang_moves)
                    _clear(board)
                    print("[Hang easy]")
                    return {'piece': piece, 'move': move}

            # 3. Ignore saving a hanging piece
            if random.random() < self._blunder_rate:
                hanging_pos = {
                    (r2,c2) for r2 in range(8) for c2 in range(8)
                    if _hanging(board,r2,c2)
                    and board.squares[r2][c2].piece
                    and board.squares[r2][c2].piece.color==self.color
                }
                if hanging_pos:
                    non_rescue = [
                        (p,m,r,c) for p,m,r,c in anow
                        if (r,c) not in hanging_pos
                        and not any(m.final.row==hr and m.final.col==hc
                                    for hr,hc in hanging_pos)
                    ]
                    if non_rescue:
                        piece, move, r, c = random.choice(non_rescue)
                        _clear(board)
                        print("[Ignored hanging easy]")
                        return {'piece': piece, 'move': move}

            # 4. Bad king move
            if random.random() < self._bad_king_move_chance:
                km = [(p,m,r,c) for p,m,r,c in anow
                      if isinstance(p,King) and abs(m.initial.col-m.final.col)!=2]
                if km:
                    piece, move, r, c = random.choice(km)
                    _clear(board)
                    print("[Bad king easy]")
                    return {'piece': piece, 'move': move}

            # 5. Miss a free capture
            if random.random() < self._blunder_rate * 0.8:
                free_caps = [(p,m,r,c) for p,m,r,c in anow
                             if board.squares[m.final.row][m.final.col].piece
                             and _hanging(board,m.final.row,m.final.col)]
                if free_caps:
                    non_caps = [(p,m,r,c) for p,m,r,c in anow
                                if not board.squares[m.final.row][m.final.col].piece]
                    if non_caps:
                        piece, move, r, c = random.choice(non_caps)
                        _clear(board)
                        print("[Missed cap easy]")
                        return {'piece': piece, 'move': move}

        # Defend against opponent mate - only hard/normal
        if self.difficulty != 'easy':
            opp_mate=False
            for (op,om,r,c) in _moves(board,opp):
                nb=_apply(board,op,om)
                if not _moves(nb,self.color) and _in_check(nb,self.color):
                    opp_mate=True; break
        else:
            opp_mate = False

        # ── Clearly winning capture: play instantly (all difficulties except easy) ──
        # This guarantees the bot never misses a free piece even if search times out.
        if self.difficulty != 'easy':
            best_gain = 200   # threshold: at least a pawn+
            best_cap  = None
            for (piece, move, r, c) in anow:
                vic = board.squares[move.final.row][move.final.col].piece
                if vic is None: continue
                vv  = PV.get(type(vic), 0)
                av  = PV.get(type(piece), 0)
                if vv < av - 100: continue   # quick reject: attacker worth more
                # Compute net gain using SEE
                nb2       = _apply(board, piece, move)
                opp2      = 'black' if piece.color=='white' else 'white'
                recapture = _see(nb2, move.final.row, move.final.col, opp2)
                net       = vv - recapture
                if net > best_gain:
                    best_gain = net
                    best_cap  = (piece, move)
            if best_cap:
                # Only shortcut if this is the ONLY big winner
                # (if multiple exist, search finds the best one)
                piece, move = best_cap
                live = board.squares[move.initial.row][move.initial.col].piece
                if live:
                    _clear(board)
                    print(f"[Win capture +{best_gain}cp]")
                    return {'piece': live, 'move': move}

        # Opening book (skip if winning capture exists)
        if not opp_mate:
            has_win_cap = any(
                _see_ok(board, m, 100)
                for (_, m, _, _) in anow
                if board.squares[m.final.row][m.final.col].piece
            )
            if not has_win_cap:
                bsn=self.book.get_move(self.move_history,self.color)
                if bsn:
                    for r in range(8):
                        for c in range(8):
                            p=board.squares[r][c].piece
                            if p and p.color==self.color:
                                board.calc_moves(p,r,c,bool=True)
                                for m in p.moves:
                                    d=board.squares[m.final.row][m.final.col].piece
                                    if d and d.color==self.color: continue
                                    if _move_to_san(board,p,m)==bsn:
                                        _clear(board)
                                        print(f"[Book] {bsn}")
                                        return {'piece':p,'move':m}
                    _clear(board)

        # Iterative deepening
        best       = None
        top_moves  = []
        for depth in range(1, max_d+1):
            res, smoves = self._root(board, depth)
            if res: best = res
            if smoves: top_moves = smoves
            if self.timeout or time.time()-self.start_time>self._tl: break

        # ── Normal post-search blunder ─────────────────────────────────────
        # Pick 2nd/3rd best move sometimes — simulates missing deep tactics
        # but never hangs a piece in one move (SEE-checked)
        if self.difficulty == 'normal' and len(top_moves) >= 3:
            if random.random() < self._blunder_rate:
                safe = []
                for cp, cm, cs in top_moves[1:4]:
                    # Skip if it immediately loses material
                    vic = board.squares[cm.final.row][cm.final.col].piece
                    if vic:
                        if _see_ok(board, cm, -200):
                            safe.append((cp, cm))
                    else:
                        # Quiet move: skip only if piece is already hanging and move doesn't save it
                        safe.append((cp, cm))
                if safe:
                    cp, cm = random.choice(safe)
                    live = board.squares[cm.initial.row][cm.initial.col].piece
                    _clear(board)
                    print("[Normal miss]")
                    if live:
                        return {'piece': live, 'move': cm}

        _clear(board)
        return best

    def _root(self, board, depth):
        alpha=-float('inf'); beta=float('inf')
        best=None; bs=-float('inf')
        scored = []
        am=_legal_moves(board,self.color)
        if not am: return None, []
        opp='black' if self.color=='white' else 'white'
        bh=self.tt.get(_hash(board))
        ttm=bh[3] if bh else None
        k=self.killers[0]
        am.sort(key=lambda x:_mscore(x[1],board,k[0] if k else None,k[1] if k else None,ttm,self),reverse=True)
        for (piece,move,r,c) in am:
            if self.timeout: break
            nb=_apply(board,piece,move)
            sc=-self._ab(nb,depth-1,-beta,-alpha,opp,True,1)
            scored.append((piece, move, sc))
            if sc>bs:
                bs=sc; alpha=sc
                live=board.squares[move.initial.row][move.initial.col].piece
                best={'piece':live,'move':move}
        if best:
            r=best['move'].initial.row; c=best['move'].initial.col
            lp=board.squares[r][c].piece
            if not lp or lp.color!=self.color:
                am=_legal_moves(board,self.color)
                best={'piece':am[0][0],'move':am[0][1]} if am else None
            else: best['piece']=lp
        scored.sort(key=lambda x: x[2], reverse=True)
        return best, scored

    def _ab(self, board, depth, alpha, beta, color, null=True, ply=1):
        self.nodes+=1
        if self.nodes%1000==0:
            if time.time()-self.start_time>self._tl: self.timeout=True
        if self.timeout: return 0

        h=_hash(board); te=self.tt.get(h); ttm=None
        if te and te[0]>=depth:
            td,tf,ts,ttm=te
            if tf==TT_EXACT: return ts
            if tf==TT_LOWER and ts>=beta: return ts
            if tf==TT_UPPER and ts<=alpha: return ts

        qs_max = self._qs_depth
        if depth<=0: return _qsearch(board,alpha,beta,color,max_depth=qs_max,bot=self)

        am=_legal_moves(board,color); ic=_in_check(board,color)
        if not am: return (-(PV[King]+500-ply)) if ic else 0
        if ic: depth+=1

        if self._null_move and null and not ic and depth>=3 and not _endgame(board):
            nc='black' if color=='white' else 'white'
            R=3 if depth>=6 else 2
            ns=-self._ab(_copy(board),depth-1-R,-beta,-beta+1,nc,False,ply+1)
            if ns>=beta: return beta

        k=self.killers[ply] if ply<len(self.killers) else [None,None]
        am.sort(key=lambda x:_mscore(x[1],board,k[0] if k else None,k[1] if k else None,ttm,self),reverse=True)

        nc='black' if color=='white' else 'white'
        orig=alpha; bm=None

        for i,(piece,move,r,c) in enumerate(am):
            if self.timeout: break
            nb=_apply(board,piece,move)
            cap=bool(board.squares[move.final.row][move.final.col].piece)
            gc=_in_check(nb,nc)

            ext = 0
            if self._use_checks and gc and depth >= 2:
                ext = 1   # extend checks, but only if depth >= 2 to prevent infinite recursion
            
            red=0
            if i>=4 and depth>=3 and not cap and not ic and not gc:
                red=1 if i<8 else 2

            # Clamp: new_depth must be < current depth to prevent infinite recursion
            new_depth = min(depth-1, depth-1-red+ext)
            sc=-self._ab(nb,new_depth,-beta,-alpha,nc,True,ply+1)
            if red>0 and sc>alpha and not self.timeout:
                new_depth2 = min(depth-1, depth-1+ext)
                sc=-self._ab(nb,new_depth2,-beta,-alpha,nc,True,ply+1)

            if sc>=beta:
                if not cap and ply<len(self.killers):
                    if not self.killers[ply][0] or self.killers[ply][0]!=move:
                        self.killers[ply][1]=self.killers[ply][0]
                        self.killers[ply][0]=move
                    key=(type(piece).__name__,(move.final.row,move.final.col))
                    self.history[key]=self.history.get(key,0)+depth*depth
                self.tt[h]=(depth,TT_LOWER,beta,move)
                return beta
            if sc>alpha: alpha=sc; bm=move

        if not self.timeout and bm:
            self.tt[h]=(depth,TT_EXACT if alpha>orig else TT_UPPER,alpha,bm)
        if len(self.tt)>300_000: self.tt.clear()
        return alpha