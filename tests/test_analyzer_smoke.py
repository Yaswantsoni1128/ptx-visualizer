import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PTX = ROOT / "ptx" / "add.ptx"


def test_smoke_analyze_ptx():
    # Runs analyzer on the included add.ptx and expects exit code 0
    cmd = [sys.executable, str(ROOT / "analyzer.py"), str(PTX)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    assert res.returncode == 0
    # Basic assertion that kernel name appears
    assert "Kernel: add" in res.stdout
