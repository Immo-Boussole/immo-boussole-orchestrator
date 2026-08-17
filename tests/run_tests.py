"""
Test runner — mirrors Immo-Boussole pattern.

Usage:
    python tests/run_tests.py
    python tests/run_tests.py --ci
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ci_mode = "--ci" in sys.argv

    args = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
    ]
    if ci_mode:
        args += ["--no-header", "-q"]

    result = subprocess.run(args, cwd=str(ROOT))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
