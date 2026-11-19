#!/usr/bin/env python3
"""
Classifica questões usando DeepSeek.

Atalho para classify_questions.py com provider=deepseek.

Uso:
    poetry run python scripts/classify_questions_deepseek.py --input scripts/quest.json
    poetry run python scripts/classify_questions_deepseek.py --input scripts/quest.json --output questoes_classificadas.json
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    script_path = Path(__file__).resolve().parent / "classify_questions.py"
    command = [sys.executable, str(script_path), *sys.argv[1:], "--provider", "deepseek"]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
