#!/usr/bin/env python3
"""
Classifica questões de matemática na Taxonomia de Bloom via IA (Groq ou DeepSeek).

Uso:
    poetry run python scripts/classify_questions.py --input scripts/questions_to_classify.example.json
    poetry run python scripts/classify_questions.py --input questoes.json --output questoes_classificadas.json --provider deepseek
    poetry run python scripts/classify_questions_deepseek.py --input scripts/quest.json --output questoes_classificadas.json

Formato de entrada:
    - Lista de questões, ou
    - Objeto JSON com a chave "questions"

Questões com level=0 são classificadas pela IA. As demais são preservadas.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.services.question_classifier import classify_questions_batch, load_questions_from_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classifica questões de matemática na Taxonomia de Bloom usando IA."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Arquivo JSON com as questões a classificar.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Arquivo JSON de saída. Se omitido, imprime no stdout.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reclassifica também questões que já possuem level entre 1 e 6.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Segundos de espera entre lotes de classificação (padrão: CLASSIFICATION_REQUEST_DELAY_SECONDS).",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "deepseek"],
        default=None,
        help="Provedor de IA (padrão: CLASSIFICATION_PROVIDER do .env).",
    )
    return parser.parse_args()


def load_input_file(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return load_questions_from_payload(payload)


def write_output(path: Path | None, questions: list[dict]) -> None:
    payload = {"questions": questions}
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)

    if path is None:
        print(serialized)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")
    print(f"Classificação concluída. Arquivo salvo em: {path}")


async def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    try:
        questions = load_input_file(input_path)
        classified = await classify_questions_batch(
            questions,
            only_unclassified=not args.force,
            request_delay_seconds=args.delay,
            provider=args.provider,
        )
        write_output(output_path, classified)
        return 0
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
