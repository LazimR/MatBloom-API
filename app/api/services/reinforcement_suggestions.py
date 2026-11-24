"""Suggest existing questions from observed errors, without inferring difficulty from Bloom."""
from collections import Counter

from sqlalchemy.orm import joinedload

from app.core.exceptions import ValidationError
from app.db.models.models import Question


def rank_questions(questions, content_errors, bloom_errors, quantity):
    contents = {item.content_name: item.wrong_count for item in content_errors}
    levels = {item.level: item.wrong_count for item in bloom_errors}
    if not contents:
        raise ValidationError("Não há erros por conteúdo com ordem confirmada suficientes para sugerir questões.")
    groups = {size: [] for size in range(2, 6)}
    for question in questions:
        matched = [content.name for content in question.contents if content.name in contents]
        if not matched or len(question.itens) not in groups:
            continue
        # Os erros por conteúdo são o sinal principal; Bloom desempata dentro dele.
        priority = sum(contents[name] for name in set(matched))
        groups[len(question.itens)].append((question, priority, levels.get(question.level, 0), matched))
    for group in groups.values():
        group.sort(key=lambda item: (-item[1], -item[2], item[0].id))
    available = max((len(group) for group in groups.values()), default=0)
    eligible = [group for group in groups.values() if len(group) >= quantity]
    if not eligible:
        raise ValidationError(f"Não há {quantity} questões compatíveis com os conteúdos e com a mesma quantidade de alternativas. Máximo disponível: {available}.")
    best = max(eligible, key=lambda group: (sum(item[1] for item in group[:quantity]), sum(item[2] for item in group[:quantity])))
    return [{"id": q.id, "matched_contents": matched, "content_errors": score, "bloom_errors": bloom} for q, score, bloom, matched in best[:quantity]]


def suggest_questions(db, analysis, quantity):
    questions = db.query(Question).options(joinedload(Question.contents)).all()
    return {
        "questions": rank_questions(questions, analysis.errors_by_content, analysis.errors_by_bloom, quantity),
        "unordered_attempts": analysis.unordered_attempts,
    }
