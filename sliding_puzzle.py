"""
3x3 Sliding Puzzle (tkinter, no extra installs needed)

Controls
  Arrow keys / W A S D : move a tile Up, Down, Left, Right into a blank square
  Mouse click          : click a tile next to a blank to slide it
  Shuffle button       : new random (always solvable) puzzle

Set NUM_BLANKS = 2 to play with 7 tiles + 2 blanks on the 3x3 grid.
"""
import random
import tkinter as tk

SIZE = 3            # 3x3 matrix
NUM_BLANKS = 1      # 1 -> 8 tiles (classic). 2 -> 7 tiles + 2 blanks.
CELL = 110          # pixel size of a square
PAD = 8

# Colors
BG = "#1e1e2e"
BLANK_COLOR = "#2b2b3d"
TILE_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71",
               "#1abc9c", "#3498db", "#9b59b6", "#e84393"]
TEXT_COLOR = "#ffffff"

# Direction -> (row change, col change) of the TILE's movement
DIRS = {"Up": (-1, 0), "Down": (1, 0), "Left": (0, -1), "Right": (0, 1)}


class Puzzle:
    def __init__(self, root):
        self.root = root
        root.title("Sliding Puzzle")
        root.configure(bg=BG)
        root.resizable(False, False)

        n_tiles = SIZE * SIZE - NUM_BLANKS
        self.goal = [[0] * SIZE for _ in range(SIZE)]
        for i in range(SIZE * SIZE):
            self.goal[i // SIZE][i % SIZE] = i + 1 if i < n_tiles else 0
        self.board = [row[:] for row in self.goal]  # 0 = blank
        self.moves = 0

        self.info = tk.Label(root, text="", font=("Arial", 14, "bold"),
                             bg=BG, fg=TEXT_COLOR)
        self.info.pack(pady=(10, 0))

        side = SIZE * CELL + PAD
        self.canvas = tk.Canvas(root, width=side, height=side, bg=BG,
                                highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)

        tk.Button(root, text="Shuffle", font=("Arial", 12), command=self.shuffle,
                  bg="#3498db", fg="white", relief="flat",
                  padx=14, pady=4).pack(pady=(0, 12))

        self.canvas.bind("<Button-1>", self.on_click)
        root.bind("<Key>", self.on_key)
        self.shuffle()

    # ---------- game logic ----------
    def blanks(self):
        return [(r, c) for r in range(SIZE) for c in range(SIZE)
                if self.board[r][c] == 0]

    def move(self, direction):
        """Move a tile Up/Down/Left/Right into a blank. Returns True if moved."""
        dr, dc = DIRS[direction]
        for br, bc in self.blanks():
            sr, sc = br - dr, bc - dc          # tile that would slide into blank
            if 0 <= sr < SIZE and 0 <= sc < SIZE and self.board[sr][sc] != 0:
                self.board[br][bc], self.board[sr][sc] = self.board[sr][sc], 0
                return True
        return False

    def is_solved(self):
        return self.board == self.goal

    def shuffle(self):
        # Random legal moves from the goal => always solvable
        self.board = [row[:] for row in self.goal]
        for _ in range(300):
            self.move(random.choice(list(DIRS)))
        if self.is_solved():
            self.shuffle()
            return
        self.moves = 0
        self.update_ui()

    # ---------- input ----------
    def on_key(self, event):
        keys = {"Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
                "w": "Up", "s": "Down", "a": "Left", "d": "Right"}
        d = keys.get(event.keysym)
        if d and not self.is_solved() and self.move(d):
            self.moves += 1
            self.update_ui()

    def on_click(self, event):
        if self.is_solved():
            return
        r, c = event.y // CELL, event.x // CELL
        if not (0 <= r < SIZE and 0 <= c < SIZE) or self.board[r][c] == 0:
            return
        for name, (dr, dc) in DIRS.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE and self.board[nr][nc] == 0:
                self.board[nr][nc], self.board[r][c] = self.board[r][c], 0
                self.moves += 1
                self.update_ui()
                return

    # ---------- drawing ----------
    def update_ui(self):
        self.canvas.delete("all")
        for r in range(SIZE):
            for c in range(SIZE):
                v = self.board[r][c]
                x0, y0 = c * CELL + PAD, r * CELL + PAD
                x1, y1 = x0 + CELL - PAD, y0 + CELL - PAD
                color = BLANK_COLOR if v == 0 else TILE_COLORS[(v - 1) % len(TILE_COLORS)]
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
                if v:
                    self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=str(v),
                                            font=("Arial", 36, "bold"), fill=TEXT_COLOR)
        if self.is_solved():
            self.info.config(text=f"Solved in {self.moves} moves!", fg="#2ecc71")
        else:
            self.info.config(text=f"Moves: {self.moves}", fg=TEXT_COLOR)


if __name__ == "__main__":
    root = tk.Tk()
    Puzzle(root)
    root.mainloop()
