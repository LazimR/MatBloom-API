import httpx
import json
import os
import re
from dotenv import load_dotenv
from typing import Dict, List

# Carrega a API Key do .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.3"))
GROQ_MAX_COMPLETION_TOKENS = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "1400"))

BLOOM_LEVEL_NAMES = {
    1: "Lembrar",
    2: "Entender",
    3: "Aplicar",
    4: "Analisar",
    5: "Avaliar",
    6: "Criar",
}


def _extract_json_payload(raw_content: str) -> dict:
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
                raise Exception("A resposta do modelo precisa conter apenas objetos JSON.")

            parsed_objects.append(parsed_object)
            remaining = remaining[end_index:]

        if not parsed_objects:
            raise Exception(
                f"A resposta do modelo não retornou JSON válido. Conteúdo recebido: {raw_content}"
            ) from exc

        merged_questions: list[dict] = []
        for parsed_object in parsed_objects:
            questions = parsed_object.get("questions")
            if isinstance(questions, list):
                merged_questions.extend(questions)

        if not merged_questions:
            merged_questions = _extract_partial_question_objects(content)

        if not merged_questions:
            raise Exception("Os blocos JSON retornados não contêm questões válidas.")

        return {"questions": merged_questions}

    if not isinstance(parsed, dict):
        raise Exception("A resposta do modelo precisa ser um objeto JSON.")

    return parsed


def _extract_partial_question_objects(content: str) -> list[dict]:
    match = re.search(r'"questions"\s*:\s*\[', content)
    if not match:
        return []

    index = match.end()
    decoder = json.JSONDecoder()
    extracted_questions: list[dict] = []

    while index < len(content):
        while index < len(content) and content[index] in " \n\r\t,":
            index += 1

        if index >= len(content) or content[index] == "]":
            break

        try:
            parsed_question, end_index = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            break

        if isinstance(parsed_question, dict):
            extracted_questions.append(parsed_question)

        index += end_index

    return extracted_questions


def _normalize_generated_questions(payload: dict) -> dict[str, list[dict]]:
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise Exception("A resposta do modelo não trouxe questões válidas.")

    normalized_questions: list[dict] = []
    seen_questions: set[tuple] = set()
    for index, raw_question in enumerate(raw_questions, start=1):
        if not isinstance(raw_question, dict):
            raise Exception(f"A questão {index} não está em formato de objeto JSON.")

        enunciation = str(raw_question.get("enunciation", "")).strip()
        itens = raw_question.get("itens") or raw_question.get("options")
        correct_item = raw_question.get("correct_item", raw_question.get("correct_option_index"))
        level = raw_question.get("level")
        contents = raw_question.get("contents")
        if contents is None:
            primary_content = str(raw_question.get("content", "")).strip()
            contents = [primary_content] if primary_content else []
        level_name = str(raw_question.get("level_name", "")).strip()

        if not enunciation:
            raise Exception(f"A questão {index} veio sem enunciado.")
        if not isinstance(itens, list) or len(itens) < 2:
            raise Exception(f"A questão {index} precisa ter pelo menos duas alternativas.")
        if not isinstance(correct_item, int):
            raise Exception(f"A questão {index} precisa informar correct_item como índice numérico.")
        if not isinstance(level, int) or level not in BLOOM_LEVEL_NAMES:
            raise Exception(f"A questão {index} veio com nível Bloom inválido.")
        if level_name and level_name != BLOOM_LEVEL_NAMES[level]:
            raise Exception(
                f"A questão {index} veio com nome de nível inconsistente: "
                f"esperado '{BLOOM_LEVEL_NAMES[level]}' e recebido '{level_name}'."
            )

        normalized_itens = [str(item).strip() for item in itens]
        if any(not item for item in normalized_itens):
            raise Exception(f"A questão {index} possui alternativa vazia.")
        if correct_item < 0 or correct_item >= len(normalized_itens):
            raise Exception(f"A questão {index} possui correct_item fora do intervalo das alternativas.")

        normalized_contents = [str(content).strip() for content in contents if str(content).strip()]
        if not normalized_contents:
            raise Exception(f"A questão {index} precisa informar pelo menos um conteúdo.")

        question_key = (
            enunciation,
            tuple(normalized_itens),
            correct_item,
            level,
            tuple(normalized_contents),
        )
        if question_key in seen_questions:
            continue

        seen_questions.add(question_key)
        normalized_questions.append(
            {
                "enunciation": enunciation,
                "itens": normalized_itens,
                "correct_item": correct_item,
                "level": level,
                "level_name": BLOOM_LEVEL_NAMES[level],
                "contents": normalized_contents,
            }
        )

    if not normalized_questions:
        raise Exception("A resposta do modelo não trouxe questões completas aproveitáveis.")

    return {"questions": normalized_questions}

async def gerar_questoes_reforco(
    questao_errada: List[str],
    nivel_bloom: List[int],
    conteudo: List[str],
    numero_questoes_por_nivel: int = 2,
    incluir_todos_niveis: bool = False
) -> Dict[str, List[str]]:
    """
    Gera questões de reforço baseadas no erro do aluno e na Taxonomia de Bloom.

    Args:
        questao_errada (str): Questão que o aluno errou.
        nivel_bloom (int): Nível da Taxonomia de Bloom (1-6).
        conteudo (str): Tema específico da questão.
        numero_questoes_por_nivel (int): Quantidade de questões por nível (padrão: 2).
        incluir_todos_niveis (bool): Se True, gera questões para todos os níveis (1-6).

    Returns:
        Dict[str, List[str]]: Dicionário com questões agrupadas por nível.
    """
    if not GROQ_API_KEY or not GROQ_API_KEY.strip():
        raise Exception(
            "GROQ_API_KEY não configurada no backend. Defina a chave da Groq para habilitar o reforço automático."
        )

    # Construção do prompt
    prompt = """
    Você é um tutor especializado em ensino de matemática e reforço escolar.
Gere questões objetivas de múltipla escolha para um aluno com dificuldades registradas.
Seja direto e retorne SOMENTE JSON válido, sem markdown, sem comentários e sem texto extra.
Use linguagem apropriada para alunos e priorize clareza conceitual em matemática.

**Taxonomia de Bloom usada neste sistema**
- Nível 1: Lembrar
- Nível 2: Entender
- Nível 3: Aplicar
- Nível 4: Analisar
- Nível 5: Avaliar
- Nível 6: Criar

Use EXATAMENTE esses nomes de níveis na resposta. Não substitua por sinônimos, variações ou traduções diferentes.

**Regras**
- Gere exatamente 4 alternativas por questão.
- Informe `correct_item` como índice numérico de 0 a 3.
- Mantenha o foco no conteúdo específico mencionado.
- Cada questão precisa ter apenas um conteúdo principal em `contents`.
- Retorne um ÚNICO objeto JSON final, com todas as questões reunidas em um único array `questions`.
- Não inclua resolução, explicação, dicas, comentários pedagógicos ou texto fora do JSON.

**Formato obrigatório de saída**
{
  "questions": [
    {
      "enunciation": "Enunciado da questão",
      "itens": ["Alternativa A", "Alternativa B", "Alternativa C", "Alternativa D"],
      "correct_item": 0,
      "level": 3,
      "level_name": "Aplicar",
      "contents": ["Equações do 1º grau"]
    }
  ]
}

**Tarefa**
"""

    if incluir_todos_niveis:
        prompt += (
            f"Gere {numero_questoes_por_nivel} questões para cada nível de Bloom de 1 a 6, "
            "mantendo aderência ao conteúdo e à dificuldade informados."
        )
    else:
        prompt += (
            f"Gere {numero_questoes_por_nivel} novas questões para cada erro listado abaixo, "
            "mantendo o mesmo nível de Bloom e o mesmo conteúdo principal da questão de origem."
        )

    prompt += "\n\n**Erros de origem do aluno**\n"
    for i in range(len(questao_errada)):
        prompt += (
            f"- Erro {i + 1}: questão errada='{questao_errada[i]}', "
            f"nível={nivel_bloom[i]} ({BLOOM_LEVEL_NAMES.get(nivel_bloom[i], 'Desconhecido')}), "
            f"conteúdo='{conteudo[i]}'\n"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",  # endpoint correto
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Você é um gerador de questões objetivas de matemática. "
                                "Retorne apenas JSON válido e siga exatamente o esquema pedido."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": GROQ_TEMPERATURE,
                    "max_completion_tokens": GROQ_MAX_COMPLETION_TOKENS,
                },
                timeout=30.0
            )
            response.raise_for_status()
            return _processar_resposta(response.json())
    
    except httpx.HTTPStatusError as e:
        raise Exception(f"Erro na API: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Erro ao gerar questões: {str(e)}")

def _processar_resposta(resposta_api: Dict) -> Dict[str, List[dict]]:
    """
    Processa a resposta da API para extrair as questões geradas.
    """
    texto_resposta = resposta_api["choices"][0]["message"]["content"]
    parsed_payload = _extract_json_payload(texto_resposta)
    return _normalize_generated_questions(parsed_payload)
    

if __name__ == "__main__":

    import asyncio
    # Exemplo de uso
    questao_errada = ["Resolva 2x + 3 = 11"]
    nivel_bloom = [3]
    conteudo = ["equações do 1º grau"]
    
    questoes_geradas = asyncio.run(gerar_questoes_reforco(questao_errada, nivel_bloom, conteudo))
    print(questoes_geradas)
