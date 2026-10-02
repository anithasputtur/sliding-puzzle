# Super Sliding Puzzle

A sliding tile puzzle game in Python (tkinter) - no extra installs needed.

## Files
| File | What it is |
|------|------------|
| `super_sliding_puzzle_v3.py` | **Main game**: 3 pages, max-moves limit, stars, leaderboard, daily challenge, robot solver |
| `super_sliding_puzzle.py` | v2: themes, timer, undo, hint, robot solver |
| `sliding_puzzle.py` | v1: the basic 3x3 puzzle |

## Features (v3)
- Start page, game page and result page
- Modes: 3x3 Classic (8 tiles), 3x3 Two Blanks (7 tiles), 4x4 Big (15 tiles)
- Max-moves limit based on par (best possible solution) or a custom number
- Run out of moves and you get a Try Again screen
- 1-3 star rating, top-5 leaderboard, Daily Challenge
- Hints, undo, pause, A* robot solver, 4 colour themes

## Run
```
python super_sliding_puzzle_v3.py
```
Requires Python 3 (tkinter comes with it).

## Keys (game page)
Arrows / WASD move, Z undo, H hint, Space pause, P robot, R restart, N new puzzle, T theme, M sound, Esc menu.
