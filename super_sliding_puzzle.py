"""
SUPER SLIDING PUZZLE  (tkinter - no extra installs needed)

Features
  * 3 game modes : 3x3 Classic (8 tiles), 3x3 Two Blanks (7 tiles), 4x4 Big (15 tiles)
  * 3 difficulties: Easy / Medium / Hard (how much the board is scrambled)
  * Smooth sliding animation, move counter and live timer
  * Best time + best moves saved in puzzle_scores.json (per mode & difficulty)
  * Undo, Hint (highlights the next tile to move) and Auto-Solve robot (A* search)
  * 4 colour themes, gold border on tiles that are already in the right place
  * Confetti party when you win, optional sound (Windows)

Controls
  Arrow keys / W A S D : slide a tile Up / Down / Left / Right into a blank square
  Mouse click          : click a tile that is next to a blank
  N new game | Z undo | H hint | P auto-solve (press again to stop) | T theme | M sound
"""
import heapq
import itertools
import json
import os
import random
import time
import tkinter as tk
from tkinter import ttk

try:
    import winsound          # only exists on Windows
except ImportError:
    winsound = None

# ------------------------------------------------------------------ settings
MODES = {                    # name -> (grid size, number of blank squares)
    "3x3 Classic (8 tiles)": (3, 1),
    "3x3 Two Blanks (7 tiles)": (3, 2),
    "4x4 Big (15 tiles)": (4, 1),
}
DIFFICULTY = {"Easy": 12, "Medium": 40, "Hard": 150}   # scramble moves

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

SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzle_scores.json")
BOARD_PX = 330
PAD = 8
GOLD = "#ffd700"


# ------------------------------------------------------------------ helpers
def build_adj(n):
    """For each square index, the list of neighbouring square indices."""
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


def solve_puzzle(start, goal, n, weight=1.0, limit=100000):
    """A* search. Returns a list of (from_index, to_index) tile moves, or None."""
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return []
    size = n * n
    adj = build_adj(n)
    goal_pos = {v: i for i, v in enumerate(goal) if v}
    table = {v: [abs(i // n - g // n) + abs(i % n - g % n) for i in range(size)]
             for v, g in goal_pos.items()}               # Manhattan distance
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


def fmt_time(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


# ------------------------------------------------------------------ the game
class Game:
    def __init__(self, root):
        self.root = root
        root.title("Super Sliding Puzzle")
        root.resizable(False, False)

        self.theme_names = list(THEMES)
        self.theme_i = 0
        self.sound = False
        self.scores = self.load_scores()

        self.animating = False
        self.autoplay = False
        self.hint_tile = None
        self.confetti_job = None
        self.running = False
        self.solved = False
        self.cheated = False
        self.elapsed = 0.0
        self.t0 = 0.0
        self.moves = 0
        self.history = []
        self.n, self.cell = 3, BOARD_PX // 3
        self.board, self.goal, self.adj, self.size = [], [], [], 9

        self.mode_var = tk.StringVar(value=list(MODES)[0])
        self.diff_var = tk.StringVar(value="Medium")
        self.frames, self.labels, self.buttons = [], [], []

        self.build_ui()
        self.new_game()
        self.apply_theme()
        self.tick()

    # ---------------------------------------------------------- UI building
    @property
    def theme(self):
        return THEMES[self.theme_names[self.theme_i]]

    def make_label(self, parent, **kw):
        lbl = tk.Label(parent, **kw)
        self.labels.append(lbl)
        return lbl

    def make_button(self, parent, text, cmd, width=9):
        b = tk.Button(parent, text=text, command=cmd, width=width, relief="flat",
                      font=("Arial", 10, "bold"), takefocus=0, cursor="hand2")
        self.buttons.append(b)
        return b

    def make_frame(self, parent):
        f = tk.Frame(parent)
        self.frames.append(f)
        return f

    def build_ui(self):
        r = self.root
        self.make_label(r, text="SUPER SLIDING PUZZLE", font=("Arial", 18, "bold")).pack(pady=(10, 2))

        stats = self.make_frame(r)
        stats.pack()
        self.moves_lbl = self.make_label(stats, font=("Arial", 12, "bold"), width=11)
        self.time_lbl = self.make_label(stats, font=("Arial", 12, "bold"), width=11)
        self.best_lbl = self.make_label(stats, font=("Arial", 10), width=22)
        self.moves_lbl.grid(row=0, column=0)
        self.time_lbl.grid(row=0, column=1)
        self.best_lbl.grid(row=1, column=0, columnspan=2)

        self.status_lbl = self.make_label(r, font=("Arial", 10, "italic"), wraplength=340, height=2)
        self.status_lbl.pack()

        self.canvas = tk.Canvas(r, highlightthickness=0)
        self.canvas.pack(padx=10, pady=4)
        self.canvas.bind("<Button-1>", self.on_click)

        row1 = self.make_frame(r)
        row1.pack(pady=4)
        self.make_button(row1, "Shuffle (N)", self.new_game).grid(row=0, column=0, padx=3)
        self.make_button(row1, "Undo (Z)", self.undo).grid(row=0, column=1, padx=3)
        self.make_button(row1, "Hint (H)", self.hint).grid(row=0, column=2, padx=3)
        self.solve_btn = self.make_button(row1, "Solve (P)", self.toggle_solve)
        self.solve_btn.grid(row=0, column=3, padx=3)

        row2 = self.make_frame(r)
        row2.pack(pady=4)
        mode_cb = ttk.Combobox(row2, textvariable=self.mode_var, values=list(MODES),
                               state="readonly", width=24)
        diff_cb = ttk.Combobox(row2, textvariable=self.diff_var, values=list(DIFFICULTY),
                               state="readonly", width=8)
        mode_cb.grid(row=0, column=0, padx=3)
        diff_cb.grid(row=0, column=1, padx=3)
        for cb in (mode_cb, diff_cb):
            cb.bind("<<ComboboxSelected>>", self.on_setting_change)

        row3 = self.make_frame(r)
        row3.pack(pady=4)
        self.theme_btn = self.make_button(row3, "", self.next_theme, width=22)
        self.theme_btn.grid(row=0, column=0, padx=3)
        self.sound_btn = self.make_button(row3, "", self.toggle_sound, width=14)
        self.sound_btn.grid(row=0, column=1, padx=3)

        self.make_label(r, font=("Arial", 8), wraplength=340, justify="center",
                        text="Arrows / WASD or click to slide tiles  |  gold border = tile in the right place"
                        ).pack(pady=(4, 10))

        r.bind("<Key>", self.on_key)

    def apply_theme(self):
        th = self.theme
        self.root.configure(bg=th["bg"])
        for f in self.frames:
            f.configure(bg=th["bg"])
        for lbl in self.labels:
            lbl.configure(bg=th["bg"], fg=th["fg"])
        for b in self.buttons:
            b.configure(bg=th["accent"], fg="#ffffff",
                        activebackground=th["tiles"][0], activeforeground="#ffffff")
        self.theme_btn.configure(text=f"Theme: {self.theme_names[self.theme_i]} (T)")
        self.refresh_buttons()
        self.draw()

    def refresh_buttons(self):
        self.sound_btn.configure(text="Sound: ON (M)" if self.sound else "Sound: OFF (M)")
        self.solve_btn.configure(text="Stop (P)" if self.autoplay else "Solve (P)")

    # ---------------------------------------------------------- game setup
    def score_key(self):
        return f"{self.mode_var.get()}|{self.diff_var.get()}"

    def new_game(self):
        if self.confetti_job:
            self.root.after_cancel(self.confetti_job)
            self.confetti_job = None
        self.n, blanks = MODES[self.mode_var.get()]
        self.size = self.n * self.n
        self.cell = BOARD_PX // self.n
        self.adj = build_adj(self.n)
        tiles = self.size - blanks
        self.goal = list(range(1, tiles + 1)) + [0] * blanks
        side = self.n * self.cell + PAD
        self.canvas.configure(width=side, height=side)

        self.board = self.goal[:]
        while True:                                   # scramble with legal moves only
            last = None
            for _ in range(DIFFICULTY[self.diff_var.get()]):
                options = [m for m in self.legal_moves() if last is None or m != (last[1], last[0])]
                a, b = random.choice(options)
                self.board[b], self.board[a] = self.board[a], 0
                last = (a, b)
            if self.board != self.goal:
                break

        self.moves = 0
        self.history = []
        self.elapsed = 0.0
        self.running = False
        self.solved = False
        self.cheated = False
        self.autoplay = False
        self.animating = False
        self.hint_tile = None
        self.set_status("Shuffled! Your first move starts the clock.")
        self.update_labels()
        self.refresh_buttons()
        self.draw()

    def on_setting_change(self, _event=None):
        self.new_game()
        self.root.focus_set()

    def legal_moves(self):
        """All (from_index, to_index): a tile at from_index can slide into blank to_index."""
        return [(a, b) for b in range(self.size) if self.board[b] == 0
                for a in self.adj[b] if self.board[a] != 0]

    # ---------------------------------------------------------- moving tiles
    def try_move(self, a, b, auto=False, done=None):
        if self.animating or self.solved or (self.autoplay and not auto):
            return
        self.hint_tile = None
        if not self.running:
            self.running = True
            self.t0 = time.time() - self.elapsed
        self.history.append(self.board[:])
        self.animating = True
        self.beep(700, 15)
        steps = 8

        def step(k):
            if k <= steps:
                self.draw(moving=(a, b, k / steps))
                self.root.after(12, lambda: step(k + 1))
            else:
                finish()

        def finish():
            self.board[b], self.board[a] = self.board[a], 0
            self.moves += 1
            self.animating = False
            self.update_labels()
            if self.board == self.goal:
                self.win()
            else:
                self.draw()
            if done:
                done()

        step(1)

    def move_dir(self, dr, dc):
        """Slide a tile in direction (dr, dc) into a blank square."""
        for b in range(self.size):
            if self.board[b] != 0:
                continue
            r, c = divmod(b, self.n)
            sr, sc = r - dr, c - dc
            if 0 <= sr < self.n and 0 <= sc < self.n and self.board[sr * self.n + sc] != 0:
                self.try_move(sr * self.n + sc, b)
                return

    def on_key(self, e):
        k = e.keysym.lower()
        dirs = {"up": (-1, 0), "w": (-1, 0), "down": (1, 0), "s": (1, 0),
                "left": (0, -1), "a": (0, -1), "right": (0, 1), "d": (0, 1)}
        if k in dirs:
            self.move_dir(*dirs[k])
        elif k == "n": self.new_game()
        elif k == "z": self.undo()
        elif k == "h": self.hint()
        elif k == "p": self.toggle_solve()
        elif k == "t": self.next_theme()
        elif k == "m": self.toggle_sound()

    def on_click(self, e):
        c, r = (e.x - PAD) // self.cell, (e.y - PAD) // self.cell
        if not (0 <= r < self.n and 0 <= c < self.n):
            return
        a = r * self.n + c
        if self.board[a] == 0:
            return
        for b in self.adj[a]:
            if self.board[b] == 0:
                self.try_move(a, b)
                return

    # ---------------------------------------------------------- extras
    def undo(self):
        if self.animating or self.autoplay or self.solved or not self.history:
            return
        self.board = self.history.pop()
        self.moves = max(0, self.moves - 1)
        self.hint_tile = None
        self.set_status("Undone!")
        self.update_labels()
        self.draw()

    def run_solver(self):
        self.set_status("Thinking...")
        self.root.update_idletasks()
        weight, limit = (1.0, 200000) if self.n == 3 else (3.0, 80000)
        return solve_puzzle(self.board, self.goal, self.n, weight, limit)

    def hint(self):
        if self.animating or self.autoplay or self.solved:
            return
        path = self.run_solver()
        if not path:
            self.set_status("Hmm, too tangled for a hint. Try Undo or an easier difficulty.")
            return
        a = path[0][0]
        self.hint_tile = a
        self.set_status(f"Hint: slide tile {self.board[a]}. Solvable in about {len(path)} moves.")
        self.draw()

    def toggle_solve(self):
        if self.solved or self.animating:
            return
        if self.autoplay:
            self.autoplay = False
            self.set_status("Robot stopped. Your turn!")
            self.refresh_buttons()
            return
        path = self.run_solver()
        if not path:
            self.set_status("Too tangled for the robot. Try Undo or an easier difficulty.")
            return
        self.cheated = True
        self.autoplay = True
        self.hint_tile = None
        self.set_status(f"Robot is solving it in {len(path)} moves... (no score saved)")
        self.refresh_buttons()
        self.run_path(path)

    def run_path(self, path):
        if not self.autoplay or not path or self.solved:
            self.autoplay = False
            self.refresh_buttons()
            return
        a, b = path.pop(0)
        self.try_move(a, b, auto=True,
                      done=lambda: self.root.after(100, lambda: self.run_path(path)))

    def next_theme(self):
        self.theme_i = (self.theme_i + 1) % len(self.theme_names)
        self.apply_theme()

    def toggle_sound(self):
        self.sound = not self.sound
        self.refresh_buttons()
        self.beep(880, 60)

    def beep(self, freq, ms):
        if self.sound and winsound:
            try:
                winsound.Beep(freq, ms)
            except Exception:
                pass

    # ---------------------------------------------------------- winning
    def win(self):
        self.solved = True
        self.running = False
        self.autoplay = False
        self.elapsed = time.time() - self.t0
        self.refresh_buttons()
        msg = f"Solved in {self.moves} moves and {fmt_time(self.elapsed)}!"
        if self.cheated:
            msg = "The robot solved it! (no score saved)"
        else:
            rec = self.scores.setdefault(self.score_key(), {})
            notes = []
            if "time" not in rec or self.elapsed < rec["time"]:
                rec["time"] = round(self.elapsed, 1)
                notes.append("NEW BEST TIME")
            if "moves" not in rec or self.moves < rec["moves"]:
                rec["moves"] = self.moves
                notes.append("NEW BEST MOVES")
            self.save_scores()
            if notes:
                msg += "  " + " + ".join(notes) + "!"
        self.set_status(msg)
        self.update_labels()
        self.draw()
        self.start_confetti()
        for f, d in ((523, 110), (659, 110), (784, 220)):
            self.beep(f, d)

    def start_confetti(self):
        side = self.n * self.cell + PAD
        colors = self.theme["tiles"] + [GOLD]
        self.parts = [[random.uniform(0, side), random.uniform(-side, 0),
                       random.uniform(-1.5, 1.5), random.uniform(2, 5),
                       random.choice(colors), random.randint(4, 8)] for _ in range(80)]
        self.confetti_frame(0)

    def confetti_frame(self, k):
        self.canvas.delete("confetti")
        if k > 110 or not self.solved:
            return
        for p in self.parts:
            p[0] += p[2]
            p[1] += p[3]
            self.canvas.create_rectangle(p[0], p[1], p[0] + p[5], p[1] + p[5],
                                         fill=p[4], outline="", tags="confetti")
        self.confetti_job = self.root.after(30, lambda: self.confetti_frame(k + 1))

    # ---------------------------------------------------------- labels / scores
    def set_status(self, text):
        self.status_lbl.configure(text=text)

    def update_labels(self):
        self.moves_lbl.configure(text=f"Moves: {self.moves}")
        self.time_lbl.configure(text=f"Time: {fmt_time(self.elapsed)}")
        rec = self.scores.get(self.score_key())
        if rec:
            self.best_lbl.configure(text=f"Best: {fmt_time(rec['time'])} | {rec['moves']} moves")
        else:
            self.best_lbl.configure(text="Best: --")

    def tick(self):
        if self.running:
            self.elapsed = time.time() - self.t0
            self.time_lbl.configure(text=f"Time: {fmt_time(self.elapsed)}")
        self.root.after(200, self.tick)

    def load_scores(self):
        try:
            with open(SCORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_scores(self):
        try:
            with open(SCORE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.scores, f, indent=2)
        except Exception:
            pass

    # ---------------------------------------------------------- drawing
    def cell_xy(self, i):
        return PAD + (i % self.n) * self.cell, PAD + (i // self.n) * self.cell

    def round_rect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def draw(self, moving=None):
        if not self.board:
            return
        c, th, cell = self.canvas, self.theme, self.cell
        c.delete("all")
        c.configure(bg=th["bg"])
        for i in range(self.size):                        # empty slots
            x, y = self.cell_xy(i)
            self.round_rect(x, y, x + cell - PAD, y + cell - PAD, 14, fill=th["slot"], outline="")
        for i, v in enumerate(self.board):
            if v == 0:
                continue
            x, y = self.cell_xy(i)
            if moving and moving[0] == i:                 # tile in mid-slide
                dx, dy = self.cell_xy(moving[1])
                x += (dx - x) * moving[2]
                y += (dy - y) * moving[2]
            color = th["tiles"][(v - 1) % len(th["tiles"])]
            outline, width = "", 1
            if self.goal[i] == v:
                outline, width = GOLD, 3
            if self.hint_tile == i:
                outline, width = th["fg"], 5
            self.round_rect(x, y, x + cell - PAD, y + cell - PAD, 14,
                            fill=color, outline=outline, width=width)
            c.create_text(x + (cell - PAD) / 2, y + (cell - PAD) / 2, text=str(v),
                          font=("Arial", cell // 3, "bold"), fill="#ffffff")
        if self.solved:
            mid = (self.n * self.cell + PAD) / 2
            self.round_rect(mid - 130, mid - 45, mid + 130, mid + 45, 18, fill=th["bg"], outline=GOLD, width=3)
            c.create_text(mid, mid - 12, text="SOLVED!", font=("Arial", 30, "bold"), fill=GOLD)
            c.create_text(mid, mid + 24, text="Press N for a new game", font=("Arial", 11), fill=th["fg"])


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()
