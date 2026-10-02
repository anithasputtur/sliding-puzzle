import random
import tkinter as tk

SIZE = 3
BLANKS = 1
CELL = 110
PAD = 8

BG = "#1e1e2e"
EMPTY = "#2b2b3d"
COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71",
          "#1abc9c", "#3498db", "#9b59b6", "#e84393"]

DIRECTIONS = {"Up": (-1, 0), "Down": (1, 0), "Left": (0, -1), "Right": (0, 1)}
KEYS = {"Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
        "w": "Up", "s": "Down", "a": "Left", "d": "Right"}


class Puzzle:
    def __init__(self, root):
        self.root = root
        root.title("Sliding Puzzle")
        root.configure(bg=BG)
        root.resizable(False, False)

        tiles = SIZE * SIZE - BLANKS
        flat = list(range(1, tiles + 1)) + [0] * BLANKS
        self.goal = [flat[i * SIZE:(i + 1) * SIZE] for i in range(SIZE)]
        self.board = [row[:] for row in self.goal]
        self.moves = 0

        self.info = tk.Label(root, font=("Arial", 14, "bold"), bg=BG, fg="white")
        self.info.pack(pady=(10, 0))

        side = SIZE * CELL + PAD
        self.canvas = tk.Canvas(root, width=side, height=side, bg=BG, highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)

        tk.Button(root, text="Shuffle", font=("Arial", 12), command=self.shuffle,
                  bg="#3498db", fg="white", relief="flat", padx=14, pady=4).pack(pady=(0, 12))

        self.canvas.bind("<Button-1>", self.on_click)
        root.bind("<Key>", self.on_key)
        self.shuffle()

    def blanks(self):
        found = []
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board[r][c] == 0:
                    found.append((r, c))
        return found

    # direction is where the tile goes, so the blank must be on the other side
    def move(self, direction):
        dr, dc = DIRECTIONS[direction]
        for br, bc in self.blanks():
            r, c = br - dr, bc - dc
            if 0 <= r < SIZE and 0 <= c < SIZE and self.board[r][c] != 0:
                self.board[br][bc] = self.board[r][c]
                self.board[r][c] = 0
                return True
        return False

    def solved(self):
        return self.board == self.goal

    def shuffle(self):
        # moving randomly from the solved board keeps the puzzle solvable
        self.board = [row[:] for row in self.goal]
        for _ in range(300):
            self.move(random.choice(list(DIRECTIONS)))
        if self.solved():
            self.shuffle()
            return
        self.moves = 0
        self.draw()

    def on_key(self, event):
        direction = KEYS.get(event.keysym)
        if direction and not self.solved() and self.move(direction):
            self.moves += 1
            self.draw()

    def on_click(self, event):
        if self.solved():
            return
        r, c = event.y // CELL, event.x // CELL
        if not (0 <= r < SIZE and 0 <= c < SIZE) or self.board[r][c] == 0:
            return
        for dr, dc in DIRECTIONS.values():
            nr, nc = r + dr, c + dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE and self.board[nr][nc] == 0:
                self.board[nr][nc] = self.board[r][c]
                self.board[r][c] = 0
                self.moves += 1
                self.draw()
                return

    def draw(self):
        self.canvas.delete("all")
        for r in range(SIZE):
            for c in range(SIZE):
                value = self.board[r][c]
                x0 = c * CELL + PAD
                y0 = r * CELL + PAD
                x1 = x0 + CELL - PAD
                y1 = y0 + CELL - PAD
                color = EMPTY if value == 0 else COLORS[(value - 1) % len(COLORS)]
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
                if value:
                    self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=str(value),
                                            font=("Arial", 36, "bold"), fill="white")
        if self.solved():
            self.info.config(text="Solved in %d moves!" % self.moves, fg="#2ecc71")
        else:
            self.info.config(text="Moves: %d" % self.moves, fg="white")


if __name__ == "__main__":
    root = tk.Tk()
    Puzzle(root)
    root.mainloop()
