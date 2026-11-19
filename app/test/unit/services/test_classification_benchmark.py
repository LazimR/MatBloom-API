import asyncio
import csv
import json
import sys
from types import SimpleNamespace

import httpx
import pytest

from app.api.services import question_classifier as classifier
from scripts import classify_questions_repeat as benchmark


def questions(count=1, level=0):
    return [
        {"enunciation": f"Calcule {index} + 2", "itens": ["2", "3"],
         "correct_item": 0, "level": level, "contents": ["Adição"]}
        for index in range(count)
    ]


def response_payload(count=1):
    content = {"classifications": [{"index": i, "level": 3} for i in range(count)]}
    return {"choices": [{"message": {"content": json.dumps(content)}}]}


@pytest.fixture
def clock(monkeypatch):
    state = SimpleNamespace(seconds=0.0)

    def now():
        return state.seconds

    async def sleep(seconds):
        # Simula também um pequeno atraso no agendamento da espera.
        state.seconds += seconds + 0.1

    monkeypatch.setattr(classifier, "perf_counter", now)
    monkeypatch.setattr(benchmark, "perf_counter", now)
    monkeypatch.setattr(classifier.asyncio, "sleep", sleep)
    monkeypatch.setattr(classifier, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(classifier, "CLASSIFICATION_BATCH_SIZE", 2)
    monkeypatch.setattr(classifier, "CLASSIFICATION_MAX_RETRIES", 2)
    return state


def mock_groq(monkeypatch, handler):
    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(classifier.httpx, "AsyncClient", lambda: original_client(transport=transport))


def test_tracks_groq_attempts_and_measured_waits_separately(monkeypatch, clock):
    calls = []

    async def handler(request):
        calls.append(request)
        clock.seconds += 1
        if len(calls) == 1:
            return httpx.Response(429, text="Please try again in 1s")
        return httpx.Response(200, json=response_payload(2 if len(calls) == 2 else 1))

    mock_groq(monkeypatch, handler)
    metrics = classifier.ClassificationMetrics()
    result = asyncio.run(classifier.classify_questions_batch(
        questions(3), provider="groq", request_delay_seconds=3, metrics=metrics,
    ))

    assert [q["level"] for q in result] == [3, 3, 3]
    assert metrics.pending_questions == metrics.completed_questions == 3
    assert [r["status_code"] for r in metrics.requests] == [429, 200, 200]
    assert [r["batch"] for r in metrics.requests] == [1, 1, 2]
    assert [r["attempt"] for r in metrics.requests] == [1, 2, 1]
    assert [r["seconds"] for r in metrics.requests] == pytest.approx([1, 1, 1])
    assert [w["reason"] for w in metrics.waits] == ["rate_limit", "between_batches"]
    assert [w["seconds"] for w in metrics.waits] == pytest.approx([2.1, 3.1])
    row = benchmark.build_run_metrics(1, "now", "success", "", "result.json", 3, clock.seconds, metrics)
    assert row["total_seconds"] == pytest.approx(8.2)
    assert row["api_seconds"] == pytest.approx(3)
    assert row["retries"] == row["failed_requests"] == 1
    assert row["seconds_per_question"] == pytest.approx(8.2 / 3)
    assert row["other_seconds"] == pytest.approx(0)


def test_tracks_deepseek_retries_without_hidden_sdk_attempts(monkeypatch, clock):
    monkeypatch.setattr(classifier, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(classifier, "CLASSIFICATION_REQUEST_DELAY_SECONDS", 4)
    state = SimpleNamespace(calls=0, closed=False, kwargs=None)

    async def create(**kwargs):
        state.calls += 1
        clock.seconds += 2
        if state.calls == 1:
            response = httpx.Response(429, request=httpx.Request("POST", "https://example.test"))
            raise classifier.RateLimitError("limit", response=response, body=None)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({"classifications": [{"index": 0, "level": 3}]}))
        )])

    async def close():
        state.closed = True

    def client(**kwargs):
        state.kwargs = kwargs
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=close)

    monkeypatch.setattr(classifier, "AsyncOpenAI", client)
    metrics = classifier.ClassificationMetrics()
    asyncio.run(classifier.classify_questions_batch(questions(), provider="deepseek", metrics=metrics))

    assert state.kwargs["max_retries"] == 0
    assert state.closed
    assert [r["status_code"] for r in metrics.requests] == [429, 200]
    assert metrics.requests[0]["error"] == "RateLimitError"
    assert metrics.waits[0]["seconds"] == pytest.approx(4.1)
    assert metrics.completed_questions == 1


def test_reports_failure_and_continues_with_same_input(monkeypatch, clock, tmp_path):
    input_path = tmp_path / "questions.json"
    input_path.write_text(json.dumps(questions()))
    base = tmp_path / "results" / "run.json"
    metrics_path = base.with_name("run_metrics.csv")
    calls = []

    async def handler(request):
        calls.append(request)
        clock.seconds += 1
        if len(calls) == 1:
            return httpx.Response(500, text="temporary failure")
        # A falha anterior já deve estar persistida antes da próxima chamada.
        assert metrics_path.exists()
        return httpx.Response(200, json=response_payload())

    mock_groq(monkeypatch, handler)
    monkeypatch.setattr(sys, "argv", ["benchmark", str(input_path), "3", "--provider", "groq", "-o", str(base)])
    assert asyncio.run(benchmark.main()) == 1

    with metrics_path.open() as file:
        rows = list(csv.DictReader(file))
    assert [row["status"] for row in rows] == ["failed", "success", "success"]
    assert [row["classified_questions"] for row in rows] == ["0", "1", "1"]
    assert rows[0]["seconds_per_question"] == ""
    assert rows[0]["failed_requests"] == "1"
    summary = json.loads(base.with_name("run_summary.json").read_text())
    assert summary["successful_runs"] == 2
    assert summary["failed_runs"] == 1
    assert summary["failure_rate"] == pytest.approx(1 / 3)
    assert summary["statistics"]["total_seconds"] == {
        "count": 2, "mean": 1, "median": 1, "sample_stddev": 0, "min": 1, "max": 1,
    }
    assert summary["settings"]["input_questions"] == 1
    assert summary["settings"]["provider"] == "groq"
    assert json.loads(input_path.read_text()) == questions()
    assert not base.with_name("run_1.json").exists()
    assert base.with_name("run_2.json").exists()
    assert base.with_name("run_3.json").exists()
    with base.with_name("run_requests.csv").open() as file:
        assert len(list(csv.DictReader(file))) == 3


@pytest.mark.parametrize("force", [False, True])
def test_already_classified_inputs_do_not_create_false_measurements(monkeypatch, clock, tmp_path, force):
    input_path = tmp_path / "questions.json"
    input_path.write_text(json.dumps(questions(level=2)))
    calls = []

    async def handler(request):
        calls.append(request)
        clock.seconds += 1
        return httpx.Response(200, json=response_payload())

    mock_groq(monkeypatch, handler)
    argv = ["benchmark", str(input_path), "1", "--provider", "groq"]
    monkeypatch.setattr(sys, "argv", argv + (["--force"] if force else []))
    assert asyncio.run(benchmark.main()) == 0
    summary = json.loads((tmp_path / "questions_classificadas_summary.json").read_text())
    assert len(calls) == int(force)
    assert summary["successful_runs"] == int(force)
    assert summary["skipped_runs"] == int(not force)
    assert summary["statistics"]["total_seconds"]["count"] == int(force)
    assert summary["statistics"]["total_seconds"]["sample_stddev"] is None


def test_invalid_model_response_records_network_time_without_completed_questions(monkeypatch, clock):
    async def handler(request):
        clock.seconds += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "invalid JSON"}}]})

    mock_groq(monkeypatch, handler)
    metrics = classifier.ClassificationMetrics()
    with pytest.raises(Exception, match="JSON válido"):
        asyncio.run(classifier.classify_questions_batch(questions(), provider="groq", metrics=metrics))
    assert len(metrics.requests) == 1
    assert metrics.requests[0]["seconds"] == 1
    assert metrics.completed_questions == 0


def test_retry_exhaustion_preserves_partial_counts_and_excludes_productivity(monkeypatch, clock):
    calls = []

    async def handler(request):
        calls.append(request)
        clock.seconds += 1
        if len(calls) == 1:
            return httpx.Response(200, json=response_payload(2))
        return httpx.Response(429, text="try again in 1s")

    mock_groq(monkeypatch, handler)
    metrics = classifier.ClassificationMetrics()
    with pytest.raises(Exception, match="429"):
        asyncio.run(classifier.classify_questions_batch(
            questions(3), provider="groq", request_delay_seconds=0, metrics=metrics,
        ))
    assert metrics.pending_questions == 3
    assert metrics.completed_questions == 2
    assert [r["attempt"] for r in metrics.requests] == [1, 1, 2]
    assert len(metrics.waits) == 1
    row = benchmark.build_run_metrics(1, "now", "failed", "rate limit", "output.json", 3, clock.seconds, metrics)
    assert row["failed_requests"] == 2
    assert row["seconds_per_question"] is None
    assert row["questions_per_minute"] is None


def test_summary_has_no_timing_statistics_when_all_runs_fail(monkeypatch, clock, tmp_path):
    input_path = tmp_path / "questions.json"
    input_path.write_text(json.dumps(questions()))

    async def handler(request):
        clock.seconds += 1
        raise httpx.ConnectError("offline", request=request)

    mock_groq(monkeypatch, handler)
    monkeypatch.setattr(sys, "argv", ["benchmark", str(input_path), "2", "--provider", "groq"])
    assert asyncio.run(benchmark.main()) == 1
    summary = json.loads((tmp_path / "questions_classificadas_summary.json").read_text())
    assert summary["failed_runs"] == 2
    assert summary["failure_rate"] == 1
    assert summary["statistics"]["total_seconds"]["mean"] is None
    assert summary["statistics"]["total_seconds"]["count"] == 0
    assert summary["runs"][0]["request_attempts"] == 1
    assert summary["runs"][0]["failed_requests"] == 1
