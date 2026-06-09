import os
import pygame


from const import *
from board import Board
from dragger import Dragger
from config import Config
from square import Square

class Game:

    def __init__(self):
        self.next_player = 'white'
        self.hovered_sqr = None
        self.board = Board()
        self.dragger = Dragger()
        self.config = Config()
        self.promoting = False
        self.promotion_square = None
        self.promotion_color = None
        self._img_cache = {}   # path -> pygame.Surface

    def _load_img(self, path):
        """Load and cache a piece image."""
        if path not in self._img_cache:
            self._img_cache[path] = pygame.image.load(path).convert_alpha()
        return self._img_cache[path]

    # blit methods

    def show_bg(self, surface, flipped=False):
        theme = self.config.theme
        for row in range(ROWS):
            for col in range(COLS):
                dr = 7 - row if flipped else row
                dc = 7 - col if flipped else col
                color = theme.bg.light if (row + col) % 2 == 0 else theme.bg.dark
                rect = (col * SQSIZE, row * SQSIZE, SQSIZE, SQSIZE)
                pygame.draw.rect(surface, color, rect)
                if col == 0:
                    color = theme.bg.dark if row % 2 == 0 else theme.bg.light
                    lbl = self.config.font.render(str(dr + 1), 1, color)
                    surface.blit(lbl, (5, 5 + row * SQSIZE))
                if row == 7:
                    color = theme.bg.dark if (row + col) % 2 == 0 else theme.bg.light
                    lbl = self.config.font.render(Square.get_alphacol(dc), 1, color)
                    surface.blit(lbl, (col * SQSIZE + SQSIZE - 20, HEIGHT - 20))

    def show_pieces(self, surface, flipped=False):
        for row in range(ROWS):
            for col in range(COLS):
                dr = 7 - row if flipped else row
                dc = 7 - col if flipped else col
                if self.board.squares[dr][dc].has_piece():
                    piece = self.board.squares[dr][dc].piece
                    if piece is not self.dragger.piece:
                        piece.set_texture(size=80)
                        img = self._load_img(piece.texture)
                        img_center = col * SQSIZE + SQSIZE // 2, row * SQSIZE + SQSIZE // 2
                        piece.texture_rect = img.get_rect(center=img_center)
                        surface.blit(img, piece.texture_rect)

    def show_promotion(self, surface, flipped=False):
        if not self.promoting or self.promotion_square is None:
            return

        row, col = self.promotion_square
        dc = 7 - col if flipped else col
        color  = self.promotion_color
        pieces = ['queen', 'rook', 'bishop', 'knight']

        # Horizontal bar — 4 pieces side by side, centered on promotion column
        start_col = max(0, min(dc, COLS - 4))

        # Position bar: 
        # - White promotes on rank 8 (top of board), so bar at top
        # - Black promotes on rank 1 (bottom of board), so bar at bottom
        # When flipped, swap the positions
        if (color == 'white' and not flipped) or (color == 'black' and flipped):
            bar_y = 0
        else:
            bar_y = HEIGHT - SQSIZE - 8

        bar_rect = pygame.Rect(start_col * SQSIZE, bar_y, 4 * SQSIZE, SQSIZE + 8)
        pygame.draw.rect(surface, (30, 30, 30), bar_rect)
        pygame.draw.rect(surface, (200, 200, 200), bar_rect, 2)

        for i, name in enumerate(pieces):
            pc = start_col + i
            px = pc * SQSIZE
            py = bar_y + 4

            # Hover highlight
            mx, my = pygame.mouse.get_pos()
            hovered = (px <= mx < px + SQSIZE and py <= my < py + SQSIZE)
            bg = (80, 80, 80) if hovered else (50, 50, 50)
            pygame.draw.rect(surface, bg, (px, py, SQSIZE, SQSIZE))

            # Fix the path here too
            import os
            _HERE = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(_HERE, 'assets', 'images', 'imgs-80px', f'{color}_{name}.png')
            img  = self._load_img(path)
            img  = pygame.transform.scale(img, (SQSIZE, SQSIZE))
            surface.blit(img, (px, py))

    def show_moves(self, surface, flipped=False):
        theme = self.config.theme
        if self.dragger.dragging:
            piece = self.dragger.piece
            for move in piece.moves:
                fr = 7 - move.final.row if flipped else move.final.row
                fc = 7 - move.final.col if flipped else move.final.col
                color = theme.moves.light if (fr + fc) % 2 == 0 else theme.moves.dark
                rect = (fc * SQSIZE, fr * SQSIZE, SQSIZE, SQSIZE)
                pygame.draw.rect(surface, color, rect)

    def show_last_move(self, surface, flipped=False):
        theme = self.config.theme
        if self.board.last_move:
            for pos in [self.board.last_move.initial, self.board.last_move.final]:
                r = 7 - pos.row if flipped else pos.row
                c = 7 - pos.col if flipped else pos.col
                color = theme.trace.light if (r + c) % 2 == 0 else theme.trace.dark
                pygame.draw.rect(surface, color, (c * SQSIZE, r * SQSIZE, SQSIZE, SQSIZE))

    def show_hover(self, surface, flipped=False):
        if self.hovered_sqr:
            r = 7 - self.hovered_sqr.row if flipped else self.hovered_sqr.row
            c = 7 - self.hovered_sqr.col if flipped else self.hovered_sqr.col
            pygame.draw.rect(surface, (180, 180, 180), (c * SQSIZE, r * SQSIZE, SQSIZE, SQSIZE), width=3)

    # other methods

    def next_turn(self):
        self.next_player = 'white' if self.next_player == 'black' else 'black'

    def set_hover(self, row, col):
        if 0 <= row < ROWS and 0 <= col < COLS:
            self.hovered_sqr = self.board.squares[row][col]
        else:
            self.hovered_sqr = None

    def change_theme(self):
        self.config.change_theme()
        self._img_cache.clear()

    def change_skin(self):
        import piece as piece_module
        piece_module.next_skin()
        self._img_cache.clear()
        for row in self.board.squares:
            for sq in row:
                if sq.has_piece():
                    sq.piece.set_texture(size=80)

    def play_sound(self, captured=False):
        if captured:
            self.config.capture_sound.play()
        else:
            self.config.move_sound.play()
            
    def reset(self):
        self.__init__()