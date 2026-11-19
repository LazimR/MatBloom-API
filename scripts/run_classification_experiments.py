#!/usr/bin/env python3
"""Executa e retoma experimentos de lote e de ordem, com identidade das questões.

poetry run python scripts/run_classification_experiments.py
poetry run python scripts/run_classification_experiments.py --prepare-only
poetry run python scripts/run_classification_experiments.py --analyze-only

As dez repetições padrão usam as mesmas 20 questões. A entrada e o .env não
são alterados. O controle de ordem é a rodada de lote 2 do mesmo bloco.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sys
import fcntl
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.services import question_classifier as classifier
from scripts import classify_questions_repeat as benchmark

SEED = 20261015
BATCH_SIZES = (1, 2, 5, 10)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(payload) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def shuffled_positions(count: int, seed: int) -> list[int]:
    """Muda a posição e o colega de lote de cada questão, mantendo lotes de 2."""
    rng = random.Random(seed)
    for _ in range(10000):
        positions = list(range(count))
        rng.shuffle(positions)
        if all(position != original for position, original in enumerate(positions)) and all(
            positions[i] // 2 != positions[i + 1] // 2 for i in range(0, count, 2)
        ):
            return positions
    raise ValueError("Não foi possível gerar a permutação com as restrições pedidas.")


def build_plan(repetitions: int, count: int = 20) -> list[dict]:
    plan = []
    for run in range(1, repetitions + 1):
        block = [
            {"experiment": "tamanho_lote", "condition": f"lote_{size}", "batch_size": size,
             "run": run, "seed": None, "positions": list(range(count))}
            for size in BATCH_SIZES
        ]
        block.append({
            "experiment": "ordem_agrupamento", "condition": "embaralhado", "batch_size": 2,
            "run": run, "seed": SEED + run,
            "positions": shuffled_positions(count, SEED + run),
        })
        # Intercala condições para reduzir a associação de uma condição com um horário.
        random.Random(SEED + 1000 + run).shuffle(block)
        for job in block:
            job["id"] = f"{job['experiment']}/{job['condition']}/rodada_{run:02d}"
        plan.extend(block)
    return plan


def record_path(root: Path, job: dict) -> Path:
    return root / f"{job['id']}_registro.json"


def canonical_levels(record: dict) -> dict[int, int]:
    if record["metrics"]["status"] != "success":
        return {}
    return {original: question["level"] for original, question in zip(
        record["job"]["positions"], record["questions"], strict=True,
    )}


def load_reference(path: Path | None, questions: list[dict]) -> list[int] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "levels" in payload:
        levels = payload["levels"]
    else:
        items = classifier.load_questions_from_payload(payload)
        if len(items) != len(questions) or any(
            item["enunciation"] != question["enunciation"] for item, question in zip(items, questions)
        ):
            raise ValueError("A referência deve conter as mesmas questões, na ordem original.")
        levels = [item["level"] for item in items]
    if not isinstance(levels, list) or len(levels) != len(questions) or any(
        type(level) is not int or level not in range(1, 7) for level in levels
    ):
        raise ValueError("A referência deve informar exatamente 20 níveis inteiros entre 1 e 6.")
    return levels


def prepare(args) -> dict:
    questions = benchmark.load_questions(args.input)
    if len(questions) != 20:
        raise ValueError("Estes experimentos exigem exatamente 20 questões.")
    for index, question in enumerate(questions, start=1):
        classifier._validate_input_question(question, index)
    if args.repetitions <= 0 or classifier.CLASSIFICATION_REQUEST_DELAY_SECONDS < 0:
        raise ValueError("Repetições devem ser positivas e o intervalo não pode ser negativo.")
    # Todos os itens devem ser classificados, mesmo que a entrada possua níveis antigos.
    questions = [{**deepcopy(question), "level": 0} for question in questions]
    settings = benchmark.experiment_settings(
        argparse.Namespace(provider="deepseek", times=args.repetitions, force=True),
        args.input, questions, classifier.CLASSIFICATION_REQUEST_DELAY_SECONDS,
    )
    manifest = {
        "created_at": timestamp(), "settings": settings, "seed": SEED,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "questions": questions, "plan": build_plan(args.repetitions),
        "control": "tamanho_lote/lote_2, mesma repetição; compartilhado sem nova chamada",
        "reference_file": str(args.reference.resolve()) if args.reference else None,
        "reference_levels": load_reference(args.reference, questions),
    }
    manifest_path = args.output / "experimentos_manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("questions", "plan", "seed", "runner_sha256"):
            if previous[key] != manifest[key]:
                raise ValueError(f"Configuração mudou ({key}). Use outra pasta para uma nova coleta.")
        for key, value in settings.items():
            if key not in {"started_at", "input_file"} and previous["settings"].get(key) != value:
                raise ValueError(f"Configuração mudou ({key}). Use outra pasta para uma nova coleta.")
        if args.reference:
            previous["reference_file"] = manifest["reference_file"]
            previous["reference_levels"] = manifest["reference_levels"]
            write_json(manifest_path, previous)
        return previous
    write_json(manifest_path, manifest)
    for experiment in ("tamanho_lote", "ordem_agrupamento"):
        write_json(args.output / experiment / "questoes_originais.json", questions)
    for job in manifest["plan"]:
        ordered = [questions[index] for index in job["positions"]]
        write_json(args.output / f"{job['id']}_entrada.json", {
            "questions": ordered,
            "original_positions": [index + 1 for index in job["positions"]],
            "seed": job["seed"],
        })
    return manifest


def failure_category(error: str) -> str:
    if not error:
        return ""
    if "não classificou todas" in error:
        return "incomplete_response"
    if "content vazio" in error:
        return "empty_response"
    if any(fragment in error for fragment in ("JSON", "index inválido", "nível Bloom inválido", "mais de uma vez", "classificações válidas")):
        return "invalid_response"
    if "Timeout" in error:
        return "timeout"
    return "api_or_processing_error"


async def execute_job(root: Path, manifest: dict, job: dict) -> dict:
    questions = [deepcopy(manifest["questions"][index]) for index in job["positions"]]
    metrics = classifier.ClassificationMetrics()
    previous_size = classifier.CLASSIFICATION_BATCH_SIZE
    classifier.CLASSIFICATION_BATCH_SIZE = job["batch_size"]
    started_at = timestamp()
    started = perf_counter()
    result = None
    error = ""
    try:
        result = await classifier.classify_questions_batch(
            questions, only_unclassified=False, provider="deepseek",
            request_delay_seconds=manifest["settings"]["batch_delay_seconds"], metrics=metrics,
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        total = perf_counter() - started
        classifier.CLASSIFICATION_BATCH_SIZE = previous_size
    output = root / f"{job['id']}_resultado.json"
    row = benchmark.build_run_metrics(
        job["run"], started_at, "failed" if error else "success", error,
        output, len(questions), total, metrics,
    )
    row["failure_category"] = failure_category(error)
    if result is not None:
        write_json(output, {"questions": result})
    record = {
        "job": job, "metrics": row, "questions": result,
        "requests": metrics.requests, "waits": metrics.waits, "finished_at": timestamp(),
    }
    write_json(record_path(root, job), record)
    return record


def stats(values: list[float]) -> dict:
    return {
        "count": len(values), "mean": mean(values) if values else None,
        "median": median(values) if values else None,
        "sample_stddev": stdev(values) if len(values) > 1 else None,
        "min": min(values) if values else None, "max": max(values) if values else None,
    }


def percent(numerator: int, denominator: int) -> float | None:
    return numerator * 100 / denominator if denominator else None


def fmt(number, places=3) -> str:
    return "pendente" if number is None else f"{number:.{places}f}".replace(".", ",")


def analyze(root: Path, manifest: dict) -> None:
    records = []
    for job in manifest["plan"]:
        path = record_path(root, job)
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["job"] != job:
                raise ValueError(f"O registro não corresponde ao plano: {path}")
            records.append(record)
    controls = {r["job"]["run"]: r for r in records if r["job"]["condition"] == "lote_2"}
    control_distributions = {original: Counter() for original in range(20)}
    for record in controls.values():
        for original, level in canonical_levels(record).items():
            control_distributions[original][level] += 1
    control_stability = {
        "successful_runs": sum(r["metrics"]["status"] == "success" for r in controls.values()),
        "variable_questions": [f"Q{i + 1:03d}" for i, counts in control_distributions.items() if len(counts) > 1],
        "levels_by_question": {f"Q{i + 1:03d}": dict(counts) for i, counts in control_distributions.items()},
    }
    reference = manifest["reference_levels"]
    for experiment in ("tamanho_lote", "ordem_agrupamento"):
        selected = [r for r in records if r["job"]["experiment"] == experiment]
        if experiment == "ordem_agrupamento":
            selected = list(controls.values()) + selected
            for record in controls.values():
                write_json(root / experiment / "original" / f"rodada_{record['job']['run']:02d}_registro.json", {
                    **record, "shared_control_from": record["job"]["id"],
                })
        rows, details, conditions = [], [], []
        names = [f"lote_{size}" for size in BATCH_SIZES] if experiment == "tamanho_lote" else ["original", "embaralhado"]
        for name in names:
            condition_records = [r for r in selected if (
                (r["job"]["condition"] == "lote_2" and name == "original") or r["job"]["condition"] == name
            )]
            valid = [r for r in condition_records if r["metrics"]["status"] == "success"]
            correct = evaluated = changes = compared = 0
            for record in condition_records:
                row = {"condition": name, **record["metrics"]}
                rows.append(row)
                levels = canonical_levels(record)
                control = canonical_levels(controls[record["job"]["run"]]) if record["job"]["run"] in controls else {}
                for position, original in enumerate(record["job"]["positions"]):
                    if original not in levels:
                        continue
                    level = levels[original]
                    baseline = control.get(original)
                    expected = reference[original] if reference else None
                    if expected is not None:
                        correct += level == expected
                        evaluated += 1
                    if baseline is not None:
                        changes += level != baseline
                        compared += 1
                    details.append({
                        "condition": name, "run": record["job"]["run"],
                        "question_id": f"Q{original + 1:03d}", "original_position": original + 1,
                        "input_position": position + 1,
                        "batch": position // record["job"]["batch_size"] + 1,
                        "position_in_batch": position % record["job"]["batch_size"] + 1,
                        "level": level, "control_level": baseline,
                        "changed": level != baseline if baseline is not None else None,
                        "reference_level": expected,
                        "correct": level == expected if expected is not None else None,
                    })
            conditions.append({
                "condition": name, "completed_runs": len(condition_records), "successful_runs": len(valid),
                "failed_runs": len(condition_records) - len(valid),
                "success_rate_percent": percent(len(valid), len(condition_records)),
                "incomplete_responses": sum(r["metrics"]["failure_category"] == "incomplete_response" for r in condition_records),
                "invalid_or_empty_responses": sum(r["metrics"]["failure_category"] in {"invalid_response", "empty_response"} for r in condition_records),
                "request_attempts": sum(r["metrics"]["request_attempts"] for r in condition_records),
                "retries": sum(r["metrics"]["retries"] for r in condition_records),
                "accuracy_percent": percent(correct, evaluated), "accuracy_evaluated": evaluated,
                "changed_vs_control": changes, "compared_vs_control": compared,
                "changed_percent": percent(changes, compared),
                "statistics": {field: stats([r["metrics"][field] for r in valid]) for field in benchmark.TIME_FIELDS},
            })
        folder = root / experiment
        benchmark.write_csv(folder / "metricas.csv", ["condition", *benchmark.RUN_FIELDS, "failure_category"], rows)
        benchmark.write_csv(folder / "por_questao.csv", [
            "condition", "run", "question_id", "original_position", "input_position", "batch", "position_in_batch",
            "level", "control_level", "changed", "reference_level", "correct",
        ], details)
        for kind, fields in (("requests", benchmark.REQUEST_FIELDS), ("waits", benchmark.WAIT_FIELDS)):
            traces = []
            for record in selected:
                name = "original" if experiment == "ordem_agrupamento" and record["job"]["condition"] == "lote_2" else record["job"]["condition"]
                traces.extend({"condition": name, "run": record["job"]["run"], **item} for item in record[kind])
            benchmark.write_csv(folder / f"{kind}.csv", ["condition", *fields], traces)
        summary = {
            "updated_at": timestamp(), "planned_runs_per_condition": manifest["settings"]["requested_runs"],
            "accuracy_status": "Referência humana fornecida" if reference else "Pendente: referência humana não fornecida; concordância com controle não é acurácia",
            "control_source": manifest["control"], "control_stability": control_stability,
            "settings": manifest["settings"], "conditions": conditions,
        }
        write_json(folder / "resumo.json", summary)
        lines = [
            f"EXPERIMENTO: {experiment}", f"Atualizado em UTC: {summary['updated_at']}",
            f"Modelo: {manifest['settings']['model']}; temperatura: {manifest['settings']['temperature']}.",
            "Cada execução classifica as mesmas 20 questões. Os tempos são medidos em segundos.",
            "As estatísticas de tempo consideram somente execuções concluídas com sucesso.",
            summary["accuracy_status"], "",
            "Condição | Rodadas | Sucessos | API média (s) | API/questão (s) | Total médio (s) | Mudanças/controle",
        ]
        for condition in conditions:
            s = condition["statistics"]
            lines.append(
                f"{condition['condition']} | {condition['completed_runs']} | {condition['successful_runs']} | "
                f"{fmt(s['api_seconds']['mean'])} | {fmt(s['api_seconds_per_question']['mean'])} | "
                f"{fmt(s['total_seconds']['mean'])} | {condition['changed_vs_control']}/{condition['compared_vs_control']}"
            )
        lines.extend([
            "", "INTERPRETAÇÃO E LIMITAÇÕES",
            f"As condições são intercaladas em {manifest['settings']['requested_runs']} blocos com ordem de execução aleatorizada e sementes registradas.",
            "O controle é a execução original de lote 2 no mesmo bloco; seu resultado é compartilhado pelos dois experimentos.",
            "Na condição original/lote_2, a diferença contra si mesma é zero por definição; não representa estabilidade entre rodadas.",
            f"Questões com variação entre rodadas bem-sucedidas do controle: {', '.join(control_stability['variable_questions']) or 'nenhuma observada até o momento'}.",
            "O campo changed compara a mesma identidade Q001 a Q020, após restaurar a ordem original.",
            "Nas permutações, todas as questões mudam de posição e de colega de lote. Isso mede o efeito conjunto de ordem e agrupamento.",
            "Uma diferença pode também refletir a variabilidade normal do modelo; não demonstra causalidade isolada de posição ou de colega.",
            "Concordância com o controle não equivale a acurácia pedagógica. Nenhum nível de referência foi inventado.",
            "O tempo de API inclui rede e SDK. O tempo total inclui as esperas necessárias entre lotes.",
            "Os níveis de uma mesma questão em várias rodadas não são amostras de questões distintas.",
            "Uma execução com falha não é reexecutada silenciosamente; permanece registrada. Retomar pula as rodadas já registradas.",
        ])
        (folder / "analise.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(root / "progresso.json", {
        "updated_at": timestamp(), "planned_jobs": len(manifest["plan"]), "completed_jobs": len(records),
        "successful_jobs": sum(r["metrics"]["status"] == "success" for r in records),
        "failed_jobs": sum(r["metrics"]["status"] == "failed" for r in records),
        "status": "complete" if len(records) == len(manifest["plan"]) else "in_progress",
    })


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "scripts/questoes/quest_20.json")
    parser.add_argument("--output", type=Path, default=ROOT / "resultados")
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--reference", type=Path, help="JSON de referência humana: questões na ordem original ou {levels: [...]}.")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    lock_file = None
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        lock_file = (args.output / ".classification_experiments.lock").open("a")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Já existe uma coleta em execução nesta pasta. Consulte progresso.json.") from exc
        manifest = prepare(args)
        analyze(args.output, manifest)
        if args.prepare_only or args.analyze_only:
            print(f"Plano e relatórios: {args.output.resolve()}", flush=True)
            return 0
        if not classifier.DEEPSEEK_API_KEY or not classifier.DEEPSEEK_API_KEY.strip():
            raise ValueError("DEEPSEEK_API_KEY não configurada; nenhuma chamada foi executada.")
        consecutive_failures = 0
        for number, job in enumerate(manifest["plan"], start=1):
            if record_path(args.output, job).exists():
                continue
            print(f"[{number}/{len(manifest['plan'])}] INÍCIO {job['id']}, lote={job['batch_size']}", flush=True)
            write_json(args.output / "progresso.json", {
                **json.loads((args.output / "progresso.json").read_text()),
                "current_job": job["id"], "current_job_started_at": timestamp(),
            })
            record = await execute_job(args.output, manifest, job)
            analyze(args.output, manifest)
            row = record["metrics"]
            print(f"[{number}/{len(manifest['plan'])}] {row['status']}: API={row['api_seconds']:.3f}s total={row['total_seconds']:.3f}s {row['error']}", flush=True)
            consecutive_failures = consecutive_failures + 1 if row["status"] == "failed" else 0
            # Evita continuar enviando chamadas quando há bloqueio persistente de acesso/rede.
            if consecutive_failures >= 3 or any(r["status_code"] in {401, 402, 403, 404} for r in record["requests"]):
                progress_path = args.output / "progresso.json"
                write_json(progress_path, {
                    **json.loads(progress_path.read_text()), "status": "interrupted",
                    "reason": row["error"],
                })
                print("Coleta interrompida após falhas persistentes/de acesso. Os registros foram preservados.", flush=True)
                return 1
        print("Coleta concluída. Consulte tamanho_lote/analise.txt e ordem_agrupamento/analise.txt.", flush=True)
        return 0
    except Exception as exc:
        print(f"Erro: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        if lock_file is not None:
            lock_file.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
