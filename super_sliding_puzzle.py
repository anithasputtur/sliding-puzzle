import heapq
import json
import os
import random
import time
import tkinter as tk
from tkinter import ttk

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

THEMES = {
    "Neon Night": {"bg": "#12121f", "slot": "#1e1e36", "fg": "#ffffff", "button": "#6c5ce7",
                   "tiles": ["#ff4757", "#ffa502", "#ffdd59", "#2ed573",
                             "#18dcff", "#3d9bff", "#a55eea", "#ff6bcb"]},
    "Sunset": {"bg": "#2d142c", "slot": "#451b3f", "fg": "#fff3e0", "button": "#d63031",
               "tiles": ["#ff7675", "#fab1a0", "#fdcb6e", "#e17055",
                         "#ff9f43", "#ee5a24", "#c44569", "#f8a5c2"]},
    "Ocean": {"bg": "#0b2545", "slot": "#13315c", "fg": "#e8f4ff", "button": "#0984e3",
              "tiles": ["#00cec9", "#0abde3", "#48dbfb", "#1dd1a1",
                        "#54a0ff", "#5f27cd", "#00b894", "#74b9ff"]},
    "Candy": {"bg": "#fff0f6", "slot": "#f3d6e4", "fg": "#5a2a4a", "button": "#e84393",
              "tiles": ["#ff6b81", "#ff9ff3", "#feca57", "#1dd1a1",
                        "#48dbfb", "#a29bfe", "#fd79a8", "#55efc4"]},
}

SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzle_scores.json")
BOARD_SIZE = 330
PAD = 8
GOLD = "#ffd700"
DIRECTIONS = {"Up": (-1, 0), "Down": (1, 0), "Left": (0, -1), "Right": (0, 1)}
KEYS = {"up": "Up", "down": "Down", "left": "Left", "right": "Right",
        "w": "Up", "s": "Down", "a": "Left", "d": "Right"}


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


# A* search, used for hints and the robot
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


def fmt_time(seconds):
    seconds = int(seconds)
    return "%02d:%02d" % (seconds // 60, seconds % 60)


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Super Sliding Puzzle")
        root.resizable(False, False)

        self.theme_names = list(THEMES)
        self.theme_index = 0
        self.sound = False
        self.scores = self.load_scores()

        self.animating = False
        self.autoplay = False
        self.hint_tile = None
        self.running = False
        self.solved = False
        self.cheated = False
        self.elapsed = 0.0
        self.t0 = 0.0
        self.moves = 0
        self.history = []
        self.confetti_job = None
        self.confetti = []

        self.n = 3
        self.cell = BOARD_SIZE // 3
        self.size = 9
        self.neighbours = get_neighbours(3)
        self.board = []
        self.goal = []

        self.mode_var = tk.StringVar(value=list(MODES)[0])
        self.level_var = tk.StringVar(value="Medium")
        self.frames = []
        self.labels = []
        self.buttons = []

        self.build_ui()
        self.new_game()
        self.apply_theme()
        self.tick()

    @property
    def theme(self):
        return THEMES[self.theme_names[self.theme_index]]

    def make_label(self, parent, **kw):
        lbl = tk.Label(parent, **kw)
        self.labels.append(lbl)
        return lbl

    def make_button(self, parent, text, command, width=10):
        btn = tk.Button(parent, text=text, command=command, width=width, relief="flat",
                        font=("Arial", 10, "bold"), takefocus=0, cursor="hand2")
        self.buttons.append(btn)
        return btn

    def make_frame(self, parent):
        f = tk.Frame(parent)
        self.frames.append(f)
        return f

    def build_ui(self):
        root = self.root
        self.make_label(root, text="SUPER SLIDING PUZZLE", font=("Arial", 18, "bold")).pack(pady=(10, 2))

        stats = self.make_frame(root)
        stats.pack()
        self.moves_label = self.make_label(stats, font=("Arial", 12, "bold"), width=11)
        self.time_label = self.make_label(stats, font=("Arial", 12, "bold"), width=11)
        self.best_label = self.make_label(stats, font=("Arial", 10), width=22)
        self.moves_label.grid(row=0, column=0)
        self.time_label.grid(row=0, column=1)
        self.best_label.grid(row=1, column=0, columnspan=2)

        self.status = self.make_label(root, font=("Arial", 10, "italic"), wraplength=340, height=2)
        self.status.pack()

        self.canvas = tk.Canvas(root, highlightthickness=0)
        self.canvas.pack(padx=10, pady=4)
        self.canvas.bind("<Button-1>", self.on_click)

        row1 = self.make_frame(root)
        row1.pack(pady=4)
        self.make_button(row1, "Shuffle (N)", self.new_game).grid(row=0, column=0, padx=3)
        self.make_button(row1, "Undo (Z)", self.undo).grid(row=0, column=1, padx=3)
        self.make_button(row1, "Hint (H)", self.hint).grid(row=0, column=2, padx=3)
        self.solve_btn = self.make_button(row1, "Solve (P)", self.toggle_solve)
        self.solve_btn.grid(row=0, column=3, padx=3)

        row2 = self.make_frame(root)
        row2.pack(pady=4)
        mode_box = ttk.Combobox(row2, textvariable=self.mode_var, values=list(MODES), state="readonly", width=24)
        level_box = ttk.Combobox(row2, textvariable=self.level_var, values=list(LEVELS), state="readonly", width=8)
        mode_box.grid(row=0, column=0, padx=3)
        level_box.grid(row=0, column=1, padx=3)
        for box in (mode_box, level_box):
            box.bind("<<ComboboxSelected>>", self.on_setting_change)

        row3 = self.make_frame(root)
        row3.pack(pady=(4, 10))
        self.theme_btn = self.make_button(row3, "", self.next_theme, width=22)
        self.theme_btn.grid(row=0, column=0, padx=3)
        self.sound_btn = self.make_button(row3, "", self.toggle_sound, width=14)
        self.sound_btn.grid(row=0, column=1, padx=3)

        root.bind("<Key>", self.on_key)

    def apply_theme(self):
        theme = self.theme
        self.root.configure(bg=theme["bg"])
        for f in self.frames:
            f.configure(bg=theme["bg"])
        for lbl in self.labels:
            lbl.configure(bg=theme["bg"], fg=theme["fg"])
        for btn in self.buttons:
            btn.configure(bg=theme["button"], fg="#ffffff",
                          activebackground=theme["tiles"][0], activeforeground="#ffffff")
        self.theme_btn.configure(text="Theme: %s (T)" % self.theme_names[self.theme_index])
        self.refresh_buttons()
        self.draw()

    def refresh_buttons(self):
        self.sound_btn.configure(text="Sound: ON (M)" if self.sound else "Sound: OFF (M)")
        self.solve_btn.configure(text="Stop (P)" if self.autoplay else "Solve (P)")

    def score_key(self):
        return "%s|%s" % (self.mode_var.get(), self.level_var.get())

    def new_game(self):
        if self.confetti_job:
            self.root.after_cancel(self.confetti_job)
            self.confetti_job = None

        self.n, blanks = MODES[self.mode_var.get()]
        self.size = self.n * self.n
        self.cell = BOARD_SIZE // self.n
        self.neighbours = get_neighbours(self.n)
        self.goal = list(range(1, self.size - blanks + 1)) + [0] * blanks
        side = self.n * self.cell + PAD
        self.canvas.configure(width=side, height=side)

        # scramble from the solved board using only legal moves
        self.board = self.goal[:]
        while True:
            last = None
            for _ in range(LEVELS[self.level_var.get()]):
                moves = self.legal_moves()
                if last:
                    moves = [m for m in moves if m != (last[1], last[0])]
                src, dst = random.choice(moves)
                self.board[dst] = self.board[src]
                self.board[src] = 0
                last = (src, dst)
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

    def on_setting_change(self, event=None):
        self.new_game()
        self.root.focus_set()

    def legal_moves(self):
        moves = []
        for blank in range(self.size):
            if self.board[blank] != 0:
                continue
            for tile in self.neighbours[blank]:
                if self.board[tile] != 0:
                    moves.append((tile, blank))
        return moves

    # src is the tile, dst is the blank it slides into
    def try_move(self, src, dst, auto=False, done=None):
        if self.animating or self.solved:
            return
        if self.autoplay and not auto:
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
                self.draw(moving=(src, dst, k / steps))
                self.root.after(12, lambda: step(k + 1))
                return
            self.board[dst] = self.board[src]
            self.board[src] = 0
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

    def move_dir(self, drow, dcol):
        for blank in range(self.size):
            if self.board[blank] != 0:
                continue
            row, col = divmod(blank, self.n)
            r, c = row - drow, col - dcol
            if 0 <= r < self.n and 0 <= c < self.n and self.board[r * self.n + c] != 0:
                self.try_move(r * self.n + c, blank)
                return

    def on_key(self, event):
        key = event.keysym.lower()
        if key in KEYS:
            self.move_dir(*DIRECTIONS[KEYS[key]])
        elif key == "n":
            self.new_game()
        elif key == "z":
            self.undo()
        elif key == "h":
            self.hint()
        elif key == "p":
            self.toggle_solve()
        elif key == "t":
            self.next_theme()
        elif key == "m":
            self.toggle_sound()

    def on_click(self, event):
        col = (event.x - PAD) // self.cell
        row = (event.y - PAD) // self.cell
        if not (0 <= row < self.n and 0 <= col < self.n):
            return
        tile = row * self.n + col
        if self.board[tile] == 0:
            return
        for other in self.neighbours[tile]:
            if self.board[other] == 0:
                self.try_move(tile, other)
                return

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
        if self.n == 3:
            return solve(self.board, self.goal, self.n, 1.0, 200000)
        return solve(self.board, self.goal, self.n, 3.0, 80000)

    def hint(self):
        if self.animating or self.autoplay or self.solved:
            return
        path = self.run_solver()
        if not path:
            self.set_status("Hmm, too tangled for a hint. Try Undo or an easier difficulty.")
            return
        self.hint_tile = path[0][0]
        self.set_status("Hint: slide tile %d. Solvable in about %d moves." % (self.board[self.hint_tile], len(path)))
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
        self.set_status("Robot is solving it in %d moves... (no score saved)" % len(path))
        self.refresh_buttons()
        self.play_path(path)

    def play_path(self, path):
        if not self.autoplay or not path or self.solved:
            self.autoplay = False
            self.refresh_buttons()
            return
        src, dst = path.pop(0)
        self.try_move(src, dst, auto=True,
                      done=lambda: self.root.after(100, lambda: self.play_path(path)))

    def next_theme(self):
        self.theme_index = (self.theme_index + 1) % len(self.theme_names)
        self.apply_theme()

    def toggle_sound(self):
        self.sound = not self.sound
        self.refresh_buttons()
        self.beep(880, 60)

    def beep(self, freq, ms):
        if self.sound and winsound:
            try:
                winsound.Beep(freq, ms)
            except RuntimeError:
                pass

    # best scores are not saved if the robot solved it
    def win(self):
        self.solved = True
        self.running = False
        self.autoplay = False
        self.elapsed = time.time() - self.t0
        self.refresh_buttons()

        if self.cheated:
            message = "The robot solved it! (no score saved)"
        else:
            message = "Solved in %d moves and %s!" % (self.moves, fmt_time(self.elapsed))
            record = self.scores.setdefault(self.score_key(), {})
            notes = []
            if "time" not in record or self.elapsed < record["time"]:
                record["time"] = round(self.elapsed, 1)
                notes.append("NEW BEST TIME")
            if "moves" not in record or self.moves < record["moves"]:
                record["moves"] = self.moves
                notes.append("NEW BEST MOVES")
            self.save_scores()
            if notes:
                message += "  " + " + ".join(notes) + "!"

        self.set_status(message)
        self.update_labels()
        self.draw()
        self.start_confetti()
        for freq, ms in ((523, 110), (659, 110), (784, 220)):
            self.beep(freq, ms)

    def start_confetti(self):
        side = self.n * self.cell + PAD
        colors = self.theme["tiles"] + [GOLD]
        self.confetti = []
        for _ in range(80):
            self.confetti.append([random.uniform(0, side), random.uniform(-side, 0),
                                  random.uniform(-1.5, 1.5), random.uniform(2, 5),
                                  random.choice(colors), random.randint(4, 8)])
        self.confetti_frame(0)

    def confetti_frame(self, frame):
        self.canvas.delete("confetti")
        if frame > 110 or not self.solved:
            return
        for p in self.confetti:
            p[0] += p[2]
            p[1] += p[3]
            self.canvas.create_rectangle(p[0], p[1], p[0] + p[5], p[1] + p[5],
                                         fill=p[4], outline="", tags="confetti")
        self.confetti_job = self.root.after(30, lambda: self.confetti_frame(frame + 1))

    def set_status(self, text):
        self.status.configure(text=text)

    def update_labels(self):
        self.moves_label.configure(text="Moves: %d" % self.moves)
        self.time_label.configure(text="Time: " + fmt_time(self.elapsed))
        record = self.scores.get(self.score_key())
        if record:
            self.best_label.configure(text="Best: %s | %d moves" % (fmt_time(record["time"]), record["moves"]))
        else:
            self.best_label.configure(text="Best: --")

    def tick(self):
        if self.running:
            self.elapsed = time.time() - self.t0
            self.time_label.configure(text="Time: " + fmt_time(self.elapsed))
        self.root.after(200, self.tick)

    def load_scores(self):
        try:
            with open(SCORE_FILE) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def save_scores(self):
        try:
            with open(SCORE_FILE, "w") as f:
                json.dump(self.scores, f, indent=2)
        except OSError:
            pass

    def pos(self, i):
        return PAD + (i % self.n) * self.cell, PAD + (i // self.n) * self.cell

    def rounded(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def draw(self, moving=None):
        if not self.board:
            return
        c = self.canvas
        theme = self.theme
        cell = self.cell
        c.delete("all")
        c.configure(bg=theme["bg"])

        for i in range(self.size):
            x, y = self.pos(i)
            self.rounded(x, y, x + cell - PAD, y + cell - PAD, 14, fill=theme["slot"], outline="")

        for i, v in enumerate(self.board):
            if v == 0:
                continue
            x, y = self.pos(i)
            if moving and moving[0] == i:
                dx, dy = self.pos(moving[1])
                x += (dx - x) * moving[2]
                y += (dy - y) * moving[2]
            color = theme["tiles"][(v - 1) % len(theme["tiles"])]
            outline, width = "", 1
            if self.goal[i] == v:
                outline, width = GOLD, 3
            if self.hint_tile == i:
                outline, width = theme["fg"], 5
            self.rounded(x, y, x + cell - PAD, y + cell - PAD, 14, fill=color, outline=outline, width=width)
            c.create_text(x + (cell - PAD) / 2, y + (cell - PAD) / 2, text=str(v),
                          font=("Arial", cell // 3, "bold"), fill="#ffffff")

        if self.solved:
            mid = (self.n * self.cell + PAD) / 2
            self.rounded(mid - 130, mid - 45, mid + 130, mid + 45, 18, fill=theme["bg"], outline=GOLD, width=3)
            c.create_text(mid, mid - 12, text="SOLVED!", font=("Arial", 30, "bold"), fill=GOLD)
            c.create_text(mid, mid + 24, text="Press N for a new game", font=("Arial", 11), fill=theme["fg"])


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()
