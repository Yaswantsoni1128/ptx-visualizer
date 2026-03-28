#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path


REGISTER_RE = re.compile(r"%[A-Za-z_][A-Za-z0-9_\.]*")
ENTRY_RE = re.compile(r"\.entry\s+([^\s(]+)")
FUNC_RE = re.compile(r"\.func\s+([^\s(]+)")
LOC_RE = re.compile(r"^\s*\.loc\s+(\d+)\s+(\d+)\s+(\d+)")

# Matches an optional predicate like "@%p1 " and then the mnemonic.
MNEMONIC_RE = re.compile(
    r"^(?:@!?%[A-Za-z_][A-Za-z0-9_\.]*\s+)?([A-Za-z_][A-Za-z0-9_]*)(?:\.[A-Za-z0-9_]+)*\b"
)

CATEGORY_MAP = {
    # memory
    "ld": "Memory Load",
    "st": "Memory Store",
    "atom": "Atomic",
    "red": "Atomic",

    # arithmetic
    "add": "Arithmetic",
    "sub": "Arithmetic",
    "mul": "Arithmetic",
    "mad": "Arithmetic",
    "fma": "Arithmetic",
    "div": "Arithmetic",
    "rem": "Arithmetic",

    # type / address conversion
    "cvt": "Type Conversion",
    "cvta": "Type Conversion",

    # logic / bitwise
    "and": "Bitwise",
    "or": "Bitwise",
    "xor": "Bitwise",
    "not": "Bitwise",
    "shl": "Bitwise",
    "shr": "Bitwise",

    # compare / select
    "set": "Compare",
    "selp": "Compare",
    "slct": "Compare",

    # control flow
    "bra": "Control Flow",
    "call": "Control Flow",
    "ret": "Control Flow",
    "brk": "Control Flow",
    "exit": "Control Flow",
    "trap": "Control Flow",

    # move / data
    "mov": "Move",
    "prmt": "Shuffle",
    "vote": "Warp",
    "bar": "Synchronization",
}


@dataclass
class KernelStats:
    name: str
    instruction_count: int = 0
    instruction_hist: Counter = field(default_factory=Counter)
    category_hist: Counter = field(default_factory=Counter)
    registers: set[str] = field(default_factory=set)
    line_mappings: list[tuple[str, str]] = field(default_factory=list)  # ("file:line", "instruction")


def strip_comment(line: str) -> str:
    return line.split("//", 1)[0].rstrip()


def classify_mnemonic(mnemonic: str) -> str:
    base = mnemonic.split(".", 1)[0]
    return CATEGORY_MAP.get(base, "Other")


def extract_mnemonic(line: str) -> str | None:
    line = line.lstrip()
    if not line or line.startswith("."):
        return None
    if line.endswith(":"):
        return None

    m = MNEMONIC_RE.match(line)
    if not m:
        return None
    return m.group(1)


def compile_cu_to_ptx(cu_path: Path, out_dir: Path) -> Path:
    nvcc = shutil.which("nvcc")
    if not nvcc:
        raise RuntimeError(
            "nvcc was not found in PATH. Install the CUDA Toolkit or analyze an existing .ptx file."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    ptx_path = out_dir / f"{cu_path.stem}.ptx"

    cmd = [
        nvcc,
        "-ptx",
        "-lineinfo",
        str(cu_path),
        "-o",
        str(ptx_path),
    ]

    print(f"[compile] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return ptx_path


def analyze_ptx(ptx_path: Path) -> dict:
    kernels: dict[str, KernelStats] = {}
    overall_instruction_hist = Counter()
    overall_category_hist = Counter()
    overall_registers: set[str] = set()

    current_kernel: KernelStats | None = None
    current_loc: str | None = None

    lines = ptx_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    for raw_line in lines:
        line = strip_comment(raw_line).strip()
        if not line:
            continue

        # Track source-location mapping if PTX was generated with -lineinfo
        loc_match = LOC_RE.match(line)
        if loc_match:
            file_id, src_line, _col = loc_match.groups()
            current_loc = f"file#{file_id}:line{src_line}"
            continue

        # Detect kernel/function starts
        entry_match = ENTRY_RE.search(line)
        func_match = FUNC_RE.search(line)
        if entry_match:
            name = entry_match.group(1)
            current_kernel = kernels.setdefault(name, KernelStats(name=name))
            continue
        elif func_match and current_kernel is None:
            # Some PTX files may contain helper .func blocks
            name = func_match.group(1)
            current_kernel = kernels.setdefault(name, KernelStats(name=name))
            continue

        # Detect end of a kernel/function block
        if line == "}":
            current_kernel = None
            current_loc = None
            continue

        # Collect register declarations from PTX directives
        if ".reg" in line:
            regs = REGISTER_RE.findall(line)
            if current_kernel:
                current_kernel.registers.update(regs)
            else:
                overall_registers.update(regs)
            continue

        mnemonic = extract_mnemonic(line)
        if not mnemonic:
            continue

        category = classify_mnemonic(mnemonic)
        regs_in_line = set(REGISTER_RE.findall(line))

        overall_instruction_hist[mnemonic] += 1
        overall_category_hist[category] += 1
        overall_registers.update(regs_in_line)

        if current_kernel is None:
            # If a PTX file is unusual, still count globally.
            continue

        current_kernel.instruction_count += 1
        current_kernel.instruction_hist[mnemonic] += 1
        current_kernel.category_hist[category] += 1
        current_kernel.registers.update(regs_in_line)

        if current_loc:
            current_kernel.line_mappings.append((current_loc, line))

    return {
        "ptx_path": ptx_path,
        "kernels": kernels,
        "overall_instruction_hist": overall_instruction_hist,
        "overall_category_hist": overall_category_hist,
        "overall_registers": overall_registers,
    }


def print_report(report: dict) -> None:
    ptx_path: Path = report["ptx_path"]
    kernels: dict[str, KernelStats] = report["kernels"]
    overall_instruction_hist: Counter = report["overall_instruction_hist"]
    overall_category_hist: Counter = report["overall_category_hist"]
    overall_registers: set[str] = report["overall_registers"]

    print("\n=== PTX Visualizer Report ===")
    print(f"File: {ptx_path}")
    print(f"Kernels found: {len(kernels)}")
    print(f"Unique registers used: {len(overall_registers)}")
    print(f"Total instruction types: {len(overall_instruction_hist)}")

    print("\n--- Overall Category Breakdown ---")
    for category, count in overall_category_hist.most_common():
        print(f"{category:18} : {count}")

    print("\n--- Top Instructions ---")
    for mnemonic, count in overall_instruction_hist.most_common(10):
        print(f"{mnemonic:18} : {count}")

    if kernels:
        print("\n--- Per-Kernel Summary ---")
        for kernel in kernels.values():
            print(f"\nKernel: {kernel.name}")
            print(f"  Instructions : {kernel.instruction_count}")
            print(f"  Registers    : {len(kernel.registers)}")
            for category, count in kernel.category_hist.most_common():
                print(f"  {category:18} : {count}")

            loads = kernel.category_hist.get("Memory Load", 0)
            stores = kernel.category_hist.get("Memory Store", 0)
            arithmetic = kernel.category_hist.get("Arithmetic", 0)

            print("  Hint         : ", end="")
            if loads + stores > arithmetic:
                print("Likely memory-heavy; check for coalescing and reuse.")
            elif len(kernel.registers) > 64:
                print("High register use; possible register pressure.")
            else:
                print("Balanced pattern; looks reasonable for a small kernel.")

            if kernel.line_mappings:
                print("  Source map   :")
                for src, inst in kernel.line_mappings[:5]:
                    print(f"    {src} -> {inst}")

    print("\nDone.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze PTX generated from CUDA kernels."
    )
    parser.add_argument(
        "input",
        help="Path to a .ptx file or a .cu file",
    )
    parser.add_argument(
        "--out",
        default="ptx",
        help="Output folder for generated PTX when input is .cu (default: ptx)",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        if input_path.suffix.lower() == ".cu":
            ptx_path = compile_cu_to_ptx(input_path, Path(args.out).resolve())
        elif input_path.suffix.lower() == ".ptx":
            ptx_path = input_path
        else:
            print("Error: input must be a .cu or .ptx file", file=sys.stderr)
            return 1

        report = analyze_ptx(ptx_path)
        print_report(report)
        return 0

    except subprocess.CalledProcessError as e:
        print(f"nvcc failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())