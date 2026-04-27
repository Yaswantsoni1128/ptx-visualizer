# PTX Visualizer

A small compiler-tool style project that compiles a CUDA kernel to PTX and analyzes the PTX in a human-readable way.

## What it does
- Takes a `.cu` CUDA file or a `.ptx` file
- Compiles CUDA to PTX using `nvcc`
- Counts:
  - instructions
  - registers
  - memory operations

  # PTX Visualizer


  A compact, practical tool to inspect PTX (CUDA assembly) generated from small CUDA kernels. The project helps you understand how CUDA maps to PTX and gives a tiny static-analysis style summary per kernel (instruction counts, register usage, memory vs arithmetic balance, and simple hints).


  ## Features

  - Parse and summarize PTX files produced by `nvcc`.
  - Per-kernel instruction counts and category breakdowns (Memory, Arithmetic, Control Flow, etc.).
  - Register usage summary and simple source-location mapping when PTX is compiled with `-lineinfo`.
  - Lightweight, dependency-free analyzer (pure Python standard library).


  ## Repository layout

  ```
  ptx-visualizer/
  ├─ kernels/           # Example CUDA sources (e.g. add.cu)
  ├─ ptx/               # Example PTX output (e.g. add.ptx)
  ├─ analyzer.py        # Main analysis script (Python)
  ├─ tests/             # Simple smoke tests
  └─ README.md
  ```


  ## Requirements

  - Python 3.8+ (analyzer is pure Python). Optional: a virtual environment for development.
  - To compile `.cu` -> `.ptx`: NVIDIA CUDA Toolkit with `nvcc` on PATH.


  ## Quick start (Windows PowerShell)

  1. Clone the repo:

  ```powershell
  git clone https://github.com/Yaswantsoni1128/ptx-visualizer.git
  cd ptx-visualizer
  ```

  2. (Optional) Create and activate a virtual environment:

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install --upgrade pip
  ```

  3. Run the analyzer on the included PTX:

  ```powershell
  python analyzer.py ptx\add.ptx
  ```

  4. Or compile the CUDA example to PTX (requires nvcc) and analyze:

  ```powershell
  nvcc -ptx -lineinfo kernels\add.cu -o ptx\add.ptx
  python analyzer.py ptx\add.ptx
  ```


  ## Output example

  The analyzer prints a short report similar to:

  - File: ptx/add.ptx
  - Kernels found: 1
  - Unique registers used: 6
  - Total instruction types: 4

  Per-kernel you see instruction counts, category breakdown, and a hint such as:

  "Likely memory-heavy; check for coalescing and reuse." (a simple heuristic)


  ## Tests

  - A small smoke test is included under `tests/`. To run it locally you can install pytest and run:


  ```powershell
  pip install pytest
  python -m pytest -q
  ```


  If pytest is installed in a different Python environment, make sure you activate the same environment before running tests.


  ## Development notes

  - The analyzer is intentionally minimal and conservative: it matches instruction mnemonics, PTX directives like `.entry`/`.func`, and collects registers via simple regexes.
  - For best source-to-PTX mapping, compile with `-lineinfo` so `.loc` directives are present in PTX.
  - If you want to extend the analyzer, consider:
    - Adding more mnemonic categories to the classifier.
    - Emitting JSON/CSV output for downstream tooling.
    - Adding CI (GitHub Actions) to run the smoke test on push.


  ## Contributing

  - Open an issue or a pull request.
  - Keep changes small and focused. Add tests for any new behavior.


  ## License

  - This repository currently has no explicit license file. If you plan to share or re-use the code, add a LICENSE (MIT, Apache-2.0, etc.).


  ---

  If you want, I can also add a small GitHub Actions workflow to run the smoke test automatically on push. Just say "add CI" and I'll create it.
+
+```powershell
+python analyzer.py kernels\add.cu --out ptx
+```
+
+
+Notes:
+
+- The analyzer looks for `.entry` and `.func` blocks in PTX and collects simple metrics.
+- For reproducible results, generate PTX with `nvcc -ptx -lineinfo` so source mappings are available.
+
+
+License: small permissive use is implied; add an explicit license file if you plan to redistribute.
*** End Patch