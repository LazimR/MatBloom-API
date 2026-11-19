import asyncio
import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from openai import APIStatusError, AsyncOpenAI, RateLimitError

from app.core.bloom import UNCLASSIFIED_LEVEL, format_bloom_levels_for_prompt, is_classified_level

load_dotenv()

ClassificationProvider = Literal["groq", "deepseek"]

CLASSIFICATION_PROVIDER = os.getenv("CLASSIFICATION_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.1"))
GROQ_MAX_COMPLETION_TOKENS = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "1200"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.1"))
DEEPSEEK_MAX_COMPLETION_TOKENS = int(os.getenv("DEEPSEEK_MAX_COMPLETION_TOKENS", "1200"))
DEEPSEEK_REASONING_EFFORT = os.getenv("DEEPSEEK_REASONING_EFFORT", "high")
DEEPSEEK_THINKING_ENABLED = os.getenv("DEEPSEEK_THINKING_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
}

CLASSIFICATION_BATCH_SIZE = int(os.getenv("CLASSIFICATION_BATCH_SIZE", "2"))
CLASSIFICATION_REQUEST_DELAY_SECONDS = float(
    os.getenv(
        "CLASSIFICATION_REQUEST_DELAY_SECONDS",
        os.getenv("GROQ_REQUEST_DELAY_SECONDS", "25"),
    )
)
CLASSIFICATION_MAX_RETRIES = int(
    os.getenv(
        "CLASSIFICATION_MAX_RETRIES",
        os.getenv("GROQ_MAX_RETRIES", "5"),
    )
)

SYSTEM_MESSAGE = (
    "Você classifica questões de matemática na Taxonomia de Bloom "
    "com base nas descrições cognitivas de cada nível. "
    "Retorne apenas JSON válido e siga exatamente o esquema pedido."
)

REQUIRED_QUESTION_FIELDS = ("enunciation", "itens", "correct_item", "contents")


@dataclass
class ClassificationMetrics:
    """Medições opcionais de uma execução, sem incluir prompts ou chaves de API."""

    requests: list[dict[str, Any]] = field(default_factory=list)
    waits: list[dict[str, Any]] = field(default_factory=list)
    batch: int = 0
    batch_questions: int = 0
    pending_questions: int = 0
    completed_questions: int = 0


@contextmanager
def _measure_request(metrics: ClassificationMetrics | None, attempt: int):
    record: dict[str, Any] = {"attempt": attempt, "status_code": None, "error": ""}
    started = perf_counter()
    try:
        yield record
    except Exception as exc:
        record["error"] = type(exc).__name__
        record["status_code"] = getattr(exc, "status_code", record["status_code"])
        raise
    finally:
        if metrics is not None:
            metrics.requests.append({
                **record,
                "batch": metrics.batch,
                "questions": metrics.batch_questions,
                "seconds": perf_counter() - started,
            })


async def _classification_wait(
    seconds: float,
    reason: str,
    metrics: ClassificationMetrics | None,
) -> None:
    started = perf_counter()
    try:
        await asyncio.sleep(seconds)
    finally:
        if metrics is not None:
            metrics.waits.append({
                "batch": metrics.batch,
                "reason": reason,
                "requested_seconds": seconds,
                "seconds": perf_counter() - started,
            })


def _extract_json_payload(raw_content: str) -> dict | list:
    content = raw_content.strip()
    if content.startswith("```"):
        content = content.removeprefix("```json").removeprefix("```").strip()
        if content.endswith("```"):
            content = content[:-3].strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        decoder = json.JSONDecoder()
        parsed_objects: list[dict] = []
        remaining = content

        while remaining:
            remaining = remaining.lstrip()
            if not remaining:
                break

            try:
                parsed_object, end_index = decoder.raw_decode(remaining)
            except json.JSONDecodeError:
                raise Exception(
                    f"A resposta do modelo não retornou JSON válido. Conteúdo recebido: {raw_content}"
                ) from exc

            if not isinstance(parsed_object, dict):
                raise Exception("A resposta do modelo precisa conter objetos JSON.")

            parsed_objects.append(parsed_object)
            remaining = remaining[end_index:]

        if not parsed_objects:
            raise Exception(
                f"A resposta do modelo não retornou JSON válido. Conteúdo recebido: {raw_content}"
            ) from exc

        merged_classifications: list[dict] = []
        for parsed_object in parsed_objects:
            classifications = parsed_object.get("classifications")
            if isinstance(classifications, list):
                merged_classifications.extend(classifications)

        if not merged_classifications:
            merged_classifications = _extract_partial_classification_objects(content)

        if not merged_classifications:
            raise Exception("Os blocos JSON retornados não contêm classificações válidas.")

        return {"classifications": merged_classifications}

    return parsed


def _extract_partial_classification_objects(content: str) -> list[dict]:
    match = re.search(r'"classifications"\s*:\s*\[', content)
    if not match:
        return []

    index = match.end()
    decoder = json.JSONDecoder()
    extracted: list[dict] = []

    while index < len(content):
        while index < len(content) and content[index] in " \n\r\t,":
            index += 1

        if index >= len(content) or content[index] == "]":
            break

        try:
            parsed_item, end_index = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            break

        if isinstance(parsed_item, dict):
            extracted.append(parsed_item)

        index += end_index

    return extracted


def _validate_input_question(question: dict[str, Any], index: int) -> None:
    if not isinstance(question, dict):
        raise Exception(f"A questão na posição {index} não está em formato de objeto JSON.")

    for field in REQUIRED_QUESTION_FIELDS:
        if field not in question:
            raise Exception(f"A questão na posição {index} está sem o campo '{field}'.")

    enunciation = str(question["enunciation"]).strip()
    itens = question["itens"]
    correct_item = question["correct_item"]
    contents = question["contents"]

    if not enunciation:
        raise Exception(f"A questão na posição {index} veio sem enunciado.")
    if not isinstance(itens, list) or len(itens) < 2:
        raise Exception(f"A questão na posição {index} precisa ter pelo menos duas alternativas.")
    if not isinstance(correct_item, int):
        raise Exception(f"A questão na posição {index} precisa informar correct_item como índice numérico.")
    if correct_item < 0 or correct_item >= len(itens):
        raise Exception(f"A questão na posição {index} possui correct_item fora do intervalo das alternativas.")
    if not isinstance(contents, list) or not contents:
        raise Exception(f"A questão na posição {index} precisa informar ao menos um conteúdo.")


def _normalize_question(question: dict[str, Any]) -> dict[str, Any]:
    level = question.get("level", UNCLASSIFIED_LEVEL)
    if not isinstance(level, int):
        level = UNCLASSIFIED_LEVEL

    return {
        "enunciation": str(question["enunciation"]).strip(),
        "itens": [str(item).strip() for item in question["itens"]],
        "correct_item": question["correct_item"],
        "level": level,
        "contents": [str(content).strip() for content in question["contents"] if str(content).strip()],
    }


def _build_classification_prompt(questions: list[dict[str, Any]]) -> str:
    bloom_lines = format_bloom_levels_for_prompt()

    questions_payload = []
    for index, question in enumerate(questions):
        questions_payload.append(
            {
                "index": index,
                "enunciation": question["enunciation"],
                "itens": question["itens"],
                "contents": question["contents"],
            }
        )

    return f"""
Você é um especialista em Taxonomia de Bloom aplicada à Educação Matemática.

Sua tarefa é classificar cada questão atribuindo o MENOR nível cognitivo necessário para que um estudante responda corretamente.

Retorne SOMENTE JSON válido, sem markdown, sem comentários e sem texto adicional.

**Taxonomia de Bloom utilizada**
{bloom_lines}

**Regras Gerais**

1. Utilize as descrições dos níveis como critério principal de classificação.

2. Determine a ação cognitiva mínima necessária para resolver a questão seguindo o procedimento esperado pelo conteúdo avaliado, Considere o procedimento matemático necessário, e não possíveis atalhos, memorização ou tentativas.

3. Os níveis são hierárquicos:
   - Se uma questão puder ser resolvida utilizando apenas habilidades de um nível inferior, ela NÃO deve ser classificada em um nível superior.

4. Considere exclusivamente o processo cognitivo necessário para chegar à resposta.

5. NÃO considere:
   - tamanho dos números;
   - quantidade de cálculos;
   - dificuldade aritmética;
   - tempo necessário para resolver;
   - aparência de complexidade da questão.

6. Questões equivalentes que exigem o mesmo raciocínio devem receber o mesmo nível, mesmo quando os valores numéricos forem diferentes.

7. Analise:
   - o enunciado;
   - as alternativas;
   - os conteúdos informados.

8. Preserve obrigatoriamente o campo `index`.

9. Não classifique como Lembrar apenas porque alguns estudantes podem ter memorizado o resultado.

10. Ao classificar, considere o menor nível cognitivo que exige a realização de uma ação mental explícita.

**Orientações para Matemática**

Classifique como nível 1 (Lembrar) quando a questão exigir apenas recordar:
- definições;
- fórmulas;
- propriedades;
- fatos matemáticos memorizados.

Classifique como nível 2 (Entender) quando a questão exigir:
- reconhecer representações equivalentes;
- identificar propriedades;
- interpretar conceitos;
- relacionar representações matemáticas;
- compreender significados.

Classifique como nível 3 (Aplicar) quando a questão exigir:
- executar cálculos;
- utilizar fórmulas;
- aplicar propriedades conhecidas;
- seguir procedimentos ou algoritmos já aprendidos.

Classifique como nível 4 (Analisar) somente quando a questão exigir:
- identificar relações entre elementos;
- decompor estruturas matemáticas;
- comparar estratégias;
- examinar padrões;
- selecionar informações relevantes antes da resolução.

Questões que apenas aplicam uma fórmula ou propriedade conhecida NÃO devem ser classificadas como nível 4.

Classifique como nível 5 (Avaliar) quando a questão exigir:
- justificar escolhas;
- validar soluções;
- criticar argumentos;
- julgar procedimentos com base em critérios.

Classifique como nível 6 (Criar) quando a questão exigir:
- elaborar estratégias originais;
- formular problemas;
- construir modelos;
- criar soluções novas.

**Exemplos de Referência**

- Calcular 2^5 → normalmente nível 2 ou 3.
- Aplicar uma propriedade de potenciação → normalmente nível 3.
- Resolver uma equação utilizando procedimento conhecido → normalmente nível 3.
- Comparar dois métodos de resolução → normalmente nível 4.
- Determinar qual solução é mais adequada e justificar → nível 5.
- Criar uma nova situação-problema → nível 6.

**Formato obrigatório de saída**

{{
  "classifications": [
    {{
      "index": 0,
      "level": 3
    }}
  ]
}}

**Questões para classificar**

{json.dumps(questions_payload, ensure_ascii=False, indent=2)}
"""


def _normalize_classifications(
    payload: dict | list,
    expected_count: int,
) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        raw_classifications = payload
    elif isinstance(payload, dict):
        raw_classifications = payload.get("classifications")
    else:
        raise Exception("A resposta do modelo precisa ser um objeto JSON.")

    if not isinstance(raw_classifications, list) or not raw_classifications:
        raise Exception("A resposta do modelo não trouxe classificações válidas.")

    normalized: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()

    for item_index, raw_item in enumerate(raw_classifications, start=1):
        if not isinstance(raw_item, dict):
            raise Exception(f"A classificação {item_index} não está em formato de objeto JSON.")

        index = raw_item.get("index")
        level = raw_item.get("level")

        if not isinstance(index, int) or index < 0 or index >= expected_count:
            raise Exception(f"A classificação {item_index} possui index inválido.")
        if index in seen_indexes:
            raise Exception(f"A classificação para index {index} foi retornada mais de uma vez.")
        if not isinstance(level, int) or not is_classified_level(level):
            raise Exception(f"A classificação {item_index} possui nível Bloom inválido.")

        seen_indexes.add(index)
        normalized.append({"index": index, "level": level})

    if len(normalized) != expected_count:
        missing = sorted(set(range(expected_count)) - seen_indexes)
        raise Exception(f"A resposta do modelo não classificou todas as questões. Faltam os índices: {missing}")

    return sorted(normalized, key=lambda item: item["index"])


def _parse_rate_limit_delay(response_text: str) -> float:
    match = re.search(r"try again in ([\d.]+)s", response_text, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0
    return CLASSIFICATION_REQUEST_DELAY_SECONDS


def _resolve_provider(provider: str | None) -> ClassificationProvider:
    selected = (provider or CLASSIFICATION_PROVIDER).lower()
    if selected not in {"groq", "deepseek"}:
        raise Exception("CLASSIFICATION_PROVIDER deve ser 'groq' ou 'deepseek'.")
    return selected


async def _call_groq_classification(
    prompt: str, metrics: ClassificationMetrics | None = None,
) -> dict | list:
    if not GROQ_API_KEY or not GROQ_API_KEY.strip():
        raise Exception(
            "GROQ_API_KEY não configurada no backend. Defina a chave da Groq para habilitar a classificação."
        )

    last_error: Exception | None = None

    async with httpx.AsyncClient() as client:
        for attempt in range(1, CLASSIFICATION_MAX_RETRIES + 1):
            with _measure_request(metrics, attempt) as measurement:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": [
                            {"role": "system", "content": SYSTEM_MESSAGE},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": GROQ_TEMPERATURE,
                        "max_completion_tokens": GROQ_MAX_COMPLETION_TOKENS,
                    },
                    timeout=60.0,
                )
                measurement["status_code"] = response.status_code

            if response.status_code == 429:
                delay = _parse_rate_limit_delay(response.text)
                if attempt < CLASSIFICATION_MAX_RETRIES:
                    await _classification_wait(delay, "rate_limit", metrics)
                    continue
                last_error = Exception(
                    f"Erro na API Groq: {response.status_code} - {response.text}"
                )
                break

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise Exception(f"Erro na API Groq: {exc.response.status_code} - {exc.response.text}") from exc

            raw_content = response.json()["choices"][0]["message"]["content"]
            return _extract_json_payload(raw_content)

    if last_error:
        raise last_error
    raise Exception("Erro na API Groq: limite de tentativas excedido.")


async def _call_deepseek_classification(
    prompt: str, metrics: ClassificationMetrics | None = None,
) -> dict | list:
    if not DEEPSEEK_API_KEY or not DEEPSEEK_API_KEY.strip():
        raise Exception(
            "DEEPSEEK_API_KEY não configurada no backend. Defina a chave da DeepSeek para habilitar a classificação."
        )

    client = AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        # No experimento, cada tentativa deve aparecer nas medições.
        **({"max_retries": 0} if metrics is not None else {}),
    )

    request_kwargs: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        "temperature": DEEPSEEK_TEMPERATURE,
        "max_tokens": DEEPSEEK_MAX_COMPLETION_TOKENS,
        "stream": False,
    }

    if DEEPSEEK_REASONING_EFFORT and DEEPSEEK_THINKING_ENABLED:
        request_kwargs["reasoning_effort"] = DEEPSEEK_REASONING_EFFORT
        request_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        
    last_error: Exception | None = None

    try:
        for attempt in range(1, CLASSIFICATION_MAX_RETRIES + 1):
            try:
                with _measure_request(metrics, attempt) as measurement:
                    response = await client.chat.completions.create(**request_kwargs)
                    measurement["status_code"] = 200

                if metrics is None:
                    print("\n=== RESPOSTA COMPLETA DEEPSEEK ===")
                    print(response.model_dump_json(indent=2))

                choice = response.choices[0]
                raw_content = choice.message.content

                if not raw_content:
                    raise Exception(
                        f"DeepSeek retornou content vazio. "
                        f"finish_reason={choice.finish_reason}"
                    )
                return _extract_json_payload(raw_content)
            except RateLimitError as exc:
                if attempt < CLASSIFICATION_MAX_RETRIES:
                    await _classification_wait(CLASSIFICATION_REQUEST_DELAY_SECONDS, "rate_limit", metrics)
                    continue
                last_error = Exception(f"Erro na API DeepSeek: rate limit - {exc}")
            except APIStatusError as exc:
                if exc.status_code == 429 and attempt < CLASSIFICATION_MAX_RETRIES:
                    await _classification_wait(CLASSIFICATION_REQUEST_DELAY_SECONDS, "rate_limit", metrics)
                    continue
                raise Exception(f"Erro na API DeepSeek: {exc.status_code} - {exc.message}") from exc
    finally:
        await client.close()

    if last_error:
        raise last_error
    raise Exception("Erro na API DeepSeek: limite de tentativas excedido.")


async def _call_classification_api(
    prompt: str,
    provider: ClassificationProvider | None = None,
    metrics: ClassificationMetrics | None = None,
) -> dict | list:
    selected_provider = _resolve_provider(provider)
    kwargs = {"metrics": metrics} if metrics is not None else {}
    if selected_provider == "deepseek":
        return await _call_deepseek_classification(prompt, **kwargs)
    return await _call_groq_classification(prompt, **kwargs)


async def classify_questions_batch(
    questions: list[dict[str, Any]],
    *,
    only_unclassified: bool = True,
    request_delay_seconds: float | None = None,
    provider: ClassificationProvider | None = None,
    metrics: ClassificationMetrics | None = None,
) -> list[dict[str, Any]]:
    """
    Classifica questões pela Taxonomia de Bloom usando IA.

    Questões com level=0 são consideradas não classificadas.
    As demais são preservadas quando only_unclassified=True.
    """
    if not questions:
        raise Exception("Nenhuma questão foi informada para classificação.")
    if CLASSIFICATION_BATCH_SIZE <= 0 or CLASSIFICATION_MAX_RETRIES <= 0:
        raise Exception("O tamanho do lote e o limite de tentativas devem ser maiores que zero.")

    normalized_questions = []
    for index, question in enumerate(questions, start=1):
        _validate_input_question(question, index)
        normalized_questions.append(_normalize_question(question))

    pending_indexes = [
        index
        for index, question in enumerate(normalized_questions)
        if not only_unclassified or question["level"] == UNCLASSIFIED_LEVEL
    ]
    if metrics is not None:
        metrics.pending_questions = len(pending_indexes)

    if not pending_indexes:
        return normalized_questions

    delay_seconds = (
        CLASSIFICATION_REQUEST_DELAY_SECONDS
        if request_delay_seconds is None
        else max(0.0, request_delay_seconds)
    )

    for batch_start in range(0, len(pending_indexes), CLASSIFICATION_BATCH_SIZE):
        if metrics is not None:
            metrics.batch = batch_start // CLASSIFICATION_BATCH_SIZE + 1
        if batch_start > 0 and delay_seconds > 0:
            await _classification_wait(delay_seconds, "between_batches", metrics)

        batch_indexes = pending_indexes[batch_start : batch_start + CLASSIFICATION_BATCH_SIZE]
        batch_questions = [normalized_questions[index] for index in batch_indexes]
        if metrics is not None:
            metrics.batch_questions = len(batch_questions)

        prompt = _build_classification_prompt(batch_questions)
        kwargs = {"metrics": metrics} if metrics is not None else {}
        payload = await _call_classification_api(prompt, provider=provider, **kwargs)
        classifications = _normalize_classifications(payload, len(batch_questions))

        for classification in classifications:
            batch_index = classification["index"]
            source_index = batch_indexes[batch_index]
            normalized_questions[source_index]["level"] = classification["level"]
        if metrics is not None:
            metrics.completed_questions += len(batch_questions)

    return normalized_questions


def load_questions_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("questions"), list):
        return payload["questions"]
    raise Exception("O arquivo JSON deve conter uma lista de questões ou um objeto com a chave 'questions'.")
