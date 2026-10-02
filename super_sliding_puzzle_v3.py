import datetime
import heapq
import json
import math
import os
import random
import time
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import winsound
except ImportError:
    winsound = None

MODES = {
    "3x3 Classic (8 tiles)": (3, 1),
    "3x3 Two Blanks (7 tiles)": (3, 2),
    "4x4 Big (15 tiles)": (4, 1),
}
LEVELS = {"Easy": 12, "Medium": 40, "Hard": 150}
LIMITS = ["No limit", "Relaxed (3x par)", "Normal (2x par)", "Tight (1.5x par)", "Custom"]
MULTIPLIER = {"Relaxed (3x par)": 3, "Normal (2x par)": 2, "Tight (1.5x par)": 1.5}

THEMES = {
    "Neon Night": {"bg": "#12121f", "slot": "#1e1e36", "fg": "#ffffff", "accent": "#6c5ce7",
                   "tiles": ["#ff4757", "#ffa502", "#ffdd59", "#2ed573",
                             "#18dcff", "#3d9bff", "#a55eea", "#ff6bcb"]},
    "Sunset": {"bg": "#2d142c", "slot": "#451b3f", "fg": "#fff3e0", "accent": "#d63031",
               "tiles": ["#ff7675", "#fab1a0", "#fdcb6e", "#e17055",
                         "#ff9f43", "#ee5a24", "#c44569", "#f8a5c2"]},
    "Ocean": {"bg": "#0b2545", "slot": "#13315c", "fg": "#e8f4ff", "accent": "#0984e3",
              "tiles": ["#00cec9", "#0abde3", "#48dbfb", "#1dd1a1",
                        "#54a0ff", "#5f27cd", "#00b894", "#74b9ff"]},
    "Candy": {"bg": "#fff0f6", "slot": "#f3d6e4", "fg": "#5a2a4a", "accent": "#e84393",
              "tiles": ["#ff6b81", "#ff9ff3", "#feca57", "#1dd1a1",
                        "#48dbfb", "#a29bfe", "#fd79a8", "#55efc4"]},
}

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "super_puzzle_data.json")
BOARD_SIZE = 324
GOLD = "#ffd700"
RED = "#ff4757"
GREEN = "#2ed573"
ORANGE = "#ffa502"


# for every square, the squares touching it
def get_neighbours(n):
    result = []
    for i in range(n * n):
        row, col = divmod(i, n)
        near = []
        if row > 0:
            near.append(i - n)
        if row < n - 1:
            near.append(i + n)
        if col > 0:
            near.append(i - 1)
        if col < n - 1:
            near.append(i + 1)
        result.append(near)
    return result


def legal_moves(board, neighbours):
    moves = []
    for blank in range(len(board)):
        if board[blank] != 0:
            continue
        for tile in neighbours[blank]:
            if board[tile] != 0:
                moves.append((tile, blank))
    return moves


# shuffle with random legal moves so it is always solvable
def scramble(goal, n, steps, rng):
    neighbours = get_neighbours(n)
    while True:
        board = goal[:]
        last = None
        for _ in range(steps):
            moves = legal_moves(board, neighbours)
            if last:
                moves = [m for m in moves if m != (last[1], last[0])]
            src, dst = rng.choice(moves)
            board[dst] = board[src]
            board[src] = 0
            last = (src, dst)
        if board != goal:
            return board


def manhattan(board, goal, n):
    where = {v: i for i, v in enumerate(goal) if v}
    total = 0
    for i, v in enumerate(board):
        if v:
            total += abs(i // n - where[v] // n) + abs(i % n - where[v] % n)
    return total


# A* search, used for par, hints and the robot
def solve(start, goal, n, weight=1.0, max_nodes=100000):
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return []
    neighbours = get_neighbours(n)
    where = {v: i for i, v in enumerate(goal) if v}
    dist = {}
    for v, g in where.items():
        dist[v] = [abs(i // n - g // n) + abs(i % n - g % n) for i in range(n * n)]

    h0 = sum(dist[v][i] for i, v in enumerate(start) if v)
    tie = 0
    heap = [(weight * h0, tie, 0, h0, start)]
    best = {start: 0}
    parent = {start: None}
    expanded = 0

    while heap:
        _, _, g, h, state = heapq.heappop(heap)
        if state == goal:
            path = []
            while parent[state] is not None:
                state, move = parent[state]
                path.append(move)
            return path[::-1]
        if g > best[state]:
            continue
        expanded += 1
        if expanded > max_nodes:
            return None
        for blank in range(n * n):
            if state[blank] != 0:
                continue
            for tile in neighbours[blank]:
                v = state[tile]
                if v == 0:
                    continue
                nxt = list(state)
                nxt[blank], nxt[tile] = v, 0
                nxt = tuple(nxt)
                if g + 1 < best.get(nxt, 10 ** 9):
                    best[nxt] = g + 1
                    parent[nxt] = (state, (tile, blank))
                    nh = h + dist[v][blank] - dist[v][tile]
                    tie += 1
                    heapq.heappush(heap, (g + 1 + weight * nh, tie, g + 1, nh, nxt))
    return None


# move limit is based on par unless the player picks their own
def get_limit(choice, custom, par):
    if choice == "No limit":
        return None
    if choice == "Custom":
        return max(1, int(custom))
    return max(par + 3, math.ceil(par * MULTIPLIER[choice]))


def fmt_time(seconds):
    seconds = int(seconds)
    return "%02d:%02d" % (seconds // 60, seconds % 60)


def star_points(cx, cy, r):
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = r if i % 2 == 0 else r * 0.45
        points += [cx + radius * math.cos(angle), cy + radius * math.sin(angle)]
    return points


def load_data():
    data = {"settings": {}, "scores": {}}
    try:
        with open(DATA_FILE) as f:
            saved = json.load(f)
        data["settings"].update(saved.get("settings", {}))
        data["scores"].update(saved.get("scores", {}))
    except (OSError, ValueError):
        pass
    return data


def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


# draws the tiles on a canvas and animates the sliding
class BoardView:
    def __init__(self, canvas, app, show_correct=True):
        self.canvas = canvas
        self.app = app
        self.show_correct = show_correct
        self.n = 3
        self.cell = 100
        self.pad = 8
        self.board = []
        self.goal = []
        self.hint = None
        self.overlay = None
        self.animating = False

    def setup(self, n, size, board, goal):
        self.n = n
        self.cell = size // n
        self.pad = max(4, self.cell // 13)
        self.board = board
        self.goal = goal
        self.hint = None
        self.overlay = None
        self.animating = False
        side = self.side()
        self.canvas.configure(width=side, height=side)

    def side(self):
        return self.n * self.cell + self.pad

    def pos(self, i):
        return self.pad + (i % self.n) * self.cell, self.pad + (i // self.n) * self.cell

    def index_at(self, x, y):
        col = (x - self.pad) // self.cell
        row = (y - self.pad) // self.cell
        if 0 <= row < self.n and 0 <= col < self.n:
            return row * self.n + col
        return None

    def rounded(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def draw(self, moving=None):
        if not self.board:
            return
        c = self.canvas
        theme = self.app.theme
        cell, pad = self.cell, self.pad
        radius = max(4, cell // 8)
        c.delete("all")
        c.configure(bg=theme["bg"])

        for i in range(self.n * self.n):
            x, y = self.pos(i)
            self.rounded(x, y, x + cell - pad, y + cell - pad, radius, fill=theme["slot"], outline="")

        hide_tiles = self.overlay is not None and self.overlay[3]
        for i, v in enumerate(self.board):
            if v == 0 or hide_tiles:
                continue
            x, y = self.pos(i)
            if moving and moving[0] == i:
                dx, dy = self.pos(moving[1])
                x += (dx - x) * moving[2]
                y += (dy - y) * moving[2]
            color = theme["tiles"][(v - 1) % len(theme["tiles"])]
            outline, width = "", 1
            if self.show_correct and self.goal[i] == v:
                outline, width = GOLD, 3
            if self.hint == i:
                outline, width = theme["fg"], 5
            self.rounded(x, y, x + cell - pad, y + cell - pad, radius, fill=color, outline=outline, width=width)
            if cell >= 20:
                c.create_text(x + (cell - pad) / 2, y + (cell - pad) / 2, text=str(v),
                              font=("Arial", max(7, cell // 3), "bold"), fill="#ffffff")

        if self.overlay:
            title, sub, color, _ = self.overlay
            mid = self.side() / 2
            self.rounded(mid - 140, mid - 50, mid + 140, mid + 50, 18, fill=theme["bg"], outline=color, width=3)
            c.create_text(mid, mid - 13, text=title, font=("Arial", 24, "bold"), fill=color)
            c.create_text(mid, mid + 24, text=sub, font=("Arial", 10), fill=theme["fg"])

    def slide(self, src, dst, done=None):
        self.animating = True
        steps = 8

        def step(k):
            if k <= steps:
                self.draw(moving=(src, dst, k / steps))
                self.canvas.after(12, lambda: step(k + 1))
                return
            self.board[dst] = self.board[src]
            self.board[src] = 0
            self.animating = False
            self.draw()
            if done:
                done()

        step(1)


# base class for the three screens
class Page(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.frames = []
        self.labels = []
        self.tinted_labels = []
        self.buttons = []

    def make_frame(self, parent=None):
        f = tk.Frame(parent if parent is not None else self)
        self.frames.append(f)
        return f

    def make_label(self, parent=None, **kw):
        lbl = tk.Label(parent if parent is not None else self, **kw)
        self.labels.append(lbl)
        return lbl

    def make_tinted(self, parent=None, **kw):
        # only the background follows the theme, text colour is set by hand
        lbl = tk.Label(parent if parent is not None else self, **kw)
        self.tinted_labels.append(lbl)
        return lbl

    def make_button(self, parent, text, command, width=10, big=False):
        btn = tk.Button(parent, text=text, command=command, width=width, relief="flat",
                        takefocus=0, cursor="hand2", font=("Arial", 12 if big else 10, "bold"),
                        pady=5 if big else 1)
        self.buttons.append(btn)
        return btn

    def apply_theme(self):
        theme = self.app.theme
        self.configure(bg=theme["bg"])
        for f in self.frames:
            f.configure(bg=theme["bg"])
        for lbl in self.labels:
            lbl.configure(bg=theme["bg"], fg=theme["fg"])
        for lbl in self.tinted_labels:
            lbl.configure(bg=theme["bg"])
        for btn in self.buttons:
            btn.configure(bg=theme["accent"], fg="#ffffff",
                          activebackground=theme["tiles"][0], activeforeground="#ffffff")

    def refresh_toggles(self):
        pass

    def on_show(self):
        pass

    def on_key(self, event):
        pass


# page 1 - menu and settings
class StartPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        saved = app.data["settings"]
        self.player_var = tk.StringVar(value=saved.get("player", "Player"))
        self.mode_var = tk.StringVar(value=saved["mode"] if saved.get("mode") in MODES else list(MODES)[0])
        self.level_var = tk.StringVar(value=saved["difficulty"] if saved.get("difficulty") in LEVELS else "Medium")
        self.limit_var = tk.StringVar(value=saved["limit_choice"] if saved.get("limit_choice") in LIMITS
                                      else "Normal (2x par)")
        self.custom_var = tk.StringVar(value=str(saved.get("custom_limit", 50)))

        self.make_label(self, text="SUPER SLIDING PUZZLE", font=("Arial", 20, "bold")).pack(pady=(14, 0))
        self.make_label(self, text="Slide. Think. Solve.", font=("Arial", 10, "italic")).pack()

        self.logo = tk.Canvas(self, highlightthickness=0)
        self.logo.pack(pady=8)
        self.demo_goal = [1, 2, 3, 4, 5, 6, 7, 8, 0]
        self.demo_board = scramble(self.demo_goal, 3, 30, random)
        self.demo = BoardView(self.logo, app, show_correct=False)
        self.demo.setup(3, 168, self.demo_board, self.demo_goal)
        self.demo_last = None

        form = self.make_frame(self)
        form.pack(pady=2)
        for r, text in enumerate(["Player name", "Game mode", "Difficulty", "Move limit", "Custom max"]):
            self.make_label(form, text=text, font=("Arial", 10, "bold"), anchor="e", width=12).grid(
                row=r, column=0, padx=4, pady=3, sticky="e")
        self.entry = tk.Entry(form, textvariable=self.player_var, width=26, relief="flat", font=("Arial", 11))
        self.entry.grid(row=0, column=1, padx=4, pady=3, sticky="w")
        ttk.Combobox(form, textvariable=self.mode_var, values=list(MODES), state="readonly",
                     width=26).grid(row=1, column=1, padx=4, pady=3, sticky="w")
        ttk.Combobox(form, textvariable=self.level_var, values=list(LEVELS), state="readonly",
                     width=26).grid(row=2, column=1, padx=4, pady=3, sticky="w")
        self.limit_box = ttk.Combobox(form, textvariable=self.limit_var, values=LIMITS,
                                      state="readonly", width=26)
        self.limit_box.grid(row=3, column=1, padx=4, pady=3, sticky="w")
        self.limit_box.bind("<<ComboboxSelected>>", lambda e: self.update_custom())
        self.spin = ttk.Spinbox(form, from_=5, to=500, textvariable=self.custom_var, width=8)
        self.spin.grid(row=4, column=1, padx=4, pady=3, sticky="w")
        self.update_custom()

        self.make_button(self, "PLAY", self.play, width=28, big=True).pack(pady=(10, 4))
        row1 = self.make_frame(self)
        row1.pack(pady=2)
        self.make_button(row1, "Daily Challenge", self.daily, width=14).grid(row=0, column=0, padx=3)
        self.make_button(row1, "High Scores", self.show_scores, width=14).grid(row=0, column=1, padx=3)
        row2 = self.make_frame(self)
        row2.pack(pady=2)
        self.theme_btn = self.make_button(row2, "", app.next_theme, width=14)
        self.theme_btn.grid(row=0, column=0, padx=3)
        self.sound_btn = self.make_button(row2, "", app.toggle_sound, width=14)
        self.sound_btn.grid(row=0, column=1, padx=3)
        row3 = self.make_frame(self)
        row3.pack(pady=2)
        self.make_button(row3, "How to Play", self.how_to_play, width=14).grid(row=0, column=0, padx=3)
        self.make_button(row3, "Quit", app.quit, width=14).grid(row=0, column=1, padx=3)

        self.after(700, self.demo_step)

    def update_custom(self):
        state = "normal" if self.limit_var.get() == "Custom" else "disabled"
        self.spin.configure(state=state)
        self.app.root.focus_set()

    def demo_step(self):
        if self.app.current == "start" and not self.demo.animating:
            moves = legal_moves(self.demo_board, get_neighbours(3))
            if self.demo_last:
                moves = [m for m in moves if m != (self.demo_last[1], self.demo_last[0])]
            self.demo_last = random.choice(moves)
            self.demo.slide(*self.demo_last)
        self.after(650, self.demo_step)

    def read_settings(self, daily=False):
        name = self.player_var.get().strip()[:12] or "Player"
        try:
            custom = max(1, min(999, int(self.custom_var.get())))
        except ValueError:
            custom = 50
        settings = {"player": name, "mode": self.mode_var.get(), "difficulty": self.level_var.get(),
                    "limit_choice": self.limit_var.get(), "custom_limit": custom, "daily": False}
        self.app.data["settings"].update({k: v for k, v in settings.items() if k != "daily"})
        if daily:
            settings.update(mode=list(MODES)[0], difficulty="Medium", limit_choice="Normal (2x par)", daily=True)
        return settings

    def play(self):
        self.app.start_game(self.read_settings())

    def daily(self):
        self.app.start_game(self.read_settings(daily=True))

    def how_to_play(self):
        messagebox.showinfo(
            "How to Play",
            "Slide the numbered tiles into order (1, 2, 3 ... with the blank squares at the end).\n\n"
            "Move with the arrow keys / WASD, or click a tile next to a blank square.\n\n"
            "Pick a move limit on this page. If you run out of moves you have to try again.\n"
            "Par is the best possible number of moves. Finish close to par for 3 stars.\n\n"
            "You get 3 hints per game, plus undo, pause and a robot that can solve it for you "
            "(robot solves are not saved to the leaderboard).\n\n"
            "Daily Challenge gives everyone the same puzzle for today.")

    def show_scores(self):
        theme = self.app.theme
        win = tk.Toplevel(self.app.root)
        win.title("High Scores")
        win.configure(bg=theme["bg"])
        win.resizable(False, False)

        lines = []
        for key in sorted(self.app.data["scores"]):
            lines.append(key.upper())
            for rank, e in enumerate(self.app.data["scores"][key][:3], 1):
                lines.append(" %d. %-12s %3d moves  %s  %s" % (
                    rank, e["name"], e["moves"], fmt_time(e["time"]), "*" * e.get("stars", 0)))
            lines.append("")
        if not lines:
            lines = ["No scores yet. Go play a game!"]

        text = tk.Text(win, width=50, height=20, bg=theme["slot"], fg=theme["fg"],
                       font=("Courier", 10), relief="flat", padx=10, pady=8)
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")
        text.pack(padx=10, pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg=theme["accent"], fg="#ffffff",
                  relief="flat", width=12).pack(pady=(0, 10))

    def apply_theme(self):
        super().apply_theme()
        theme = self.app.theme
        self.entry.configure(bg=theme["slot"], fg=theme["fg"], insertbackground=theme["fg"])
        self.demo.draw()

    def refresh_toggles(self):
        self.theme_btn.configure(text="Theme: " + self.app.theme_name)
        self.sound_btn.configure(text="Sound: ON" if self.app.sound else "Sound: OFF")

    def on_key(self, event):
        if event.keysym == "Return":
            self.play()


# page 2 - the actual puzzle
class GamePage(Page):
    BAR_W = 332
    BAR_H = 18

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.session = 0
        self.settings = None
        self.start_board = None
        self.n = 3
        self.size = 9
        self.neighbours = get_neighbours(3)
        self.board = []
        self.goal = []
        self.par = 10
        self.limit = None
        self.moves = 0
        self.history = []
        self.undos_left = None
        self.hints_left = 3
        self.undos_used = 0
        self.hints_used = 0
        self.running = False
        self.paused = False
        self.finished = False
        self.cheated = False
        self.autoplay = False
        self.was_running = False
        self.elapsed = 0.0
        self.t0 = 0.0
        self.confetti = []

        self.header = self.make_label(self, font=("Arial", 10, "bold"), wraplength=400)
        self.header.pack(pady=(8, 2))

        top = self.make_frame(self)
        top.pack()
        stats = self.make_frame(top)
        stats.grid(row=0, column=0, padx=16)
        self.moves_label = self.make_label(stats, font=("Arial", 14, "bold"), anchor="w", width=16)
        self.time_label = self.make_label(stats, font=("Arial", 14, "bold"), anchor="w", width=16)
        self.par_label = self.make_label(stats, font=("Arial", 11), anchor="w", width=20)
        for lbl in (self.moves_label, self.time_label, self.par_label):
            lbl.pack(anchor="w")
        goal_box = self.make_frame(top)
        goal_box.grid(row=0, column=1, padx=16)
        self.goal_canvas = tk.Canvas(goal_box, highlightthickness=0)
        self.goal_canvas.pack()
        self.make_label(goal_box, text="GOAL", font=("Arial", 8, "bold")).pack()
        self.goal_view = BoardView(self.goal_canvas, app, show_correct=False)

        self.bar = tk.Canvas(self, width=self.BAR_W, height=self.BAR_H, highlightthickness=0)
        self.bar.pack(pady=5)
        self.status = self.make_label(self, font=("Arial", 10, "italic"), wraplength=390, height=2)
        self.status.pack()

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(pady=4)
        self.canvas.bind("<Button-1>", self.on_click)
        self.view = BoardView(self.canvas, app)

        row1 = self.make_frame(self)
        row1.pack(pady=3)
        self.undo_btn = self.make_button(row1, "Undo", self.undo)
        self.hint_btn = self.make_button(row1, "Hint", self.hint)
        self.pause_btn = self.make_button(row1, "Pause", self.toggle_pause)
        self.robot_btn = self.make_button(row1, "Robot", self.toggle_robot)
        for i, btn in enumerate((self.undo_btn, self.hint_btn, self.pause_btn, self.robot_btn)):
            btn.grid(row=0, column=i, padx=3)

        row2 = self.make_frame(self)
        row2.pack(pady=3)
        self.make_button(row2, "Restart", self.restart).grid(row=0, column=0, padx=3)
        self.make_button(row2, "New Puzzle", self.new_puzzle).grid(row=0, column=1, padx=3)
        self.make_button(row2, "Menu", self.to_menu).grid(row=0, column=2, padx=3)
        self.sound_btn = self.make_button(row2, "", app.toggle_sound)
        self.sound_btn.grid(row=0, column=3, padx=3)

        self.tick()

    def start(self, settings, same=False):
        self.session += 1
        self.settings = settings
        self.n, blanks = MODES[settings["mode"]]
        self.size = self.n * self.n
        self.neighbours = get_neighbours(self.n)
        self.goal = list(range(1, self.size - blanks + 1)) + [0] * blanks

        fresh = not same or self.start_board is None or len(self.start_board) != self.size
        if fresh:
            if settings["daily"]:
                rng = random.Random("daily-" + datetime.date.today().isoformat())
            else:
                rng = random
            self.start_board = scramble(self.goal, self.n, LEVELS[settings["difficulty"]], rng)
        self.board = self.start_board[:]
        self.view.setup(self.n, BOARD_SIZE, self.board, self.goal)
        self.goal_view.setup(self.n, 72, self.goal[:], self.goal)

        if fresh:
            self.set_status("Calculating par...")
            self.app.root.update_idletasks()
            path = self.run_solver()
            if path:
                self.par = len(path)
            else:
                self.par = int(manhattan(self.board, self.goal, self.n) * 1.6) + 4
        self.limit = get_limit(settings["limit_choice"], settings["custom_limit"], self.par)

        self.moves = 0
        self.history = []
        self.undos_left = 3 if self.limit else None
        self.hints_left = 3
        self.undos_used = 0
        self.hints_used = 0
        self.running = False
        self.paused = False
        self.finished = False
        self.cheated = False
        self.autoplay = False
        self.was_running = False
        self.elapsed = 0.0

        if settings["daily"]:
            title = "Daily Challenge"
        else:
            title = "%s - %s" % (settings["mode"], settings["difficulty"])
        self.header.configure(text="%s  |  %s" % (settings["player"], title))
        if self.limit:
            self.set_status("Reach the goal within %d moves. Par is %d. Good luck!" % (self.limit, self.par))
        else:
            self.set_status("No move limit. Par is %d. Your first move starts the clock." % self.par)
        self.update_stats()
        self.view.draw()
        self.goal_view.draw()

    def restart(self):
        if self.settings:
            self.start(self.settings, same=True)

    def new_puzzle(self):
        if self.settings:
            self.start(self.settings, same=bool(self.settings["daily"]))

    def to_menu(self):
        self.session += 1
        self.autoplay = False
        self.app.show("start")

    def can_act(self):
        return not (self.view.animating or self.finished or self.paused or self.autoplay)

    # src is the tile, dst is the blank it slides into
    def try_move(self, src, dst, auto=False, done=None):
        if self.view.animating or self.finished or self.paused:
            return
        if self.autoplay and not auto:
            return
        session = self.session
        self.view.hint = None
        if not self.running:
            self.running = True
            self.t0 = time.time() - self.elapsed
        self.history.append(self.board[:])
        self.app.beep(700, 15)

        def after_slide():
            if session != self.session:
                return
            self.moves += 1
            self.update_stats()
            if self.board == self.goal:
                self.finish("win")
            elif self.limit and self.moves >= self.limit:
                self.finish("lose")
            else:
                left = self.limit - self.moves if self.limit else None
                if left is not None and left <= 5 and not auto:
                    self.set_status("Only %d moves left!" % left)
                if done:
                    done()

        self.view.slide(src, dst, after_slide)

    # for arrow keys, find the tile that has to slide this way
    def move_dir(self, drow, dcol):
        for blank in range(self.size):
            if self.board[blank] != 0:
                continue
            row, col = divmod(blank, self.n)
            r, c = row - drow, col - dcol
            if 0 <= r < self.n and 0 <= c < self.n and self.board[r * self.n + c] != 0:
                self.try_move(r * self.n + c, blank)
                return

    def on_click(self, event):
        tile = self.view.index_at(event.x, event.y)
        if tile is None or self.board[tile] == 0:
            return
        for other in self.neighbours[tile]:
            if self.board[other] == 0:
                self.try_move(tile, other)
                return

    def on_key(self, event):
        key = event.keysym.lower()
        directions = {"up": (-1, 0), "w": (-1, 0), "down": (1, 0), "s": (1, 0),
                      "left": (0, -1), "a": (0, -1), "right": (0, 1), "d": (0, 1)}
        if key in directions:
            self.move_dir(*directions[key])
        elif key == "z":
            self.undo()
        elif key == "h":
            self.hint()
        elif key == "space":
            self.toggle_pause()
        elif key == "p":
            self.toggle_robot()
        elif key == "r":
            self.restart()
        elif key == "n":
            self.new_puzzle()
        elif key == "t":
            self.app.next_theme()
        elif key == "m":
            self.app.toggle_sound()
        elif key == "escape":
            self.to_menu()

    def run_solver(self):
        if self.n == 3:
            return solve(self.board, self.goal, self.n, 1.0, 200000)
        return solve(self.board, self.goal, self.n, 3.0, 80000)

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
        tile = path[0][0]
        self.view.hint = tile
        msg = "Hint: slide tile %d. About %d moves to go." % (self.board[tile], len(path))
        if self.limit and self.n == 3 and len(path) > self.limit - self.moves:
            msg += " Warning: not enough moves left to finish!"
        self.set_status(msg)
        self.update_stats()
        self.view.draw()

    def toggle_robot(self):
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
            self.set_status("Robot needs %d moves but only %d are left!" % (len(path), self.limit - self.moves))
            return
        self.cheated = True
        self.autoplay = True
        self.view.hint = None
        self.set_status("Robot is solving it in %d moves... (no score saved)" % len(path))
        self.update_stats()
        self.play_path(path, self.session)

    # robot plays the solution one move at a time
    def play_path(self, path, session):
        if session != self.session or not self.autoplay or not path or self.finished:
            self.autoplay = False
            self.update_stats()
            return
        src, dst = path.pop(0)
        self.try_move(src, dst, auto=True,
                      done=lambda: self.after(100, lambda: self.play_path(path, session)))

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

    def finish(self, outcome):
        session = self.session
        if self.running:
            self.elapsed = time.time() - self.t0
        self.running = False
        self.finished = True
        self.autoplay = False
        if outcome == "win" and self.cheated:
            outcome = "robot"
        self.update_stats()

        result = {"outcome": outcome, "moves": self.moves, "limit": self.limit, "par": self.par,
                  "time": self.elapsed, "hints": self.hints_used, "undos": self.undos_used,
                  "name": self.settings["player"], "key": self.score_key(), "stars": 0, "rank": None}

        if outcome == "win":
            # stars depend on how close the player got to par
            if self.moves <= self.par * 1.25 + 2:
                result["stars"] = 3
            elif self.moves <= self.par * 2:
                result["stars"] = 2
            else:
                result["stars"] = 1
            result["rank"], result["entry"] = self.app.add_score(result)
            self.view.overlay = ("SOLVED!", "%d moves in %s" % (self.moves, fmt_time(self.elapsed)), GOLD, False)
            self.set_status("You did it!")
            self.view.draw()
            self.start_confetti(session)
            for freq, ms in ((523, 110), (659, 110), (784, 220)):
                self.app.beep(freq, ms)
            delay = 1800
        elif outcome == "robot":
            self.view.overlay = ("SOLVED!", "by the robot", GOLD, False)
            self.set_status("The robot finished the puzzle.")
            self.view.draw()
            delay = 1400
        else:
            self.view.overlay = ("OUT OF MOVES!", "All %d moves used" % self.limit, RED, False)
            self.set_status("Game over. You ran out of moves!")
            self.view.draw()
            for freq, ms in ((440, 150), (350, 150), (260, 300)):
                self.app.beep(freq, ms)
            delay = 1500

        self.after(delay, lambda: self.show_result(session, result))

    def show_result(self, session, result):
        if session == self.session and self.app.current == "game":
            self.app.show_result(result)

    def score_key(self):
        if self.settings["daily"]:
            return "Daily Challenge " + datetime.date.today().isoformat()
        return "%s - %s" % (self.settings["mode"], self.settings["difficulty"])

    def start_confetti(self, session):
        side = self.view.side()
        colors = self.app.theme["tiles"] + [GOLD]
        self.confetti = []
        for _ in range(80):
            self.confetti.append([random.uniform(0, side), random.uniform(-side, 0),
                                  random.uniform(-1.5, 1.5), random.uniform(2, 5),
                                  random.choice(colors), random.randint(4, 8)])
        self.confetti_frame(0, session)

    def confetti_frame(self, frame, session):
        self.canvas.delete("confetti")
        if session != self.session or frame > 55:
            return
        for p in self.confetti:
            p[0] += p[2]
            p[1] += p[3]
            self.canvas.create_rectangle(p[0], p[1], p[0] + p[5], p[1] + p[5],
                                         fill=p[4], outline="", tags="confetti")
        self.after(30, lambda: self.confetti_frame(frame + 1, session))

    def set_status(self, text):
        self.status.configure(text=text)

    def tick(self):
        if self.running:
            self.elapsed = time.time() - self.t0
            self.time_label.configure(text="Time: " + fmt_time(self.elapsed))
        self.after(200, self.tick)

    def update_stats(self):
        if self.limit:
            self.moves_label.configure(text="Moves: %d / %d" % (self.moves, self.limit))
        else:
            self.moves_label.configure(text="Moves: %d" % self.moves)
        self.time_label.configure(text="Time: " + fmt_time(self.elapsed))
        self.par_label.configure(text="Par: %d moves" % self.par)
        if self.undos_left is None:
            self.undo_btn.configure(text="Undo")
        else:
            self.undo_btn.configure(text="Undo (%d)" % self.undos_left)
        self.hint_btn.configure(text="Hint (%d)" % self.hints_left)
        self.pause_btn.configure(text="Resume" if self.paused else "Pause")
        self.robot_btn.configure(text="Stop" if self.autoplay else "Robot")
        self.draw_bar()

    def draw_bar(self):
        c = self.bar
        theme = self.app.theme
        c.delete("all")
        c.configure(bg=theme["bg"])
        w, h = self.BAR_W, self.BAR_H
        c.create_rectangle(0, 0, w, h, fill=theme["slot"], outline="")
        if not self.limit:
            c.create_text(w / 2, h / 2, text="No move limit", font=("Arial", 9, "bold"), fill=theme["fg"])
            return
        left = max(0, self.limit - self.moves)
        ratio = left / self.limit
        if ratio > 0.5:
            color = GREEN
        elif ratio > 0.25:
            color = ORANGE
        else:
            color = RED
        c.create_rectangle(0, 0, w * ratio, h, fill=color, outline="")
        c.create_text(w / 2, h / 2, text="%d moves left" % left, font=("Arial", 9, "bold"), fill=theme["fg"])

    def apply_theme(self):
        super().apply_theme()
        self.view.draw()
        self.goal_view.draw()
        self.draw_bar()

    def refresh_toggles(self):
        self.sound_btn.configure(text="Sound: ON" if self.app.sound else "Sound: OFF")

    def on_show(self):
        self.refresh_toggles()


# page 3 - result, stars and leaderboard
class ResultPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.result = None
        self.stars_shown = 0
        self.job = 0

        self.title_label = self.make_tinted(self, font=("Arial", 24, "bold"))
        self.title_label.pack(pady=(26, 2))
        self.sub_label = self.make_label(self, font=("Arial", 11, "italic"), wraplength=380)
        self.sub_label.pack()
        self.stars = tk.Canvas(self, width=250, height=70, highlightthickness=0)
        self.stars.pack(pady=8)
        self.stats_label = self.make_label(self, font=("Arial", 12), justify="center")
        self.stats_label.pack(pady=4)
        self.badge = self.make_tinted(self, font=("Arial", 12, "bold"), fg=GOLD)
        self.badge.pack(pady=2)
        self.board_title = self.make_label(self, font=("Arial", 10, "bold"), wraplength=390)
        self.board_title.pack(pady=(10, 2))
        self.rows = []
        for _ in range(5):
            row = self.make_tinted(self, font=("Courier", 11), anchor="w", width=40)
            row.pack()
            self.rows.append(row)

        buttons = self.make_frame(self)
        buttons.pack(pady=(18, 4))
        self.make_button(buttons, "Try Again (R)", app.retry, width=15, big=True).grid(row=0, column=0, padx=4, pady=3)
        self.make_button(buttons, "New Puzzle (N)", app.new_from_result, width=15, big=True).grid(
            row=0, column=1, padx=4, pady=3)
        self.make_button(buttons, "Main Menu (M)", lambda: app.show("start"), width=15, big=True).grid(
            row=1, column=0, padx=4, pady=3)
        self.make_button(buttons, "Quit (Q)", app.quit, width=15, big=True).grid(row=1, column=1, padx=4, pady=3)

    def show(self, result):
        self.result = result
        theme = self.app.theme
        outcome = result["outcome"]

        if outcome == "win":
            self.title_label.configure(text="PUZZLE SOLVED!", fg=GOLD)
            messages = {3: "Flawless! A near-perfect solve.", 2: "Nice work!",
                        1: "Solved! Try for fewer moves next time."}
            self.sub_label.configure(text=messages[result["stars"]])
        elif outcome == "robot":
            self.title_label.configure(text="ROBOT SOLVED IT", fg=theme["tiles"][5])
            self.sub_label.configure(text="No score saved. Try solving it yourself next!")
        else:
            self.title_label.configure(text="OUT OF MOVES!", fg=RED)
            self.sub_label.configure(text="You used all %d moves. Press Try Again to restart this "
                                          "same puzzle, or start a new one." % result["limit"])

        limit_text = " / %d" % result["limit"] if result["limit"] else ""
        self.stats_label.configure(text="Moves: %d%s     Par: %d\nTime: %s\nHints used: %d     Undos used: %d" % (
            result["moves"], limit_text, result["par"], fmt_time(result["time"]),
            result["hints"], result["undos"]))

        badge = ""
        rank = result["rank"]
        if outcome == "win" and rank == 1:
            badge = "NEW HIGH SCORE!"
        elif outcome == "win" and rank and rank <= 5:
            badge = "You made the Top 5  (#%d)" % rank
        self.badge.configure(text=badge)

        scores = self.app.data["scores"].get(result["key"], [])
        self.board_title.configure(text="TOP 5  -  " + result["key"])
        for i, row in enumerate(self.rows):
            if i < len(scores):
                e = scores[i]
                mine = outcome == "win" and result.get("entry") is e
                row.configure(text=" %d. %-12s %3d moves  %s  %-3s" % (
                    i + 1, e["name"], e["moves"], fmt_time(e["time"]), "*" * e.get("stars", 0)),
                    fg=GOLD if mine else theme["fg"])
            else:
                row.configure(text=" %d. ---" % (i + 1), fg=theme["fg"])

        self.job += 1
        self.stars_shown = 0
        self.draw_stars()
        if outcome == "win":
            self.after(400, lambda: self.reveal_stars(self.job))

    def reveal_stars(self, job):
        if job != self.job or self.app.current != "result":
            return
        if self.stars_shown < self.result["stars"]:
            self.stars_shown += 1
            self.app.beep(500 + 120 * self.stars_shown, 80)
            self.draw_stars()
            self.after(450, lambda: self.reveal_stars(job))

    def draw_stars(self):
        c = self.stars
        theme = self.app.theme
        c.delete("all")
        c.configure(bg=theme["bg"])
        for i in range(3):
            filled = i < self.stars_shown
            c.create_polygon(star_points(45 + i * 80, 37, 30),
                             fill=GOLD if filled else theme["slot"],
                             outline=GOLD if filled else theme["fg"], width=2)

    def apply_theme(self):
        super().apply_theme()
        if self.result:
            self.show(self.result)
        else:
            self.draw_stars()

    def on_key(self, event):
        key = event.keysym.lower()
        if key == "r":
            self.app.retry()
        elif key == "n":
            self.app.new_from_result()
        elif key in ("m", "escape"):
            self.app.show("start")
        elif key == "q":
            self.app.quit()
        elif key == "t":
            self.app.next_theme()


class App:
    def __init__(self, root):
        self.root = root
        root.title("Super Sliding Puzzle")
        root.geometry("490x650")
        root.resizable(False, False)

        self.data = load_data()
        self.theme_names = list(THEMES)
        saved_theme = self.data["settings"].get("theme")
        self.theme_index = self.theme_names.index(saved_theme) if saved_theme in THEMES else 0
        self.sound = bool(self.data["settings"].get("sound", False))
        self.current = "start"

        container = tk.Frame(root)
        container.pack(fill="both", expand=True)
        self.pages = {"start": StartPage(container, self),
                      "game": GamePage(container, self),
                      "result": ResultPage(container, self)}
        for page in self.pages.values():
            page.place(x=0, y=0, relwidth=1, relheight=1)
            page.apply_theme()
            page.refresh_toggles()

        root.bind("<Key>", lambda e: self.pages[self.current].on_key(e))
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.show("start")

    @property
    def theme(self):
        return THEMES[self.theme_names[self.theme_index]]

    @property
    def theme_name(self):
        return self.theme_names[self.theme_index]

    def show(self, name):
        self.current = name
        self.pages[name].on_show()
        self.pages[name].tkraise()
        self.root.focus_set()

    def start_game(self, settings):
        save_data(self.data)
        self.pages["game"].start(settings)
        self.show("game")

    def show_result(self, result):
        self.pages["result"].show(result)
        self.show("result")

    def retry(self):
        self.pages["game"].restart()
        self.show("game")

    def new_from_result(self):
        self.pages["game"].new_puzzle()
        self.show("game")

    # keep only the top 10 for each mode, fewest moves first
    def add_score(self, result):
        entry = {"name": result["name"], "moves": result["moves"], "time": round(result["time"], 1),
                 "stars": result["stars"], "date": datetime.date.today().isoformat()}
        board = self.data["scores"].setdefault(result["key"], [])
        board.append(entry)
        board.sort(key=lambda e: (e["moves"], e["time"]))
        del board[10:]
        save_data(self.data)
        rank = None
        for i, e in enumerate(board):
            if e is entry:
                rank = i + 1
        return rank, entry

    def next_theme(self):
        self.theme_index = (self.theme_index + 1) % len(self.theme_names)
        self.data["settings"]["theme"] = self.theme_name
        for page in self.pages.values():
            page.apply_theme()
            page.refresh_toggles()

    def toggle_sound(self):
        self.sound = not self.sound
        self.data["settings"]["sound"] = self.sound
        for page in self.pages.values():
            page.refresh_toggles()
        self.beep(880, 60)

    def beep(self, freq, ms):
        if self.sound and winsound:
            try:
                winsound.Beep(freq, ms)
            except RuntimeError:
                pass

    def quit(self):
        save_data(self.data)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
