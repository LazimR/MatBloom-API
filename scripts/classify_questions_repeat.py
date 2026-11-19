#!/usr/bin/env python3
"""
Repete a classificação de questões N vezes e mede o desempenho.

Uso:
    poetry run python scripts/classify_questions_repeat.py scripts/clone_quest.json 5
    poetry run python scripts/classify_questions_repeat.py scripts/quest.json 3 -o questoes_classificadas.json

Saída gerada:
    questoes_classificadas_1.json
    questoes_classificadas_2.json
    questoes_classificadas_3.json

Também gera *_metrics.csv (execuções), *_requests.csv (tentativas de API),
*_waits.csv (esperas) e *_summary.json (configurações e estatísticas).
Edite manualmente o arquivo de entrada para mudar a quantidade de questões.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import platform
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from time import perf_counter

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.services import question_classifier as classifier


RUN_FIELDS = [
    "run", "started_at", "status", "input_questions", "pending_questions",
    "classified_questions", "skipped_questions", "batches", "request_attempts",
    "retries", "failed_requests", "total_seconds", "api_seconds",
    "batch_wait_seconds", "retry_wait_seconds", "other_seconds",
    "seconds_per_question", "api_seconds_per_question", "questions_per_minute",
    "error", "output_file",
]
REQUEST_FIELDS = ["run", "batch", "questions", "attempt", "status_code", "seconds", "error"]
WAIT_FIELDS = ["run", "batch", "reason", "requested_seconds", "seconds"]
TIME_FIELDS = [
    "total_seconds", "api_seconds", "batch_wait_seconds", "retry_wait_seconds",
    "other_seconds", "seconds_per_question", "api_seconds_per_question",
    "questions_per_minute",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repete a classificação e exporta resultados, tempos e estatísticas."
    )
    parser.add_argument("input", help="Arquivo JSON de entrada com as questões.")
    parser.add_argument("times", type=int, help="Quantas vezes repetir a classificação.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reclassifica também questões cujo level já é diferente de zero.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Nome base do arquivo de saída (ex.: questoes_classificadas.json).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Segundos de espera entre lotes (padrão: CLASSIFICATION_REQUEST_DELAY_SECONDS).",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "deepseek"],
        default="deepseek",
        help="Provedor de IA (padrão: deepseek).",
    )
    return parser.parse_args()


def load_questions(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    with path.open("r", encoding="utf-8") as file:
        return classifier.load_questions_from_payload(json.load(file))


def build_output_path(base_path: Path, run_number: int) -> Path:
    return base_path.with_name(f"{base_path.stem}_{run_number}{base_path.suffix}")


def resolve_output_base(input_path: Path, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg)

    return input_path.with_name(f"{input_path.stem}_classificadas.json")


def save_questions(path: Path, questions: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"questions": questions}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


async def main() -> int:
    args = parse_args()

    if args.times <= 0:
        print("Erro: o número de repetições deve ser maior que zero.", file=sys.stderr)
        return 1

    input_path = Path(args.input)
    output_base = resolve_output_base(input_path, args.output)

    try:
        # Uma única leitura garante a mesma entrada em todas as repetições.
        questions = load_questions(input_path)
        if not questions:
            raise ValueError("O arquivo de entrada não contém questões.")
        delay = (
            classifier.CLASSIFICATION_REQUEST_DELAY_SECONDS
            if args.delay is None else max(0.0, args.delay)
        )
        settings = experiment_settings(args, input_path, questions, delay)
        runs: list[dict] = []
        requests: list[dict] = []
        waits: list[dict] = []

        for run in range(1, args.times + 1):
            output_path = build_output_path(output_base, run)
            print(f"[{run}/{args.times}] Classificando {len(questions)} questão(ões)...")
            metrics = classifier.ClassificationMetrics()
            started_at = datetime.now(timezone.utc).isoformat()
            started = perf_counter()
            classified = None
            error = ""
            status = "success"
            try:
                classified = await classifier.classify_questions_batch(
                    deepcopy(questions),
                    only_unclassified=not args.force,
                    request_delay_seconds=delay,
                    provider=args.provider,
                    metrics=metrics,
                )
                if metrics.pending_questions == 0:
                    status = "skipped"
            except Exception as exc:
                status = "failed"
                error = f"{type(exc).__name__}: {exc}"
            total = perf_counter() - started

            # O tempo de gravação dos arquivos não entra no tempo de classificação.
            if classified is not None:
                try:
                    save_questions(output_path, classified)
                except OSError as exc:
                    status = "failed"
                    error = f"Erro ao salvar resultado: {exc}"
            row = build_run_metrics(run, started_at, status, error, output_path,
                                    len(questions), total, metrics)
            runs.append(row)
            requests.extend({"run": run, **item} for item in metrics.requests)
            waits.extend({"run": run, **item} for item in metrics.waits)
            write_reports(output_base, settings, runs, requests, waits)
            print(
                f"[{run}/{args.times}] {status}: total={total:.3f}s; "
                f"API={row['api_seconds']:.3f}s; "
                f"esperas={row['batch_wait_seconds'] + row['retry_wait_seconds']:.3f}s"
            )
            if error:
                print(f"Erro na repetição {run}: {error}", file=sys.stderr)

        successes = sum(row["status"] == "success" for row in runs)
        failures = sum(row["status"] == "failed" for row in runs)
        print(f"Concluído: {successes} sucesso(s), {failures} falha(s), "
              f"{len(runs) - successes - failures} sem questões pendentes.")
        print(f"Métricas: {report_path(output_base, 'metrics', '.csv')}")
        print(f"Resumo: {report_path(output_base, 'summary', '.json')}")
        return 1 if failures else 0
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


def experiment_settings(args, input_path: Path, questions: list[dict], delay: float) -> dict:
    is_deepseek = args.provider == "deepseek"
    prefix = "DEEPSEEK" if is_deepseek else "GROQ"
    canonical_input = json.dumps(questions, ensure_ascii=False, sort_keys=True)
    return {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path.resolve()),
        "input_sha256": hashlib.sha256(canonical_input.encode("utf-8")).hexdigest(),
        "classifier_sha256": hashlib.sha256(Path(classifier.__file__).read_bytes()).hexdigest(),
        "bloom_definitions_sha256": hashlib.sha256(
            classifier.format_bloom_levels_for_prompt().encode("utf-8")
        ).hexdigest(),
        "input_questions": len(questions),
        "requested_runs": args.times,
        "only_unclassified": not args.force,
        "provider": args.provider,
        "model": getattr(classifier, f"{prefix}_MODEL"),
        "temperature": getattr(classifier, f"{prefix}_TEMPERATURE"),
        "max_completion_tokens": getattr(classifier, f"{prefix}_MAX_COMPLETION_TOKENS"),
        "batch_size": classifier.CLASSIFICATION_BATCH_SIZE,
        "batch_delay_seconds": delay,
        "retry_delay_seconds": classifier.CLASSIFICATION_REQUEST_DELAY_SECONDS,
        "max_attempts_per_batch": classifier.CLASSIFICATION_MAX_RETRIES,
        "deepseek_thinking_enabled": classifier.DEEPSEEK_THINKING_ENABLED if is_deepseek else None,
        "deepseek_reasoning_effort": classifier.DEEPSEEK_REASONING_EFFORT if is_deepseek else None,
        "sdk_automatic_retries": False,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
    }


def build_run_metrics(run, started_at, status, error, output_path,
                      question_count, total, metrics) -> dict:
    api = sum(item["seconds"] for item in metrics.requests)
    batch_wait = sum(item["seconds"] for item in metrics.waits if item["reason"] == "between_batches")
    retry_wait = sum(item["seconds"] for item in metrics.waits if item["reason"] == "rate_limit")
    completed = metrics.completed_questions
    return {
        "run": run, "started_at": started_at, "status": status,
        "input_questions": question_count,
        "pending_questions": metrics.pending_questions,
        "classified_questions": completed,
        "skipped_questions": question_count - metrics.pending_questions,
        "batches": len({item["batch"] for item in metrics.requests}),
        "request_attempts": len(metrics.requests),
        "retries": sum(item["attempt"] > 1 for item in metrics.requests),
        "failed_requests": sum(
            bool(item["error"]) or (item["status_code"] or 0) >= 400
            for item in metrics.requests
        ),
        "total_seconds": total, "api_seconds": api,
        "batch_wait_seconds": batch_wait, "retry_wait_seconds": retry_wait,
        "other_seconds": max(0.0, total - api - batch_wait - retry_wait),
        # Não atribuir produtividade completa a execuções parciais ou puladas.
        "seconds_per_question": total / completed if status == "success" and completed else None,
        "api_seconds_per_question": api / completed if status == "success" and completed else None,
        "questions_per_minute": completed * 60 / total if status == "success" and completed and total else None,
        "error": error,
        "output_file": str(output_path) if status != "failed" else "",
    }


def report_path(base: Path, name: str, suffix: str) -> Path:
    return base.with_name(f"{base.stem}_{name}{suffix}")


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(base: Path, settings: dict, runs: list[dict],
                  requests: list[dict], waits: list[dict]) -> None:
    write_csv(report_path(base, "metrics", ".csv"), RUN_FIELDS, runs)
    write_csv(report_path(base, "requests", ".csv"), REQUEST_FIELDS, requests)
    write_csv(report_path(base, "waits", ".csv"), WAIT_FIELDS, waits)
    successful = [row for row in runs if row["status"] == "success"]
    statistics = {}
    for field_name in TIME_FIELDS:
        values = [row[field_name] for row in successful if row[field_name] is not None]
        statistics[field_name] = {
            "count": len(values),
            "mean": mean(values) if values else None,
            "median": median(values) if values else None,
            "sample_stddev": stdev(values) if len(values) > 1 else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    summary = {
        "settings": settings,
        "completed_runs": len(runs),
        "successful_runs": len(successful),
        "failed_runs": sum(row["status"] == "failed" for row in runs),
        "skipped_runs": sum(row["status"] == "skipped" for row in runs),
        "failure_rate": sum(row["status"] == "failed" for row in runs) / len(runs),
        "statistics_scope": "Somente execuções bem-sucedidas com questões classificadas.",
        "timing_scope": "Classificação completa, incluindo validação e esperas; exclui leitura e gravação dos arquivos.",
        "per_question_scope": "Tempo amortizado por questão classificada; não é latência individual.",
        "request_scope": "Tempo por tentativa, incluindo rede e processamento do cliente/SDK; exclui esperas e validação das classificações.",
        "sample_stddev_scope": "Desvio padrão amostral; null com menos de duas execuções bem-sucedidas.",
        "statistics": statistics,
        "runs": runs,
    }
    report_path(base, "summary", ".json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
