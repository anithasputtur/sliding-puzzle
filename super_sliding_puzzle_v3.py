"""
SUPER SLIDING PUZZLE v3  (tkinter - no extra installs needed)

THREE PAGES
  1. Start page  : animated logo, player name, mode, difficulty, MAX MOVES option,
                   Daily Challenge, High Scores, How to Play
  2. Game page   : the puzzle, moves-left bar, timer, goal preview, undo / hint / pause / robot
  3. Result page : stars rating, stats, leaderboard, and RETRY / NEW PUZZLE / MENU buttons
                   (if you run out of moves you get a "Try Again" screen)

FEATURES
  * Modes: 3x3 Classic (8 tiles), 3x3 Two Blanks (7 tiles + 2 blanks), 4x4 Big (15 tiles)
  * Max-moves limit: based on "par" (the best possible solution) or your own number
  * Par display, 1-3 star rating, top-5 leaderboard saved on your computer
  * Daily Challenge: the same puzzle for everyone on the same date
  * Limited hints (3) and, in limit mode, limited undos (3)
  * Pause, goal preview, robot solver (A* search), 4 themes, confetti, optional sound (Windows)

KEYS (game page)
  Arrows / WASD slide | Z undo | H hint | Space pause | P robot | R restart | N new | T theme | M sound | Esc menu
"""
import datetime
import heapq
import itertools
import json
import math
import os
import random
import time
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import winsound          # Windows only
except ImportError:
    winsound = None

# ------------------------------------------------------------------ settings
MODES = {                    # name -> (grid size, number of blank squares)
    "3x3 Classic (8 tiles)": (3, 1),
    "3x3 Two Blanks (7 tiles)": (3, 2),
    "4x4 Big (15 tiles)": (4, 1),
}
DIFFICULTY = {"Easy": 12, "Medium": 40, "Hard": 150}          # scramble moves
LIMIT_CHOICES = ["No limit", "Relaxed (3x par)", "Normal (2x par)", "Tight (1.5x par)", "Custom"]
LIMIT_MULT = {"Relaxed (3x par)": 3, "Normal (2x par)": 2, "Tight (1.5x par)": 1.5}

THEMES = {
    "Neon Night": dict(bg="#12121f", slot="#1e1e36", fg="#ffffff", accent="#6c5ce7",
                       tiles=["#ff4757", "#ffa502", "#ffdd59", "#2ed573",
                              "#18dcff", "#3d9bff", "#a55eea", "#ff6bcb"]),
    "Sunset": dict(bg="#2d142c", slot="#451b3f", fg="#fff3e0", accent="#d63031",
                   tiles=["#ff7675", "#fab1a0", "#fdcb6e", "#e17055",
                          "#ff9f43", "#ee5a24", "#c44569", "#f8a5c2"]),
    "Ocean": dict(bg="#0b2545", slot="#13315c", fg="#e8f4ff", accent="#0984e3",
                  tiles=["#00cec9", "#0abde3", "#48dbfb", "#1dd1a1",
                         "#54a0ff", "#5f27cd", "#00b894", "#74b9ff"]),
    "Candy": dict(bg="#fff0f6", slot="#f3d6e4", fg="#5a2a4a", accent="#e84393",
                  tiles=["#ff6b81", "#ff9ff3", "#feca57", "#1dd1a1",
                         "#48dbfb", "#a29bfe", "#fd79a8", "#55efc4"]),
}

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "super_puzzle_data.json")
BOARD_PX = 324
GOLD = "#ffd700"
RED = "#ff4757"
GREEN = "#2ed573"
ORANGE = "#ffa502"


# ------------------------------------------------------------------ helpers
def build_adj(n):
    adj = []
    for i in range(n * n):
        r, c = divmod(i, n)
        nb = []
        if r > 0: nb.append(i - n)
        if r < n - 1: nb.append(i + n)
        if c > 0: nb.append(i - 1)
        if c < n - 1: nb.append(i + 1)
        adj.append(nb)
    return adj


def legal_moves(board, adj):
    """All (from_index, to_index): the tile at from_index can slide into the blank at to_index."""
    return [(a, b) for b in range(len(board)) if board[b] == 0 for a in adj[b] if board[a] != 0]


def scramble(goal, n, steps, rng):
    """Scramble using only legal moves, so the puzzle is always solvable."""
    adj = build_adj(n)
    while True:
        board, last = goal[:], None
        for _ in range(steps):
            options = [m for m in legal_moves(board, adj) if last is None or m != (last[1], last[0])]
            a, b = rng.choice(options)
            board[b], board[a] = board[a], 0
            last = (a, b)
        if board != goal:
            return board


def manhattan(board, goal, n):
    pos = {v: i for i, v in enumerate(goal) if v}
    return sum(abs(i // n - pos[v] // n) + abs(i % n - pos[v] % n) for i, v in enumerate(board) if v)


def solve_puzzle(start, goal, n, weight=1.0, limit=100000):
    """A* search. Returns a list of (from_index, to_index) tile moves, or None."""
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return []
    size = n * n
    adj = build_adj(n)
    goal_pos = {v: i for i, v in enumerate(goal) if v}
    table = {v: [abs(i // n - g // n) + abs(i % n - g % n) for i in range(size)]
             for v, g in goal_pos.items()}
    h0 = sum(table[v][i] for i, v in enumerate(start) if v)
    counter = itertools.count()
    heap = [(weight * h0, next(counter), 0, h0, start)]
    best_g = {start: 0}
    parent = {start: None}
    expanded = 0
    while heap:
        _, _, g, h, state = heapq.heappop(heap)
        if state == goal:
            path = []
            while parent[state] is not None:
                state, move = parent[state]
                path.append(move)
            path.reverse()
            return path
        if g > best_g[state]:
            continue
        expanded += 1
        if expanded > limit:
            return None
        for b in range(size):
            if state[b] != 0:
                continue
            for a in adj[b]:
                v = state[a]
                if v == 0:
                    continue
                nxt = list(state)
                nxt[b], nxt[a] = v, 0
                nxt = tuple(nxt)
                ng = g + 1
                if ng < best_g.get(nxt, 1 << 30):
                    best_g[nxt] = ng
                    parent[nxt] = (state, (a, b))
                    nh = h + table[v][b] - table[v][a]
                    heapq.heappush(heap, (ng + weight * nh, next(counter), ng, nh, nxt))
    return None


def compute_limit(choice, custom, par):
    if choice == "No limit":
        return None
    if choice == "Custom":
        return max(1, int(custom))
    return max(par + 3, math.ceil(par * LIMIT_MULT[choice]))


def fmt_time(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def star_points(cx, cy, r):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts += [cx + rad * math.cos(ang), cy + rad * math.sin(ang)]
    return pts


def load_data():
    data = {"settings": {}, "scores": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        data["settings"].update(loaded.get("settings", {}))
        data["scores"].update(loaded.get("scores", {}))
    except Exception:
        pass
    return data


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ------------------------------------------------------------------ board drawing
class BoardView:
    """Draws a sliding-tile board on a canvas and animates tile slides."""

    def __init__(self, canvas, app, show_correct=True):
        self.canvas, self.app, self.show_correct = canvas, app, show_correct
        self.n, self.cell, self.pad = 3, 100, 8
        self.board, self.goal = [], []
        self.hint = None
        self.overlay = None          # (title, subtitle, color, cover_tiles)
        self.animating = False

    def setup(self, n, px, board, goal):
        self.n = n
        self.cell = px // n
        self.pad = max(4, self.cell // 13)
        self.board, self.goal = board, goal
        self.hint, self.overlay, self.animating = None, None, False
        side = n * self.cell + self.pad
        self.canvas.configure(width=side, height=side)

    def side(self):
        return self.n * self.cell + self.pad

    def xy(self, i):
        return self.pad + (i % self.n) * self.cell, self.pad + (i // self.n) * self.cell

    def index_at(self, x, y):
        c, r = (x - self.pad) // self.cell, (y - self.pad) // self.cell
        if 0 <= r < self.n and 0 <= c < self.n:
            return r * self.n + c
        return None

    def round_rect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def draw(self, moving=None):
        if not self.board:
            return
        c, th, cell, pad = self.canvas, self.app.theme, self.cell, self.pad
        rad = max(4, cell // 8)
        c.delete("all")
        c.configure(bg=th["bg"])
        for i in range(self.n * self.n):
            x, y = self.xy(i)
            self.round_rect(x, y, x + cell - pad, y + cell - pad, rad, fill=th["slot"], outline="")
        covered = self.overlay is not None and self.overlay[3]
        for i, v in enumerate(self.board):
            if v == 0 or covered:
                continue
            x, y = self.xy(i)
            if moving and moving[0] == i:
                dx, dy = self.xy(moving[1])
                x += (dx - x) * moving[2]
                y += (dy - y) * moving[2]
            color = th["tiles"][(v - 1) % len(th["tiles"])]
            outline, width = "", 1
            if self.show_correct and self.goal[i] == v:
                outline, width = GOLD, 3
            if self.hint == i:
                outline, width = th["fg"], 5
            self.round_rect(x, y, x + cell - pad, y + cell - pad, rad, fill=color, outline=outline, width=width)
            if cell >= 20:
                c.create_text(x + (cell - pad) / 2, y + (cell - pad) / 2, text=str(v),
                              font=("Arial", max(7, cell // 3), "bold"), fill="#ffffff")
        if self.overlay:
            title, sub, color, _ = self.overlay
            mid = self.side() / 2
            self.round_rect(mid - 140, mid - 50, mid + 140, mid + 50, 18, fill=th["bg"], outline=color, width=3)
            c.create_text(mid, mid - 13, text=title, font=("Arial", 24, "bold"), fill=color)
            c.create_text(mid, mid + 24, text=sub, font=("Arial", 10), fill=th["fg"])

    def slide(self, a, b, done=None, steps=8, delay=12):
        """Animate the tile at index a sliding into the blank at index b."""
        self.animating = True

        def step(k):
            if k <= steps:
                self.draw(moving=(a, b, k / steps))
                self.canvas.after(delay, lambda: step(k + 1))
            else:
                self.board[b], self.board[a] = self.board[a], 0
                self.animating = False
                self.draw()
                if done:
                    done()

        step(1)


# ------------------------------------------------------------------ pages
class Page(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.frames, self.labels, self.bg_labels, self.buttons = [], [], [], []

    def frame(self, parent=None):
        f = tk.Frame(parent if parent is not None else self)
        self.frames.append(f)
        return f

    def label(self, parent=None, **kw):
        lbl = tk.Label(parent if parent is not None else self, **kw)
        self.labels.append(lbl)
        return lbl

    def tinted(self, parent=None, **kw):
        """Label whose text colour is set manually (only the background follows the theme)."""
        lbl = tk.Label(parent if parent is not None else self, **kw)
        self.bg_labels.append(lbl)
        return lbl

    def button(self, parent, text, cmd, width=10, big=False):
        b = tk.Button(parent, text=text, command=cmd, width=width, relief="flat", takefocus=0,
                      cursor="hand2", font=("Arial", 12 if big else 10, "bold"), pady=5 if big else 1)
        self.buttons.append(b)
        return b

    def apply_theme(self):
        th = self.app.theme
        self.configure(bg=th["bg"])
        for f in self.frames:
            f.configure(bg=th["bg"])
        for lbl in self.labels:
            lbl.configure(bg=th["bg"], fg=th["fg"])
        for lbl in self.bg_labels:
            lbl.configure(bg=th["bg"])
        for b in self.buttons:
            b.configure(bg=th["accent"], fg="#ffffff",
                        activebackground=th["tiles"][0], activeforeground="#ffffff")

    def refresh_toggles(self):
        pass

    def on_show(self):
        pass

    def on_key(self, e):
        pass


# ------------------------------------------------------------------ PAGE 1: start
class StartPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        s = app.data["settings"]
        self.player_var = tk.StringVar(value=s.get("player", "Player"))
        self.mode_var = tk.StringVar(value=s["mode"] if s.get("mode") in MODES else list(MODES)[0])
        self.diff_var = tk.StringVar(value=s["difficulty"] if s.get("difficulty") in DIFFICULTY else "Medium")
        self.limit_var = tk.StringVar(value=s["limit_choice"] if s.get("limit_choice") in LIMIT_CHOICES
                                      else "Normal (2x par)")
        self.custom_var = tk.StringVar(value=str(s.get("custom_limit", 50)))

        self.label(self, text="SUPER SLIDING PUZZLE", font=("Arial", 20, "bold")).pack(pady=(14, 0))
        self.label(self, text="Slide. Think. Solve.", font=("Arial", 10, "italic")).pack()

        self.logo = tk.Canvas(self, highlightthickness=0)
        self.logo.pack(pady=8)
        self.demo_goal = list(range(1, 9)) + [0]
        self.demo_board = scramble(self.demo_goal, 3, 30, random)
        self.demo = BoardView(self.logo, app, show_correct=False)
        self.demo.setup(3, 168, self.demo_board, self.demo_goal)
        self.demo_last = None

        grid = self.frame(self)
        grid.pack(pady=2)
        names = ["Player name", "Game mode", "Difficulty", "Move limit", "Custom max"]
        for r, text in enumerate(names):
            self.label(grid, text=text, font=("Arial", 10, "bold"), anchor="e", width=12
                       ).grid(row=r, column=0, padx=4, pady=3, sticky="e")
        self.entry = tk.Entry(grid, textvariable=self.player_var, width=26, relief="flat", font=("Arial", 11))
        self.entry.grid(row=0, column=1, padx=4, pady=3, sticky="w")
        ttk.Combobox(grid, textvariable=self.mode_var, values=list(MODES), state="readonly",
                     width=26).grid(row=1, column=1, padx=4, pady=3, sticky="w")
        ttk.Combobox(grid, textvariable=self.diff_var, values=list(DIFFICULTY), state="readonly",
                     width=26).grid(row=2, column=1, padx=4, pady=3, sticky="w")
        self.limit_cb = ttk.Combobox(grid, textvariable=self.limit_var, values=LIMIT_CHOICES,
                                     state="readonly", width=26)
        self.limit_cb.grid(row=3, column=1, padx=4, pady=3, sticky="w")
        self.limit_cb.bind("<<ComboboxSelected>>", lambda e: self.sync_custom())
        self.spin = ttk.Spinbox(grid, from_=5, to=500, textvariable=self.custom_var, width=8)
        self.spin.grid(row=4, column=1, padx=4, pady=3, sticky="w")
        self.sync_custom()

        self.button(self, "PLAY", self.play, width=28, big=True).pack(pady=(10, 4))
        row = self.frame(self)
        row.pack(pady=2)
        self.button(row, "Daily Challenge", self.daily, width=14).grid(row=0, column=0, padx=3)
        self.button(row, "High Scores", self.show_scores, width=14).grid(row=0, column=1, padx=3)
        row2 = self.frame(self)
        row2.pack(pady=2)
        self.theme_btn = self.button(row2, "", app.next_theme, width=14)
        self.theme_btn.grid(row=0, column=0, padx=3)
        self.sound_btn = self.button(row2, "", app.toggle_sound, width=14)
        self.sound_btn.grid(row=0, column=1, padx=3)
        row3 = self.frame(self)
        row3.pack(pady=2)
        self.button(row3, "How to Play", self.how_to, width=14).grid(row=0, column=0, padx=3)
        self.button(row3, "Quit", app.root.destroy, width=14).grid(row=0, column=1, padx=3)

        self.after(700, self.demo_step)

    def sync_custom(self):
        self.spin.configure(state="normal" if self.limit_var.get() == "Custom" else "disabled")
        self.app.root.focus_set()

    def demo_step(self):
        if self.app.current == "start" and not self.demo.animating:
            adj = build_adj(3)
            options = [m for m in legal_moves(self.demo_board, adj)
                       if self.demo_last is None or m != (self.demo_last[1], self.demo_last[0])]
            a, b = random.choice(options)
            self.demo_last = (a, b)
            self.demo.slide(a, b)
        self.after(650, self.demo_step)

    def read_cfg(self, daily=False):
        name = self.player_var.get().strip()[:12] or "Player"
        try:
            custom = max(1, min(999, int(self.custom_var.get())))
        except ValueError:
            custom = 50
        cfg = dict(player=name, mode=self.mode_var.get(), difficulty=self.diff_var.get(),
                   limit_choice=self.limit_var.get(), custom_limit=custom, daily=False)
        self.app.data["settings"].update(player=name, mode=cfg["mode"], difficulty=cfg["difficulty"],
                                         limit_choice=cfg["limit_choice"], custom_limit=custom)
        if daily:
            cfg.update(mode=list(MODES)[0], difficulty="Medium", limit_choice="Normal (2x par)", daily=True)
        return cfg

    def play(self):
        self.app.start_game(self.read_cfg())

    def daily(self):
        self.app.start_game(self.read_cfg(daily=True))

    def how_to(self):
        messagebox.showinfo(
            "How to Play",
            "GOAL: slide the numbered tiles into order (1, 2, 3 ... with the blank squares at the end).\n\n"
            "MOVE: use the arrow keys / WASD, or click a tile next to a blank square.\n\n"
            "MAX MOVES: pick a move limit on this page. Run out of moves and you must try again!\n"
            "PAR is the best possible number of moves. Beat it closely to earn 3 stars.\n\n"
            "HELP: 3 hints per game, undo, pause, and a robot that can solve it for you "
            "(robot solves are not saved to the leaderboard).\n\n"
            "DAILY CHALLENGE: everyone gets the same puzzle today.")

    def show_scores(self):
        th = self.app.theme
        win = tk.Toplevel(self.app.root)
        win.title("High Scores")
        win.configure(bg=th["bg"])
        win.resizable(False, False)
        lines = []
        scores = self.app.data["scores"]
        for key in sorted(scores):
            lines.append(key.upper())
            for i, e in enumerate(scores[key][:3], 1):
                lines.append(f" {i}. {e['name']:<12} {e['moves']:>3} moves  {fmt_time(e['time'])}  "
                             f"{'*' * e.get('stars', 0)}")
            lines.append("")
        if not lines:
            lines = ["No scores yet. Go play a game!"]
        txt = tk.Text(win, width=50, height=20, bg=th["slot"], fg=th["fg"], font=("Courier", 10),
                      relief="flat", padx=10, pady=8)
        txt.insert("1.0", "\n".join(lines))
        txt.configure(state="disabled")
        txt.pack(padx=10, pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg=th["accent"], fg="#ffffff",
                  relief="flat", width=12).pack(pady=(0, 10))

    def apply_theme(self):
        super().apply_theme()
        th = self.app.theme
        self.entry.configure(bg=th["slot"], fg=th["fg"], insertbackground=th["fg"])
        self.demo.draw()

    def refresh_toggles(self):
        self.theme_btn.configure(text=f"Theme: {self.app.theme_name}")
        self.sound_btn.configure(text="Sound: ON" if self.app.sound else "Sound: OFF")

    def on_key(self, e):
        if e.keysym == "Return":
            self.play()


# ------------------------------------------------------------------ PAGE 2: game
class GamePage(Page):
    BAR_W, BAR_H = 332, 18

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.sid = 0                      # changes whenever a game starts/ends so old timers stop
        self.cfg, self.initial = None, None
        self.n, self.size, self.adj = 3, 9, build_adj(3)
        self.board, self.goal = [], []
        self.par, self.limit = 10, None
        self.moves = 0
        self.history = []
        self.undos_left, self.hints_left = None, 3
        self.undos_used = self.hints_used = 0
        self.running = self.paused = self.finished = self.cheated = self.autoplay = False
        self.was_running = False
        self.elapsed, self.t0 = 0.0, 0.0
        self.outcome = None
        self.parts = []

        self.header = self.label(self, font=("Arial", 10, "bold"), wraplength=400)
        self.header.pack(pady=(8, 2))

        top = self.frame(self)
        top.pack()
        stats = self.frame(top)
        stats.grid(row=0, column=0, padx=16)
        self.moves_lbl = self.label(stats, font=("Arial", 14, "bold"), anchor="w", width=16)
        self.time_lbl = self.label(stats, font=("Arial", 14, "bold"), anchor="w", width=16)
        self.par_lbl = self.label(stats, font=("Arial", 11), anchor="w", width=20)
        for w in (self.moves_lbl, self.time_lbl, self.par_lbl):
            w.pack(anchor="w")
        gbox = self.frame(top)
        gbox.grid(row=0, column=1, padx=16)
        self.goal_canvas = tk.Canvas(gbox, highlightthickness=0)
        self.goal_canvas.pack()
        self.label(gbox, text="GOAL", font=("Arial", 8, "bold")).pack()
        self.goal_view = BoardView(self.goal_canvas, app, show_correct=False)

        self.bar = tk.Canvas(self, width=self.BAR_W, height=self.BAR_H, highlightthickness=0)
        self.bar.pack(pady=5)
        self.status = self.label(self, font=("Arial", 10, "italic"), wraplength=390, height=2)
        self.status.pack()

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(pady=4)
        self.canvas.bind("<Button-1>", self.on_click)
        self.view = BoardView(self.canvas, app)

        row1 = self.frame(self)
        row1.pack(pady=3)
        self.undo_btn = self.button(row1, "Undo", self.undo, width=10)
        self.hint_btn = self.button(row1, "Hint", self.hint, width=10)
        self.pause_btn = self.button(row1, "Pause", self.toggle_pause, width=10)
        self.solve_btn = self.button(row1, "Robot", self.toggle_solve, width=10)
        for i, b in enumerate((self.undo_btn, self.hint_btn, self.pause_btn, self.solve_btn)):
            b.grid(row=0, column=i, padx=3)
        row2 = self.frame(self)
        row2.pack(pady=3)
        self.sound_btn = self.button(row2, "", app.toggle_sound, width=10)
        for i, (t, cmd) in enumerate((("Restart", self.restart), ("New Puzzle", self.new_puzzle),
                                      ("Menu", self.to_menu))):
            self.button(row2, t, cmd, width=10).grid(row=0, column=i, padx=3)
        self.sound_btn.grid(row=0, column=3, padx=3)

        self.tick()

    # ---------------------------------------------------------- starting a game
    def start(self, cfg, same=False):
        self.sid += 1
        self.cfg = cfg
        self.n, blanks = MODES[cfg["mode"]]
        self.size = self.n * self.n
        self.adj = build_adj(self.n)
        self.goal = list(range(1, self.size - blanks + 1)) + [0] * blanks
        need_new = not same or self.initial is None or len(self.initial) != self.size
        if need_new:
            steps = DIFFICULTY[cfg["difficulty"]]
            rng = random.Random("daily-" + datetime.date.today().isoformat()) if cfg["daily"] else random
            self.initial = scramble(self.goal, self.n, steps, rng)
        self.board = self.initial[:]
        self.view.setup(self.n, BOARD_PX, self.board, self.goal)
        self.goal_view.setup(self.n, 72, self.goal[:], self.goal)

        if need_new:
            self.set_status("Calculating par...")
            self.app.root.update_idletasks()
            path = self.run_solver()
            self.par = len(path) if path else int(manhattan(self.board, self.goal, self.n) * 1.6) + 4
        self.limit = compute_limit(cfg["limit_choice"], cfg["custom_limit"], self.par)

        self.moves = 0
        self.history = []
        self.undos_left = 3 if self.limit else None
        self.hints_left = 3
        self.undos_used = self.hints_used = 0
        self.running = self.paused = self.finished = self.cheated = self.autoplay = False
        self.was_running = False
        self.elapsed = 0.0
        self.outcome = None
        label = "Daily Challenge" if cfg["daily"] else f"{cfg['mode']} - {cfg['difficulty']}"
        self.header.configure(text=f"{cfg['player']}  |  {label}")
        if self.limit:
            self.set_status(f"Reach the goal within {self.limit} moves. Par is {self.par}. Good luck!")
        else:
            self.set_status(f"No move limit. Par is {self.par}. Your first move starts the clock.")
        self.update_stats()
        self.view.draw()
        self.goal_view.draw()

    def restart(self):
        if self.cfg:
            self.start(self.cfg, same=True)

    def new_puzzle(self):
        if self.cfg:
            self.start(self.cfg, same=bool(self.cfg["daily"]))

    def to_menu(self):
        self.sid += 1
        self.autoplay = False
        self.app.show("start")

    # ---------------------------------------------------------- moving tiles
    def can_act(self):
        return not (self.view.animating or self.finished or self.paused or self.autoplay)

    def try_move(self, a, b, auto=False, done=None):
        if self.view.animating or self.finished or self.paused or (self.autoplay and not auto):
            return
        sid = self.sid
        self.view.hint = None
        if not self.running:
            self.running = True
            self.t0 = time.time() - self.elapsed
        self.history.append(self.board[:])
        self.app.beep(700, 15)

        def after_slide():
            if sid != self.sid:
                return
            self.moves += 1
            self.update_stats()
            if self.board == self.goal:
                self.finish("win")
            elif self.limit and self.moves >= self.limit:
                self.finish("lose")
            else:
                if self.limit and self.limit - self.moves <= 5 and not auto:
                    self.set_status(f"Only {self.limit - self.moves} moves left!")
                if done:
                    done()

        self.view.slide(a, b, after_slide)

    def move_dir(self, dr, dc):
        for b in range(self.size):
            if self.board[b] != 0:
                continue
            r, c = divmod(b, self.n)
            sr, sc = r - dr, c - dc
            if 0 <= sr < self.n and 0 <= sc < self.n and self.board[sr * self.n + sc] != 0:
                self.try_move(sr * self.n + sc, b)
                return

    def on_click(self, e):
        a = self.view.index_at(e.x, e.y)
        if a is None or self.board[a] == 0:
            return
        for b in self.adj[a]:
            if self.board[b] == 0:
                self.try_move(a, b)
                return

    def on_key(self, e):
        k = e.keysym.lower()
        dirs = {"up": (-1, 0), "w": (-1, 0), "down": (1, 0), "s": (1, 0),
                "left": (0, -1), "a": (0, -1), "right": (0, 1), "d": (0, 1)}
        if k in dirs:
            self.move_dir(*dirs[k])
        elif k == "z": self.undo()
        elif k == "h": self.hint()
        elif k == "space": self.toggle_pause()
        elif k == "p": self.toggle_solve()
        elif k == "r": self.restart()
        elif k == "n": self.new_puzzle()
        elif k == "t": self.app.next_theme()
        elif k == "m": self.app.toggle_sound()
        elif k == "escape": self.to_menu()

    # ---------------------------------------------------------- helpers: undo / hint / robot / pause
    def run_solver(self):
        weight, limit = (1.0, 200000) if self.n == 3 else (3.0, 80000)
        return solve_puzzle(self.board, self.goal, self.n, weight, limit)

    def solve_now(self):
        self.set_status("Thinking...")
        self.app.root.update_idletasks()
        return self.run_solver()

    def undo(self):
        if not self.can_act() or not self.history:
            return
        if self.undos_left is not None and self.undos_left <= 0:
            self.set_status("No undos left in limit mode!")
            return
        self.board[:] = self.history.pop()
        self.moves = len(self.history)
        self.undos_used += 1
        if self.undos_left is not None:
            self.undos_left -= 1
        self.view.hint = None
        self.set_status("Undone!")
        self.update_stats()
        self.view.draw()

    def hint(self):
        if not self.can_act():
            return
        if self.hints_left <= 0:
            self.set_status("No hints left!")
            return
        path = self.solve_now()
        if not path:
            self.set_status("Hmm, too tangled for a hint. Try Undo or Restart.")
            return
        self.hints_left -= 1
        self.hints_used += 1
        a = path[0][0]
        self.view.hint = a
        msg = f"Hint: slide tile {self.board[a]}. About {len(path)} moves to go."
        if self.limit and self.n == 3 and len(path) > self.limit - self.moves:
            msg += " Warning: not enough moves left to finish!"
        self.set_status(msg)
        self.update_stats()
        self.view.draw()

    def toggle_solve(self):
        if self.finished or self.view.animating or self.paused:
            return
        if self.autoplay:
            self.autoplay = False
            self.set_status("Robot stopped. Your turn!")
            self.update_stats()
            return
        path = self.solve_now()
        if not path:
            self.set_status("Too tangled for the robot. Try Undo or Restart.")
            return
        if self.limit and len(path) > self.limit - self.moves:
            self.set_status(f"Robot needs {len(path)} moves but only {self.limit - self.moves} are left!")
            return
        self.cheated = True
        self.autoplay = True
        self.view.hint = None
        self.set_status(f"Robot is solving it in {len(path)} moves... (no score saved)")
        self.update_stats()
        self.run_path(path, self.sid)

    def run_path(self, path, sid):
        if sid != self.sid or not self.autoplay or not path or self.finished:
            self.autoplay = False
            self.update_stats()
            return
        a, b = path.pop(0)
        self.try_move(a, b, auto=True, done=lambda: self.after(100, lambda: self.run_path(path, sid)))

    def toggle_pause(self):
        if self.finished or self.view.animating or self.autoplay:
            return
        if not self.paused:
            self.was_running = self.running
            if self.running:
                self.elapsed = time.time() - self.t0
                self.running = False
            self.paused = True
            self.view.overlay = ("PAUSED", "Press Space to resume", GOLD, True)
        else:
            self.paused = False
            self.view.overlay = None
            if self.was_running:
                self.running = True
                self.t0 = time.time() - self.elapsed
        self.view.draw()
        self.update_stats()

    # ---------------------------------------------------------- finishing
    def finish(self, outcome):
        sid = self.sid
        if self.running:
            self.elapsed = time.time() - self.t0
        self.running = False
        self.finished = True
        self.autoplay = False
        if outcome == "win" and self.cheated:
            outcome = "robot"
        self.outcome = outcome
        self.update_stats()

        res = dict(outcome=outcome, moves=self.moves, limit=self.limit, par=self.par, time=self.elapsed,
                   hints=self.hints_used, undos=self.undos_used, name=self.cfg["player"],
                   key=self.score_key(), stars=0, rank=None)
        if outcome == "win":
            res["stars"] = 3 if self.moves <= self.par * 1.25 + 2 else (2 if self.moves <= self.par * 2 else 1)
            res["rank"], res["entry"] = self.app.add_score(res)
            self.view.overlay = ("SOLVED!", f"{self.moves} moves in {fmt_time(self.elapsed)}", GOLD, False)
            self.set_status("You did it!")
            self.view.draw()
            self.start_confetti(sid)
            for f, d in ((523, 110), (659, 110), (784, 220)):
                self.app.beep(f, d)
            delay = 1800
        elif outcome == "robot":
            self.view.overlay = ("SOLVED!", "by the robot", GOLD, False)
            self.set_status("The robot finished the puzzle.")
            self.view.draw()
            delay = 1400
        else:
            self.view.overlay = ("OUT OF MOVES!", f"All {self.limit} moves used", RED, False)
            self.set_status("Game over. You ran out of moves!")
            self.view.draw()
            for f, d in ((440, 150), (350, 150), (260, 300)):
                self.app.beep(f, d)
            delay = 1500
        self.after(delay, lambda: self.go_result(sid, res))

    def go_result(self, sid, res):
        if sid == self.sid and self.app.current == "game":
            self.app.show_result(res)

    def score_key(self):
        if self.cfg["daily"]:
            return "Daily Challenge " + datetime.date.today().isoformat()
        return f"{self.cfg['mode']} - {self.cfg['difficulty']}"

    def start_confetti(self, sid):
        side = self.view.side()
        colors = self.app.theme["tiles"] + [GOLD]
        self.parts = [[random.uniform(0, side), random.uniform(-side, 0), random.uniform(-1.5, 1.5),
                       random.uniform(2, 5), random.choice(colors), random.randint(4, 8)]
                      for _ in range(80)]
        self.confetti_frame(0, sid)

    def confetti_frame(self, k, sid):
        self.canvas.delete("confetti")
        if sid != self.sid or k > 55:
            return
        for p in self.parts:
            p[0] += p[2]
            p[1] += p[3]
            self.canvas.create_rectangle(p[0], p[1], p[0] + p[5], p[1] + p[5], fill=p[4],
                                         outline="", tags="confetti")
        self.after(30, lambda: self.confetti_frame(k + 1, sid))

    # ---------------------------------------------------------- labels / bar
    def set_status(self, text):
        self.status.configure(text=text)

    def tick(self):
        if self.running:
            self.elapsed = time.time() - self.t0
            self.time_lbl.configure(text=f"Time: {fmt_time(self.elapsed)}")
        self.after(200, self.tick)

    def update_stats(self):
        if self.limit:
            self.moves_lbl.configure(text=f"Moves: {self.moves} / {self.limit}")
        else:
            self.moves_lbl.configure(text=f"Moves: {self.moves}")
        self.time_lbl.configure(text=f"Time: {fmt_time(self.elapsed)}")
        self.par_lbl.configure(text=f"Par: {self.par} moves")
        self.undo_btn.configure(text="Undo" if self.undos_left is None else f"Undo ({self.undos_left})")
        self.hint_btn.configure(text=f"Hint ({self.hints_left})")
        self.pause_btn.configure(text="Resume" if self.paused else "Pause")
        self.solve_btn.configure(text="Stop" if self.autoplay else "Robot")
        self.draw_bar()

    def draw_bar(self):
        c, th = self.bar, self.app.theme
        c.delete("all")
        c.configure(bg=th["bg"])
        w, h = self.BAR_W, self.BAR_H
        c.create_rectangle(0, 0, w, h, fill=th["slot"], outline="")
        if self.limit:
            left = max(0, self.limit - self.moves)
            frac = left / self.limit
            color = GREEN if frac > 0.5 else (ORANGE if frac > 0.25 else RED)
            c.create_rectangle(0, 0, w * frac, h, fill=color, outline="")
            c.create_text(w / 2, h / 2, text=f"{left} moves left", font=("Arial", 9, "bold"), fill=th["fg"])
        else:
            c.create_text(w / 2, h / 2, text="No move limit", font=("Arial", 9, "bold"), fill=th["fg"])

    def apply_theme(self):
        super().apply_theme()
        self.view.draw()
        self.goal_view.draw()
        self.draw_bar()

    def refresh_toggles(self):
        self.sound_btn.configure(text="Sound: ON" if self.app.sound else "Sound: OFF")

    def on_show(self):
        self.refresh_toggles()


# ------------------------------------------------------------------ PAGE 3: result
class ResultPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.res = None
        self.stars_shown = 0
        self.job = 0

        self.title_lbl = self.tinted(self, font=("Arial", 24, "bold"))
        self.title_lbl.pack(pady=(26, 2))
        self.sub_lbl = self.label(self, font=("Arial", 11, "italic"), wraplength=380)
        self.sub_lbl.pack()
        self.stars = tk.Canvas(self, width=250, height=70, highlightthickness=0)
        self.stars.pack(pady=8)
        self.stats_lbl = self.label(self, font=("Arial", 12), justify="center")
        self.stats_lbl.pack(pady=4)
        self.badge = self.tinted(self, font=("Arial", 12, "bold"), fg=GOLD)
        self.badge.pack(pady=2)
        self.board_title = self.label(self, font=("Arial", 10, "bold"), wraplength=390)
        self.board_title.pack(pady=(10, 2))
        self.rows = [self.tinted(self, font=("Courier", 11), anchor="w", width=40) for _ in range(5)]
        for r in self.rows:
            r.pack()

        btns = self.frame(self)
        btns.pack(pady=(18, 4))
        self.retry_btn = self.button(btns, "Try Again (R)", lambda: self.app.retry(), width=15, big=True)
        self.retry_btn.grid(row=0, column=0, padx=4, pady=3)
        self.button(btns, "New Puzzle (N)", lambda: self.app.new_from_result(), width=15, big=True
                    ).grid(row=0, column=1, padx=4, pady=3)
        self.button(btns, "Main Menu (M)", lambda: self.app.show("start"), width=15, big=True
                    ).grid(row=1, column=0, padx=4, pady=3)
        self.button(btns, "Quit (Q)", app.root.destroy, width=15, big=True).grid(row=1, column=1, padx=4, pady=3)

    def show(self, res):
        self.res = res
        th = self.app.theme
        out = res["outcome"]
        if out == "win":
            self.title_lbl.configure(text="PUZZLE SOLVED!", fg=GOLD)
            self.sub_lbl.configure(text={3: "Flawless! A near-perfect solve.", 2: "Nice work!",
                                         1: "Solved! Try for fewer moves next time."}[res["stars"]])
        elif out == "robot":
            self.title_lbl.configure(text="ROBOT SOLVED IT", fg=th["tiles"][5])
            self.sub_lbl.configure(text="No score saved. Try solving it yourself next!")
        else:
            self.title_lbl.configure(text="OUT OF MOVES!", fg=RED)
            self.sub_lbl.configure(text=f"You used all {res['limit']} moves. Press Try Again to restart "
                                        f"this same puzzle, or start a new one.")
        lim = f" / {res['limit']}" if res["limit"] else ""
        self.stats_lbl.configure(text=f"Moves: {res['moves']}{lim}     Par: {res['par']}\n"
                                      f"Time: {fmt_time(res['time'])}\n"
                                      f"Hints used: {res['hints']}     Undos used: {res['undos']}")
        badge = ""
        if out == "win" and res["rank"] == 1:
            badge = "NEW HIGH SCORE!"
        elif out == "win" and res["rank"] and res["rank"] <= 5:
            badge = f"You made the Top 5  (#{res['rank']})"
        self.badge.configure(text=badge)

        scores = self.app.data["scores"].get(res["key"], [])
        self.board_title.configure(text=f"TOP 5  -  {res['key']}")
        for i, row in enumerate(self.rows):
            if i < len(scores):
                e = scores[i]
                mine = out == "win" and res.get("entry") is e
                row.configure(text=f" {i + 1}. {e['name']:<12} {e['moves']:>3} moves  {fmt_time(e['time'])}  "
                                   f"{'*' * e.get('stars', 0):<3}",
                              fg=GOLD if mine else th["fg"])
            else:
                row.configure(text=f" {i + 1}. ---", fg=th["slot"] if th["slot"] != th["bg"] else th["fg"])
        self.job += 1
        self.stars_shown = 0
        self.draw_stars()
        if out == "win":
            self.after(400, lambda: self.reveal(self.job))

    def reveal(self, job):
        if job != self.job or self.app.current != "result":
            return
        if self.stars_shown < self.res["stars"]:
            self.stars_shown += 1
            self.app.beep(500 + 120 * self.stars_shown, 80)
            self.draw_stars()
            self.after(450, lambda: self.reveal(job))

    def draw_stars(self):
        c, th = self.stars, self.app.theme
        c.delete("all")
        c.configure(bg=th["bg"])
        for i in range(3):
            cx = 45 + i * 80
            filled = i < self.stars_shown
            c.create_polygon(star_points(cx, 37, 30), fill=GOLD if filled else th["slot"],
                             outline=GOLD if filled else th["fg"], width=2)

    def apply_theme(self):
        super().apply_theme()
        if self.res:
            self.show(self.res)
        else:
            self.draw_stars()

    def on_key(self, e):
        k = e.keysym.lower()
        if k == "r": self.app.retry()
        elif k == "n": self.app.new_from_result()
        elif k in ("m", "escape"): self.app.show("start")
        elif k == "q": self.app.root.destroy()
        elif k == "t": self.app.next_theme()


# ------------------------------------------------------------------ the app
class App:
    def __init__(self, root):
        self.root = root
        root.title("Super Sliding Puzzle")
        root.geometry("490x650")
        root.resizable(False, False)
        self.data = load_data()
        self.theme_names = list(THEMES)
        saved = self.data["settings"].get("theme")
        self.theme_i = self.theme_names.index(saved) if saved in THEMES else 0
        self.sound = bool(self.data["settings"].get("sound", False))
        self.current = "start"

        container = tk.Frame(root)
        container.pack(fill="both", expand=True)
        self.pages = {"start": StartPage(container, self), "game": GamePage(container, self),
                      "result": ResultPage(container, self)}
        for p in self.pages.values():
            p.place(x=0, y=0, relwidth=1, relheight=1)
        for p in self.pages.values():
            p.apply_theme()
            p.refresh_toggles()
        root.bind("<Key>", lambda e: self.pages[self.current].on_key(e))
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.show("start")

    @property
    def theme(self):
        return THEMES[self.theme_names[self.theme_i]]

    @property
    def theme_name(self):
        return self.theme_names[self.theme_i]

    def show(self, name):
        self.current = name
        page = self.pages[name]
        page.on_show()
        page.tkraise()
        self.root.focus_set()

    def start_game(self, cfg):
        save_data(self.data)
        self.pages["game"].start(cfg)
        self.show("game")

    def show_result(self, res):
        self.pages["result"].show(res)
        self.show("result")

    def retry(self):
        self.pages["game"].restart()
        self.show("game")

    def new_from_result(self):
        self.pages["game"].new_puzzle()
        self.show("game")

    def add_score(self, res):
        entry = dict(name=res["name"], moves=res["moves"], time=round(res["time"], 1),
                     stars=res["stars"], date=datetime.date.today().isoformat())
        board = self.data["scores"].setdefault(res["key"], [])
        board.append(entry)
        board.sort(key=lambda e: (e["moves"], e["time"]))
        del board[10:]
        save_data(self.data)
        rank = next((i + 1 for i, e in enumerate(board) if e is entry), None)
        return rank, entry

    def next_theme(self):
        self.theme_i = (self.theme_i + 1) % len(self.theme_names)
        self.data["settings"]["theme"] = self.theme_name
        for p in self.pages.values():
            p.apply_theme()
            p.refresh_toggles()

    def toggle_sound(self):
        self.sound = not self.sound
        self.data["settings"]["sound"] = self.sound
        for p in self.pages.values():
            p.refresh_toggles()
        self.beep(880, 60)

    def beep(self, freq, ms):
        if self.sound and winsound:
            try:
                winsound.Beep(freq, ms)
            except Exception:
                pass

    def quit(self):
        save_data(self.data)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
