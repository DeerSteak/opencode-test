# String Reverser (Qt)

A small Qt Widgets GUI that reverses a string live as you type or paste,
handling Unicode correctly (emoji / surrogate pairs stay intact).

## Prerequisites

Qt (6 or 5) + CMake. On macOS via Homebrew:

```bash
brew install qt cmake
```

## Build & run

```bash
cmake -S . -B build
cmake --build build
./build/reverse
```

That's it — it's a live GUI (no "press a key" step); close the window to quit.
