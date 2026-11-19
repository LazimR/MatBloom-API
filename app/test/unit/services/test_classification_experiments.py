import argparse
import asyncio
import csv
import json
from copy import deepcopy

import pytest

from scripts import run_classification_experiments as experiments


def source_questions():
    return [{
        "enunciation": f"Questão {i}", "itens": ["A", "B"],
        "correct_item": 0, "level": 0, "contents": ["Conteúdo"],
    } for i in range(20)]


def options(tmp_path, repetitions=2, reference=None):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(source_questions()))
    return argparse.Namespace(input=path, output=tmp_path / "results", repetitions=repetitions, reference=reference)


def test_plan_is_reproducible_balanced_and_changes_all_neighbors():
    plan = experiments.build_plan(10)
    assert len(plan) == 50
    assert plan == experiments.build_plan(10)
    permutations = set()
    for run in range(1, 11):
        jobs = [job for job in plan if job["run"] == run]
        assert {job["condition"] for job in jobs} == {"lote_1", "lote_2", "lote_5", "lote_10", "embaralhado"}
        for job in jobs:
            positions = job["positions"]
            assert sorted(positions) == list(range(20))
            if job["condition"] == "embaralhado":
                assert all(i != original for i, original in enumerate(positions))
                assert all(positions[i] // 2 != positions[i + 1] // 2 for i in range(0, 20, 2))
                permutations.add(tuple(positions))
    assert len(permutations) == 10


def test_resume_does_not_accept_changed_input_or_configuration(tmp_path, monkeypatch):
    args = options(tmp_path)
    manifest = experiments.prepare(args)
    assert experiments.prepare(args) == manifest
    monkeypatch.setattr(experiments.classifier, "DEEPSEEK_TEMPERATURE", 0.567)
    with pytest.raises(ValueError, match="Configuração mudou"):
        experiments.prepare(args)


def test_reference_requires_aligned_questions_or_twenty_valid_levels(tmp_path):
    path = tmp_path / "reference.json"
    path.write_text(json.dumps({"levels": [1] * 20}))
    assert experiments.load_reference(path, source_questions()) == [1] * 20
    path.write_text(json.dumps({"levels": [0] * 20}))
    with pytest.raises(ValueError, match="20 níveis"):
        experiments.load_reference(path, source_questions())
    swapped = source_questions()
    swapped[0], swapped[1] = swapped[1], swapped[0]
    path.write_text(json.dumps(swapped))
    with pytest.raises(ValueError, match="ordem original"):
        experiments.load_reference(path, source_questions())


def test_execution_restores_batch_size_and_analysis_matches_question_identity(tmp_path, monkeypatch):
    args = options(tmp_path, repetitions=1)
    manifest = experiments.prepare(args)
    previous_size = experiments.classifier.CLASSIFICATION_BATCH_SIZE
    original_input = deepcopy(manifest["questions"])

    async def fake_api(prompt, provider=None, metrics=None):
        questions = json.loads(prompt.split("**Questões para classificar**")[-1])
        metrics.requests.append({
            "attempt": 1, "status_code": 200, "error": "", "batch": metrics.batch,
            "questions": len(questions), "seconds": 0.0,
        })
        return {"classifications": [{"index": q["index"], "level": int(q["enunciation"].split()[-1]) % 6 + 1} for q in questions]}

    monkeypatch.setattr(experiments.classifier, "_call_classification_api", fake_api)
    manifest["settings"]["batch_delay_seconds"] = 0
    for job in manifest["plan"]:
        record = asyncio.run(experiments.execute_job(args.output, manifest, job))
        assert record["metrics"]["classified_questions"] == 20
        assert experiments.classifier.CLASSIFICATION_BATCH_SIZE == previous_size
    assert manifest["questions"] == original_input
    experiments.analyze(args.output, manifest)
    summary = json.loads((args.output / "ordem_agrupamento/resumo.json").read_text())
    shuffled = next(c for c in summary["conditions"] if c["condition"] == "embaralhado")
    assert shuffled["changed_vs_control"] == 0
    assert shuffled["compared_vs_control"] == 20
    assert shuffled["accuracy_percent"] is None
    assert shuffled["accuracy_evaluated"] == 0
    with (args.output / "ordem_agrupamento/por_questao.csv").open() as file:
        rows = [r for r in csv.DictReader(file) if r["condition"] == "embaralhado"]
    assert len(rows) == 20
    assert all(r["input_position"] != r["original_position"] for r in rows)
    manifest["reference_levels"] = [i % 6 + 1 for i in range(20)]
    experiments.analyze(args.output, manifest)
    summary = json.loads((args.output / "ordem_agrupamento/resumo.json").read_text())
    assert all(c["accuracy_percent"] == 100 for c in summary["conditions"])
    progress = json.loads((args.output / "progresso.json").read_text())
    assert progress["status"] == "complete"
    assert progress["completed_jobs"] == 5  # Controle compartilhado não conta duas vezes.


def test_failed_incomplete_execution_is_not_in_timing_statistics(tmp_path, monkeypatch):
    args = options(tmp_path, repetitions=1)
    manifest = experiments.prepare(args)
    job = next(j for j in manifest["plan"] if j["condition"] == "lote_10")

    async def incomplete_api(prompt, provider=None, metrics=None):
        return {"classifications": [{"index": 0, "level": 3}]}

    monkeypatch.setattr(experiments.classifier, "_call_classification_api", incomplete_api)
    record = asyncio.run(experiments.execute_job(args.output, manifest, job))
    assert record["metrics"]["status"] == "failed"
    assert record["metrics"]["failure_category"] == "incomplete_response"
    experiments.analyze(args.output, manifest)
    summary = json.loads((args.output / "tamanho_lote/resumo.json").read_text())
    condition = next(c for c in summary["conditions"] if c["condition"] == "lote_10")
    assert condition["failed_runs"] == 1
    assert condition["incomplete_responses"] == 1
    assert condition["statistics"]["api_seconds"]["count"] == 0
    assert condition["compared_vs_control"] == 0
