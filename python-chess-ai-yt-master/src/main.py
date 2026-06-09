import pygame
import sys
import threading
import math

from const import *
from game import Game
from piece import Queen, Rook, Bishop, Knight
from square import Square
from move import Move
from engine.bot import Bot, DIFFICULTY_COLORS, DIFFICULTY_NAMES
import random

# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------
PANEL_W   = 260
WIN_W     = WIDTH + PANEL_W
WIN_H     = HEIGHT

PANEL_BG      = (22,  22,  30)
PANEL_HEADER  = (40,  40,  55)
COL_WHITE_TXT = (240, 240, 240)
COL_BLACK_TXT = (180, 180, 200)
COL_NUMBER    = (100, 100, 130)
COL_HIGHLIGHT = (255, 210, 60)

ARROW_COLOR     = (255, 170, 0, 180)
ARROW_COLOR_ALT = (50,  200, 50, 180)


def draw_arrow(surface, from_sq, to_sq, color, flipped=False):
    fr, fc = from_sq
    tr, tc = to_sq
    if flipped:
        fr, fc = 7 - fr, 7 - fc
        tr, tc = 7 - tr, 7 - tc
    x1 = fc * SQSIZE + SQSIZE // 2
    y1 = fr * SQSIZE + SQSIZE // 2
    x2 = tc * SQSIZE + SQSIZE // 2
    y2 = tr * SQSIZE + SQSIZE // 2
    if (x1, y1) == (x2, y2):
        return
    dx, dy   = x2 - x1, y2 - y1
    length   = math.hypot(dx, dy)
    ux, uy   = dx / length, dy / length
    px, py   = -uy, ux
    shaft_w  = SQSIZE * 0.15
    head_w   = SQSIZE * 0.22
    head_len = SQSIZE * 0.55
    tip_x = x2 - ux * (SQSIZE * 0.08)
    tip_y = y2 - uy * (SQSIZE * 0.08)
    base_x = tip_x - ux * head_len
    base_y = tip_y - uy * head_len
    points = [
        (x1     + px * shaft_w,  y1     + py * shaft_w),
        (base_x + px * shaft_w,  base_y + py * shaft_w),
        (base_x + px * head_w,   base_y + py * head_w),
        (tip_x, tip_y),
        (base_x - px * head_w,   base_y - py * head_w),
        (base_x - px * shaft_w,  base_y - py * shaft_w),
        (x1     - px * shaft_w,  y1     - py * shaft_w),
    ]
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(surf, color, points)
    surface.blit(surf, (0, 0))


def sq_from_pos(pos, flipped=False):
    c = pos[0] // SQSIZE
    r = pos[1] // SQSIZE
    if 0 <= r < ROWS and 0 <= c < COLS:
        if flipped:
            return (7 - r, 7 - c)
        return (r, c)
    return None


def draw_move_panel(surface, move_list, font_move, font_header, scroll_offset, copy_flash, flipped=False, game_over=None, difficulty=None):
    px = WIDTH
    pygame.draw.rect(surface, PANEL_BG, (px, 0, PANEL_W, WIN_H))

    # Header
    pygame.draw.rect(surface, PANEL_HEADER, (px, 0, PANEL_W, 36))
    hdr = font_header.render("Move History", True, COL_WHITE_TXT)
    surface.blit(hdr, (px + 10, 8))

    # Difficulty badge
    if difficulty:
        diff_color = DIFFICULTY_COLORS.get(difficulty, (255, 255, 255))
        diff_name = DIFFICULTY_NAMES.get(difficulty, 'Normal')
        diff_y = 40
        diff_h = 28
        diff_w = PANEL_W - 16
        
        # Badge background
        badge = pygame.Surface((diff_w, diff_h), pygame.SRCALPHA)
        pygame.draw.rect(badge, (*diff_color, 220), (0, 0, diff_w, diff_h), border_radius=8)
        surface.blit(badge, (px + 8, diff_y))
        
        # Badge border
        border_col = tuple(min(255, c + 60) for c in diff_color)
        pygame.draw.rect(surface, border_col, (px + 8, diff_y, diff_w, diff_h), 2, border_radius=8)
        
        # Badge text
        if difficulty == 'hard':
            text_color = (255, 255, 255)
        else:
            text_color = (0, 0, 0)
        
        if difficulty == 'easy':
            icon = "●"
        elif difficulty == 'normal':
            icon = "◆"
        else:
            icon = "▲"
        
        badge_text = f"{icon}  Bot: {diff_name}  {icon}"
        lbl = font_move.render(badge_text, True, text_color)
        surface.blit(lbl, (px + PANEL_W//2 - lbl.get_width()//2, diff_y + 6))

    # Buttons
    btn_h    = 34
    resign_y = WIN_H - btn_h * 4 - 8
    draw_y   = WIN_H - btn_h * 3 - 6
    flip_y   = WIN_H - btn_h * 2 - 4
    copy_y   = WIN_H - btn_h

    resign_col = (210, 40, 40) if not game_over else (60, 60, 60)
    pygame.draw.rect(surface, resign_col, (px, resign_y, PANEL_W, btn_h))
    r_lbl = font_header.render("Resign", True, (255, 255, 255))
    surface.blit(r_lbl, (px + PANEL_W//2 - r_lbl.get_width()//2, resign_y + 8))

    draw_col = (90, 100, 120) if not game_over else (60, 60, 60)
    pygame.draw.rect(surface, draw_col, (px, draw_y, PANEL_W, btn_h))
    d_lbl = font_header.render("Offer Draw", True, (220, 220, 230))
    surface.blit(d_lbl, (px + PANEL_W//2 - d_lbl.get_width()//2, draw_y + 8))

    flip_col = (100, 80, 200) if flipped else (70, 55, 160)
    pygame.draw.rect(surface, flip_col, (px, flip_y, PANEL_W, btn_h))
    flip_lbl = font_header.render("Flip", True, COL_WHITE_TXT)
    surface.blit(flip_lbl, (px + PANEL_W//2 - flip_lbl.get_width()//2, flip_y + 8))

    btn_color = (50, 200, 100) if copy_flash > 0 else (30, 140, 130)
    pygame.draw.rect(surface, btn_color, (px, copy_y, PANEL_W, btn_h))
    btn_lbl = font_header.render("Copied!" if copy_flash > 0 else "Copy PGN", True, COL_WHITE_TXT)
    surface.blit(btn_lbl, (px + PANEL_W//2 - btn_lbl.get_width()//2, copy_y + 8))

    # Move rows
    y_start = 76 if difficulty else 44
    rows = []
    for i in range(0, len(move_list), 2):
        w = move_list[i]
        b = move_list[i + 1] if i + 1 < len(move_list) else ""
        rows.append((i // 2 + 1, w, b))

    row_h   = 24
    y_end   = resign_y - 4
    visible = (y_end - y_start) // row_h
    max_scroll = max(0, len(rows) - visible)
    scroll_offset = min(scroll_offset, max_scroll)

    for idx, (num, white_san, black_san) in enumerate(rows[scroll_offset:]):
        y = y_start + idx * row_h
        if y + row_h > y_end:
            break
        if idx % 2 == 0:
            pygame.draw.rect(surface, (35, 35, 50), (px, y, PANEL_W, row_h))
        surface.blit(font_move.render(f"{num}.", True, COL_NUMBER), (px + 6, y + 4))
        is_last = (num == len(rows))
        w_col = COL_HIGHLIGHT if (is_last and len(move_list) % 2 == 1) else COL_WHITE_TXT
        b_col = COL_HIGHLIGHT if (is_last and len(move_list) % 2 == 0) else COL_BLACK_TXT
        surface.blit(font_move.render(white_san, True, w_col), (px + 40,  y + 4))
        if black_san:
            surface.blit(font_move.render(black_san, True, b_col), (px + 140, y + 4))

    return scroll_offset


def build_pgn(move_list):
    parts = []
    for i in range(0, len(move_list), 2):
        num = i // 2 + 1
        w   = move_list[i]
        b   = move_list[i + 1] if i + 1 < len(move_list) else ""
        parts.append(f"{num}. {w} {b}".strip())
    return " ".join(parts)


def check_game_over(board, next_player):
    from piece import King

    if board.is_insufficient_material():
        return 'draw_material'
    if board.is_threefold_repetition():
        return 'draw_repetition'

    has_moves = False
    for r in range(ROWS):
        for c in range(COLS):
            p = board.squares[r][c].piece
            if p and p.color == next_player:
                board.calc_moves(p, r, c, bool=True)
                if p.moves:
                    has_moves = True
                    break
        if has_moves:
            break

    if not has_moves:
        enemy = 'black' if next_player == 'white' else 'white'
        king_pos = None
        for r in range(ROWS):
            for c in range(COLS):
                p = board.squares[r][c].piece
                if isinstance(p, King) and p.color == next_player:
                    king_pos = (r, c); break
            if king_pos: break
        in_check = False
        if king_pos:
            for r in range(ROWS):
                for c in range(COLS):
                    p = board.squares[r][c].piece
                    if p and p.color == enemy:
                        board.calc_moves(p, r, c, bool=False)
                        for m in p.moves:
                            if (m.final.row, m.final.col) == king_pos:
                                in_check = True; break
                    if in_check: break
                if in_check: break
        return 'checkmate' if in_check else 'stalemate'
    return None


class Main:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption('Chess')
        self.game = Game()

    def _draw_menu(self, screen, step, hovered, font_title, font_btn, font_sub, font_desc, difficulty=None):
        screen.fill((18, 18, 18))

        title = font_title.render("Chess", True, (255, 215, 50))
        screen.blit(title, (WIN_W//2 - title.get_width()//2, 60))

        if step == 0:
            sub = font_sub.render("Choose game mode", True, (160, 160, 160))
            screen.blit(sub, (WIN_W//2 - sub.get_width()//2, 140))
            buttons = ["vs Bot", "1 vs 1"]
            btn_colors = [(70, 130, 180), (70, 130, 180)]
        elif step == 1:
            sub = font_sub.render("Choose difficulty", True, (160, 160, 160))
            screen.blit(sub, (WIN_W//2 - sub.get_width()//2, 140))
            buttons = ["Easy", "Normal", "Hard"]
            btn_colors = [
                DIFFICULTY_COLORS['easy'],
                DIFFICULTY_COLORS['normal'],
                DIFFICULTY_COLORS['hard']
            ]
        else:
            sub = font_sub.render("Choose your colour", True, (160, 160, 160))
            screen.blit(sub, (WIN_W//2 - sub.get_width()//2, 140))
            buttons = ["White", "Black", "Random"]
            btn_colors = [(70, 130, 180), (70, 130, 180), (70, 130, 180)]

        rects = []
        bw, bh = 300, 64
        gap    = 16
        total  = len(buttons) * bh + (len(buttons) - 1) * gap
        start_y = WIN_H//2 - total//2 + 20

        for i, label in enumerate(buttons):
            bx = WIN_W//2 - bw//2
            by = start_y + i * (bh + gap)
            
            if step == 1:
                base_color = btn_colors[i]
                if i == hovered:
                    col = tuple(min(255, c + 80) for c in base_color)
                    glow = pygame.Rect(bx - 3, by - 3, bw + 6, bh + 6)
                    pygame.draw.rect(screen, (255, 255, 255, 30), glow, border_radius=12)
                else:
                    col = base_color
                
                if label == 'Hard':
                    text_color = (255, 255, 255)
                else:
                    text_color = (0, 0, 0)
            else:
                col = (70, 130, 180) if i == hovered else (40, 40, 55)
                text_color = (240, 240, 240)
            
            pygame.draw.rect(screen, col, (bx, by, bw, bh), border_radius=10)
            pygame.draw.rect(screen, (180, 180, 180), (bx, by, bw, bh), 2, border_radius=10)
            
            lbl = font_btn.render(label, True, text_color)
            if step == 1:
                screen.blit(lbl, (bx + bw//2 - lbl.get_width()//2, by + 10))
                if label == 'Easy':
                    desc = "Blunders often"
                elif label == 'Normal':
                    desc = "Blunders sometimes"
                else:
                    desc = "Plays perfectly"
                dlbl = font_desc.render(desc, True, text_color)
                screen.blit(dlbl, (bx + bw//2 - dlbl.get_width()//2, by + 40))
            else:
                screen.blit(lbl, (bx + bw//2 - lbl.get_width()//2, by + bh//2 - lbl.get_height()//2))
            
            rects.append(pygame.Rect(bx, by, bw, bh))

        # Difficulty badge in step 2
        if step == 2 and difficulty:
            diff_color = DIFFICULTY_COLORS.get(difficulty, (255, 255, 255))
            diff_name = DIFFICULTY_NAMES.get(difficulty, 'Normal')
            
            badge_y = WIN_H - 100
            badge_w = 220
            badge_h = 42
            
            badge = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
            pygame.draw.rect(badge, (*diff_color, 230), (0, 0, badge_w, badge_h), border_radius=10)
            screen.blit(badge, (WIN_W//2 - badge_w//2, badge_y))
            
            border_col = tuple(min(255, c + 50) for c in diff_color)
            pygame.draw.rect(screen, border_col, (WIN_W//2 - badge_w//2, badge_y, badge_w, badge_h), 2, border_radius=10)
            
            text_col = (0, 0, 0) if difficulty != 'hard' else (255, 255, 255)
            badge_lbl = font_btn.render(f"Difficulty: {diff_name}", True, text_col)
            screen.blit(badge_lbl, (WIN_W//2 - badge_lbl.get_width()//2, badge_y + 9))

        hint = font_sub.render("Press  ESC  to go back" if step >= 1 else "", True, (80, 80, 80))
        screen.blit(hint, (WIN_W//2 - hint.get_width()//2, WIN_H - 40))

        pygame.display.update()
        return rects

    def _run_menu(self, screen):
        font_title = pygame.font.SysFont('monospace', 64, bold=True)
        font_btn   = pygame.font.SysFont('monospace', 24, bold=True)
        font_sub   = pygame.font.SysFont('monospace', 18)
        font_desc  = pygame.font.SysFont('monospace', 12)

        step       = 0
        vs_bot     = True
        difficulty = 'normal'
        hovered    = -1
        clock      = pygame.time.Clock()

        while True:
            clock.tick(60)
            mx, my = pygame.mouse.get_pos()
            rects  = self._draw_menu(screen, step, hovered, font_title, font_btn, font_sub, font_desc, difficulty)

            hovered = -1
            for i, r in enumerate(rects):
                if r.collidepoint(mx, my):
                    hovered = i
                    break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if step == 2:
                            step = 1
                        elif step == 1:
                            step = 0

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, r in enumerate(rects):
                        if r.collidepoint(event.pos):
                            if step == 0:
                                vs_bot = (i == 0)
                                if vs_bot:
                                    step = 1
                                else:
                                    return False, 'white', 'normal'
                            elif step == 1:
                                difficulties = ['easy', 'normal', 'hard']
                                difficulty = difficulties[i]
                                step = 2
                            else:
                                colors = ['white', 'black', 'random']
                                choice = colors[i]
                                if choice == 'random':
                                    choice = random.choice(['white', 'black'])
                                return True, choice, difficulty

    def mainloop(self):
        screen  = self.screen
        game    = self.game
        board   = self.game.board
        dragger = self.game.dragger

        vs_bot, player_color, difficulty = self._run_menu(screen)

        if vs_bot:
            bot_color = "black" if player_color == "white" else "white"
            bot = Bot(bot_color, difficulty=difficulty)
        else:
            bot_color = None
            bot = None

        bot_precompute = [None]
        bot_precomputing = [False]
        bot_needs_recompute = [True]
        
        clock = pygame.time.Clock()

        arrows         = []
        arrow_start_sq = None
        arrow_preview  = None

        move_list          = []
        panel_scroll       = 0
        copy_flash         = 0
        flipped            = False
        game_over          = None
        draw_offer_pending = False
        font_move          = pygame.font.SysFont('monospace', 15)
        font_header        = pygame.font.SysFont('monospace', 16, bold=True)
        font_big           = pygame.font.SysFont('monospace', 36, bold=True)

        if vs_bot and game.next_player == bot_color:
            bot_needs_recompute[0] = True

        while True:
            clock.tick(60)

            if vs_bot and not game_over:
                if bot_needs_recompute[0] and game.next_player == bot_color and not game.promoting and not dragger.dragging:
                    if not bot_precomputing[0] and bot_precompute[0] is None:
                        bot_needs_recompute[0] = False
                        bot_precomputing[0] = True
                        
                        def precompute():
                            result = bot.play(board)
                            bot_precompute[0] = result
                            bot_precomputing[0] = False
                        
                        threading.Thread(target=precompute, daemon=True).start()

            if vs_bot and not game_over:
                if game.next_player == bot_color and not game.promoting and not dragger.dragging:
                    if bot_precompute[0] is not None:
                        best = bot_precompute[0]
                        bot_precompute[0] = None
                        
                        if best is not None:
                            piece = best['piece']
                            move = best['move']
                            from engine.bot import _move_to_san
                            san = _move_to_san(board, piece, move)
                            bot.record_move(san)
                            move_list.append(san)
                            panel_scroll = 9999
                            captured = board.squares[move.final.row][move.final.col].has_piece()
                            from piece import Pawn as PawnPiece, Queen as QueenPiece
                            is_promo = (isinstance(piece, PawnPiece) and
                                        move.final.row in (0, 7))
                            if is_promo:
                                board.move(piece, move, testing=True)
                                board.squares[move.final.row][move.final.col].piece = QueenPiece(piece.color)
                                board.squares[move.final.row][move.final.col].piece.moved = True
                                board.last_move = move
                                game._img_cache.clear()
                            else:
                                board.move(piece, move, game)
                            board.set_true_en_passant(piece)
                            board.record_position()
                            game.play_sound(captured)
                            game.next_turn()
                            bot_needs_recompute[0] = True
                            if not game_over:
                                r = check_game_over(board, game.next_player)
                                if r: game_over = r

            game.show_bg(screen, flipped)
            game.show_last_move(screen, flipped)
            game.show_moves(screen, flipped)
            game.show_pieces(screen, flipped)
            game.show_hover(screen, flipped)
            game.show_promotion(screen, flipped)

            if dragger.dragging:
                dragger.update_blit(screen, game._img_cache)

            for (fsq, tsq, col) in arrows:
                draw_arrow(screen, fsq, tsq, col, flipped)

            if arrow_start_sq and arrow_preview and arrow_start_sq != arrow_preview:
                mods  = pygame.key.get_mods()
                color = ARROW_COLOR_ALT if (mods & pygame.KMOD_SHIFT) else ARROW_COLOR
                draw_arrow(screen, arrow_start_sq, arrow_preview, color, flipped)

            if vs_bot and (bot_precomputing[0] or (bot_precompute[0] is not None and game.next_player == bot_color)):
                font_think = pygame.font.SysFont('monospace', 18, bold=True)
                if bot_precomputing[0]:
                    lbl = font_think.render('Thinking...', True, (200, 180, 50))
                else:
                    lbl = font_think.render('Ready', True, (50, 200, 50))
                screen.blit(lbl, (10, HEIGHT - 28))

            if copy_flash > 0:
                copy_flash -= 1

            panel_scroll = draw_move_panel(
                screen, move_list, font_move, font_header, panel_scroll, copy_flash, flipped, game_over,
                difficulty if vs_bot else None)

            if game_over:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))

                sub2 = ""
                if game_over == 'checkmate':
                    winner = 'black' if game.next_player == 'white' else 'white'
                    msg  = f"Checkmate!  {winner.capitalize()} wins"
                elif game_over == 'stalemate':
                    msg  = "Stalemate  —  Draw"
                    sub2 = "No legal moves available"
                elif game_over == 'draw_repetition':
                    msg  = "Draw by repetition"
                elif game_over == 'draw_material':
                    msg  = "Draw  —  Insufficient material"
                elif game_over == 'resign':
                    if vs_bot:
                        winner = bot_color if game.next_player == player_color else player_color
                    else:
                        winner = 'black' if game.next_player == 'white' else 'white'
                    msg  = f"{winner.capitalize()} wins by resignation"
                elif game_over == 'draw':
                    msg  = "Draw agreed"
                else:
                    msg  = str(game_over)

                bw, bh = 540, 140
                bx = WIDTH//2 - bw//2
                by = HEIGHT//2 - bh//2
                pygame.draw.rect(screen, (18, 18, 18), (bx, by, bw, bh), border_radius=14)
                pygame.draw.rect(screen, (180, 180, 180), (bx, by, bw, bh), 2, border_radius=14)

                lbl = font_big.render(msg, True, (255, 215, 50))
                screen.blit(lbl, (WIDTH//2 - lbl.get_width()//2, by + 18))
                if sub2:
                    s2 = font_move.render(sub2, True, (160, 160, 160))
                    screen.blit(s2, (WIDTH//2 - s2.get_width()//2, by + 68))
                hint = font_move.render("Press  N  for a new game", True, (120, 200, 120))
                screen.blit(hint, (WIDTH//2 - hint.get_width()//2, by + 104))

            if draw_offer_pending:
                overlay2 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay2.fill((0, 0, 0, 120))
                screen.blit(overlay2, (0, 0))
                q1 = font_header.render("Bot offers a draw!" if vs_bot else "Draw offered!", True, (255, 220, 50))
                q2 = font_move.render("Press Y to accept, N to decline", True, (200, 200, 200))
                screen.blit(q1, (WIDTH//2 - q1.get_width()//2, HEIGHT//2 - 30))
                screen.blit(q2, (WIDTH//2 - q2.get_width()//2, HEIGHT//2 + 10))

            for event in pygame.event.get():

                if event.type == pygame.MOUSEBUTTONDOWN:

                    if event.button == 4:
                        panel_scroll = max(0, panel_scroll - 1)
                    elif event.button == 5:
                        panel_scroll += 1

                    elif event.button == 1 and event.pos[0] >= WIDTH:
                        resign_y = WIN_H - 34 * 4 - 8
                        draw_y   = WIN_H - 34 * 3 - 6
                        flip_y   = WIN_H - 34 * 2 - 4
                        copy_y   = WIN_H - 34
                        py = event.pos[1]
                        if py >= resign_y and py < draw_y and not game_over:
                            game_over = 'resign'
                        elif py >= draw_y and py < flip_y and not game_over:
                            if vs_bot:
                                draw_offer_pending = True
                            else:
                                game_over = 'draw'
                        elif py >= flip_y and py < copy_y:
                            flipped = not flipped
                        elif py >= copy_y:
                            pgn = build_pgn(move_list)
                            pygame.scrap.init()
                            pygame.scrap.put(pygame.SCRAP_TEXT, pgn.encode())
                            copy_flash = 90

                    elif event.button == 3:
                        arrow_start_sq = sq_from_pos(event.pos, flipped)
                        arrow_preview  = arrow_start_sq

                    elif event.button == 1:
                        arrows.clear()
                        arrow_start_sq = None
                        arrow_preview  = None

                        if game.promoting:
                            base_row, base_col = game.promotion_square
                            dc = 7 - base_col if flipped else base_col
                            start_col = max(0, min(dc, 8 - 4))
                            color = game.promotion_color
                            if (color == 'white' and not flipped) or (color == 'black' and flipped):
                                bar_y = 0
                            else:
                                bar_y = HEIGHT - SQSIZE - 8

                            mx, my = event.pos
                            if bar_y <= my < bar_y + SQSIZE + 8:
                                actual_y = my - (bar_y + 4)
                                if 0 <= actual_y < SQSIZE:
                                    ci = (mx // SQSIZE) - start_col
                                    if 0 <= ci <= 3:
                                        piece_type = ['queen', 'rook', 'bishop', 'knight'][ci]
                                        if piece_type == 'queen':    new_piece = Queen(color)
                                        elif piece_type == 'rook':   new_piece = Rook(color)
                                        elif piece_type == 'bishop': new_piece = Bishop(color)
                                        else:                        new_piece = Knight(color)
                                        board.squares[base_row][base_col].piece = new_piece
                                        game.promoting = False
                                        game._img_cache.clear()
                                        if not game_over:
                                            r = check_game_over(board, game.next_player)
                                            if r: game_over = r
                            continue

                        if game_over:
                            continue

                        if event.pos[0] >= WIDTH:
                            continue

                        dragger.update_mouse(event.pos)
                        clicked_row = dragger.mouseY // SQSIZE
                        clicked_col = dragger.mouseX // SQSIZE
                        if flipped:
                            clicked_row = 7 - clicked_row
                            clicked_col = 7 - clicked_col

                        if board.squares[clicked_row][clicked_col].has_piece():
                            piece = board.squares[clicked_row][clicked_col].piece
                            can_move = (piece.color == game.next_player and
                                        (not vs_bot or piece.color != bot_color))
                            if can_move:
                                board.calc_moves(piece, clicked_row, clicked_col, bool=True)
                                dragger.update_mouse(event.pos)
                                dragger.initial_row = clicked_row
                                dragger.initial_col = clicked_col
                                dragger.drag_piece(piece)

                elif event.type == pygame.MOUSEMOTION:
                    motion_row = event.pos[1] // SQSIZE
                    motion_col = event.pos[0] // SQSIZE
                    if 0 <= motion_row < ROWS and 0 <= motion_col < COLS:
                        actual_row = 7 - motion_row if flipped else motion_row
                        actual_col = 7 - motion_col if flipped else motion_col
                        game.set_hover(actual_row, actual_col)
                    if dragger.dragging:
                        dragger.update_mouse(event.pos)
                    if arrow_start_sq:
                        arrow_preview = sq_from_pos(event.pos, flipped)

                elif event.type == pygame.MOUSEBUTTONUP:

                    if event.button == 3:
                        end_sq = sq_from_pos(event.pos, flipped)
                        if arrow_start_sq and end_sq and arrow_start_sq != end_sq:
                            mods  = pygame.key.get_mods()
                            color = ARROW_COLOR_ALT if (mods & pygame.KMOD_SHIFT) else ARROW_COLOR
                            arrow = (arrow_start_sq, end_sq, color)
                            if arrow in arrows:
                                arrows.remove(arrow)
                            else:
                                arrows.append(arrow)
                        arrow_start_sq = None
                        arrow_preview  = None

                    elif event.button == 1:
                        if dragger.dragging:
                            dragger.update_mouse(event.pos)
                            released_row = dragger.mouseY // SQSIZE
                            released_col = dragger.mouseX // SQSIZE
                            if flipped:
                                released_row = 7 - released_row
                                released_col = 7 - released_col
                            if 0 <= released_row < ROWS and 0 <= released_col < COLS:
                                initial = Square(dragger.initial_row, dragger.initial_col)
                                final   = Square(released_row, released_col)
                                move    = Move(initial, final)
                                if board.valid_move(dragger.piece, move):
                                    from engine.bot import _move_to_san
                                    from piece import Pawn as PawnPiece
                                    san = _move_to_san(board, dragger.piece, move)
                                    if vs_bot:
                                        bot.record_move(san)
                                    move_list.append(san)
                                    panel_scroll = 9999
                                    is_ep = (isinstance(dragger.piece, PawnPiece) and
                                             released_col != dragger.initial_col and
                                             board.squares[released_row][released_col].isempty())
                                    captured = board.squares[released_row][released_col].has_piece() or is_ep
                                    board.move(dragger.piece, move, game)
                                    board.set_true_en_passant(dragger.piece)
                                    board.record_position()
                                    game.play_sound(captured)
                                    game.next_turn()
                                    if not game_over:
                                        r = check_game_over(board, game.next_player)
                                        if r: game_over = r
                                    if vs_bot:
                                        bot_needs_recompute[0] = True
                        dragger.undrag_piece()

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t:
                        game.change_theme()
                    if event.key == pygame.K_s:
                        game.change_skin()
                    if event.key == pygame.K_f:
                        flipped = not flipped

                    if draw_offer_pending:
                        if event.key == pygame.K_y:
                            draw_offer_pending = False
                            game_over = 'draw'
                        elif event.key == pygame.K_n:
                            draw_offer_pending = False

                    elif event.key == pygame.K_n:
                        vs_bot, player_color, difficulty = self._run_menu(screen)
                        if vs_bot:
                            bot_color = "black" if player_color == "white" else "white"
                            bot = Bot(bot_color, difficulty=difficulty)
                        else:
                            bot_color = None
                            bot = None
                        game.reset()
                        game    = self.game
                        board   = self.game.board
                        dragger = self.game.dragger
                        move_list.clear()
                        panel_scroll       = 0
                        copy_flash         = 0
                        flipped            = False
                        game_over          = None
                        draw_offer_pending = False
                        arrows.clear()
                        bot_precompute[0]     = None
                        bot_precomputing[0]   = False
                        bot_needs_recompute[0] = True
                        if vs_bot and game.next_player == bot_color:
                            bot_needs_recompute[0] = True

                elif event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            pygame.display.update()


if __name__ == "__main__":
    main = Main()
    main.mainloop()