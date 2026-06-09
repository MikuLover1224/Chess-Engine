from const import *
from square import Square
from piece import *
from move import Move
from sound import Sound
import os

class Board:

    def __init__(self):
        self.squares = [[0]*8 for _ in range(COLS)]
        self.last_move = None
        self.position_history = {}
        self._create()
        self._add_pieces('white')
        self._add_pieces('black')

    # ── Position tracking ────────────────────────────────────────────────────

    def record_position(self):
        h = self._pos_hash()
        self.position_history[h] = self.position_history.get(h, 0) + 1

    def is_threefold_repetition(self):
        return any(v >= 3 for v in self.position_history.values())

    def _pos_hash(self):
        parts = []
        for row in range(ROWS):
            for col in range(COLS):
                p = self.squares[row][col].piece
                if p:
                    parts.append((row, col, type(p).__name__, p.color,
                                  getattr(p, 'en_passant', False),
                                  getattr(p, 'moved', False)))
        return hash(tuple(parts))

    def is_insufficient_material(self):
        pieces = []
        for row in range(ROWS):
            for col in range(COLS):
                p = self.squares[row][col].piece
                if p and not isinstance(p, King):
                    pieces.append((p, row, col))
        if len(pieces) == 0:
            return True
        if len(pieces) == 1:
            return isinstance(pieces[0][0], (Knight, Bishop))
        if len(pieces) == 2:
            p1, r1, c1 = pieces[0]
            p2, r2, c2 = pieces[1]
            if isinstance(p1, Bishop) and isinstance(p2, Bishop):
                return (r1 + c1) % 2 == (r2 + c2) % 2
        return False

    # ── Move execution ───────────────────────────────────────────────────────

    def move(self, piece, move, game=None, testing=False):
        initial = move.initial
        final   = move.final

        en_passant_empty = self.squares[final.row][final.col].isempty()

        # Vacate initial square, place piece on final square
        self.squares[initial.row][initial.col].piece = None
        self.squares[final.row][final.col].piece     = piece

        # ── Pawn ────────────────────────────────────────────────────────
        if isinstance(piece, Pawn):
            diff = final.col - initial.col

            # En passant: captured pawn sits beside initial square
            if diff != 0 and en_passant_empty:
                self.squares[initial.row][final.col].piece = None
                if not testing:
                    Sound(os.path.join('assets', 'sounds', 'capture.wav')).play()

            # Promotion: fires when pawn reaches back rank
            if final.row in (0, 7):
                if testing:
                    # Auto-queen during search
                    self.squares[final.row][final.col].piece = Queen(piece.color)
                elif game and not testing:
                    game.promoting        = True
                    game.promotion_square = (final.row, final.col)
                    game.promotion_color  = piece.color

        # ── Castling ────────────────────────────────────────────────────
        if isinstance(piece, King) and self.castling(initial, final):
            diff = final.col - initial.col
            if diff < 0:
                # Queenside: rook a-file → d-file
                rook_from_col = 0
                rook_to_col   = 3
            else:
                # Kingside: rook h-file → f-file
                rook_from_col = 7
                rook_to_col   = 5

            rook = self.squares[initial.row][rook_from_col].piece
            if rook and isinstance(rook, Rook):
                self.squares[initial.row][rook_from_col].piece = None
                self.squares[initial.row][rook_to_col].piece   = rook
                rook.moved = True
                rook.clear_moves()

        piece.moved = True
        piece.clear_moves()
        self.last_move = move

    def valid_move(self, piece, move):
        return move in piece.moves

    def castling(self, initial, final):
        return abs(initial.col - final.col) == 2

    def set_true_en_passant(self, piece):
        """Clear all en_passant flags then set only on the pawn that double-moved."""
        # Clear ALL pawns first
        for row in range(ROWS):
            for col in range(COLS):
                p = self.squares[row][col].piece
                if isinstance(p, Pawn):
                    p.en_passant = False

        if not isinstance(piece, Pawn):
            return

        # Only set flag if pawn actually moved two squares
        if self.last_move:
            row_diff = abs(self.last_move.final.row - self.last_move.initial.row)
            if row_diff == 2:
                piece.en_passant = True

    # ── Check detection (fast — no deepcopy) ────────────────────────────────

    def in_check(self, piece, move):
        tb = self._fast_copy()

        tp = tb.squares[move.initial.row][move.initial.col].piece
        if tp is None:
            return False

        tb.move(tp, move, testing=True)

        king_pos = None

        for r in range(ROWS):
            for c in range(COLS):
                p = tb.squares[r][c].piece
                if isinstance(p, King) and p.color == piece.color:
                    king_pos = (r, c)
                    break
            if king_pos:
                break

        if king_pos is None:
            return True

        enemy_color = 'black' if piece.color == 'white' else 'white'

        for r in range(ROWS):
            for c in range(COLS):
                p = tb.squares[r][c].piece

                if p and p.color == enemy_color:
                    p.clear_moves()

                    tb.calc_moves(p, r, c, bool=False)

                    for m in p.moves:
                        if (m.final.row, m.final.col) == king_pos:
                            return True

                    p.clear_moves()

        return False

    def _fast_copy(self):
        """Fast board copy — no deepcopy."""
        new = Board.__new__(Board)
        new.squares = [[None]*8 for _ in range(8)]
        new.last_move        = self.last_move
        new.position_history = {}
        for r in range(8):
            for c in range(8):
                os_ = self.squares[r][c]
                ns  = Square.__new__(Square)
                ns.row = os_.row; ns.col = os_.col; ns.alphacol = os_.alphacol
                if os_.piece is None:
                    ns.piece = None
                else:
                    op = os_.piece
                    np = op.__class__.__new__(op.__class__)
                    np.name = op.name; np.color = op.color; np.value = op.value
                    np.moved = op.moved; np.texture = op.texture
                    np.texture_rect = op.texture_rect; np.moves = []
                    if isinstance(op, Pawn):
                        np.dir = op.dir; np.en_passant = op.en_passant
                    if isinstance(op, King):
                        np.left_rook = None; np.right_rook = None
                    ns.piece = np
                new.squares[r][c] = ns

        piece_map = {}

        for r in range(8):
            for c in range(8):
                old_piece = self.squares[r][c].piece
                new_piece = new.squares[r][c].piece

                if old_piece and new_piece:
                    piece_map[id(old_piece)] = new_piece

        for r in range(8):
            for c in range(8):

                old_piece = self.squares[r][c].piece
                new_piece = new.squares[r][c].piece

                if isinstance(old_piece, King):

                    if old_piece.left_rook:
                        new_piece.left_rook = piece_map.get(id(old_piece.left_rook))

                    if old_piece.right_rook:
                        new_piece.right_rook = piece_map.get(id(old_piece.right_rook))
        return new
    

    # ── Move generation ──────────────────────────────────────────────────────

    def calc_moves(self, piece, row, col, bool=True):
        piece.clear_moves()

        def add(move):
            if bool:
                if not self.in_check(piece, move):
                    piece.add_move(move)
            else:
                piece.add_move(move)

        def mk(r, c):
            return Move(Square(row, col), Square(r, c, self.squares[r][c].piece))

        # ── Pawn ────────────────────────────────────────────────────────
        if isinstance(piece, Pawn):
            steps = 1 if piece.moved else 2
            # Straight push
            for i in range(1, steps + 1):
                nr = row + piece.dir * i
                if not Square.in_range(nr): break
                if not self.squares[nr][col].isempty(): break
                add(mk(nr, col))

            # Diagonal captures
            for dc in [-1, 1]:
                nr, nc = row + piece.dir, col + dc
                if Square.in_range(nr, nc):
                    if self.squares[nr][nc].has_enemy_piece(piece.color):
                        add(mk(nr, nc))

            # En passant
            ep_row = 3 if piece.color == 'white' else 4
            if row == ep_row:
                for dc in [-1, 1]:
                    nc = col + dc
                    if not Square.in_range(nc): continue
                    adj = self.squares[row][nc].piece
                    if isinstance(adj, Pawn) and adj.color != piece.color and adj.en_passant:
                        nr = row + piece.dir
                        add(Move(Square(row, col), Square(nr, nc, adj)))

        # ── Knight ──────────────────────────────────────────────────────
        elif isinstance(piece, Knight):
            for dr, dc in [(-2,1),(-1,2),(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1)]:
                nr, nc = row+dr, col+dc
                if Square.in_range(nr, nc) and self.squares[nr][nc].isempty_or_enemy(piece.color):
                    add(mk(nr, nc))

        # ── Bishop / Rook / Queen ────────────────────────────────────────
        elif isinstance(piece, (Bishop, Rook, Queen)):
            if isinstance(piece, Bishop):
                dirs = [(-1,-1),(-1,1),(1,-1),(1,1)]
            elif isinstance(piece, Rook):
                dirs = [(-1,0),(0,1),(1,0),(0,-1)]
            else:
                dirs = [(-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(0,1),(1,0),(0,-1)]
            for dr, dc in dirs:
                nr, nc = row+dr, col+dc
                while Square.in_range(nr, nc):
                    if self.squares[nr][nc].isempty():
                        add(mk(nr, nc))
                    elif self.squares[nr][nc].has_enemy_piece(piece.color):
                        add(mk(nr, nc)); break
                    else:
                        break
                    nr += dr; nc += dc

        # ── King ────────────────────────────────────────────────────────
        elif isinstance(piece, King):
            for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                nr, nc = row+dr, col+dc
                if Square.in_range(nr, nc) and self.squares[nr][nc].isempty_or_enemy(piece.color):
                    add(Move(Square(row, col), Square(nr, nc)))

            # Castling — king must not have moved
            if not piece.moved:

                # ── Queenside (O-O-O): king e→c, rook a→d ───────────────
                left_rook = self.squares[row][0].piece
                if isinstance(left_rook, Rook) and not left_rook.moved:
                    # b, c, d files must be empty (cols 1, 2, 3)
                    path_clear = all(self.squares[row][c].isempty() for c in [1, 2, 3])
                    if path_clear:
                        moveK     = Move(Square(row, col), Square(row, 2))
                        # King must not be in check now, or on col 3, or on col 2
                        thru_d    = Move(Square(row, col), Square(row, 3))
                        if bool:
                            # Check current square, d-file, c-file
                            cur_check = Move(Square(row, col), Square(row, col))
                            ok = (not self.in_check(piece, cur_check)
                                  and not self.in_check(piece, thru_d)
                                  and not self.in_check(piece, moveK))
                            if ok:
                                moveR = Move(Square(row, 0), Square(row, 3))
                                left_rook.add_move(moveR)
                                piece.add_move(moveK)
                        else:
                            moveR = Move(Square(row, 0), Square(row, 3))
                            left_rook.add_move(moveR)
                            piece.add_move(moveK)

                # ── Kingside (O-O): king e→g, rook h→f ──────────────────
                right_rook = self.squares[row][7].piece
                if isinstance(right_rook, Rook) and not right_rook.moved:
                    # f, g files must be empty (cols 5, 6)
                    path_clear = all(self.squares[row][c].isempty() for c in [5, 6])
                    if path_clear:
                        moveK  = Move(Square(row, col), Square(row, 6))
                        thru_f = Move(Square(row, col), Square(row, 5))
                        if bool:
                            cur_check = Move(Square(row, col), Square(row, col))
                            ok = (not self.in_check(piece, cur_check)
                                  and not self.in_check(piece, thru_f)
                                  and not self.in_check(piece, moveK))
                            if ok:
                                moveR = Move(Square(row, 7), Square(row, 5))
                                right_rook.add_move(moveR)
                                piece.add_move(moveK)
                        else:
                            moveR = Move(Square(row, 7), Square(row, 5))
                            right_rook.add_move(moveR)
                            piece.add_move(moveK)

    # ── Board setup ──────────────────────────────────────────────────────────

    def _create(self):
        for row in range(ROWS):
            for col in range(COLS):
                self.squares[row][col] = Square(row, col)

    def _add_pieces(self, color):
        row_pawn  = 6 if color == 'white' else 1
        row_other = 7 if color == 'white' else 0
        for col in range(COLS):
            self.squares[row_pawn][col] = Square(row_pawn, col, Pawn(color))
        order = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for col, PieceClass in enumerate(order):
            self.squares[row_other][col] = Square(row_other, col, PieceClass(color))