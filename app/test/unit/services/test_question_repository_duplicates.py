from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.schemas.question import QuestionCreate
from app.core.exceptions import ConflictError
from app.db.repositories.question_repository import QuestionRepository


def test_duplicate_is_rejected_before_insert():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=42)
    question = QuestionCreate(enunciation="Quanto é 2 + 2?", itens=["3", "4"], correct_item=1, level=3)

    with pytest.raises(ConflictError, match="ID 42"):
        QuestionRepository(db).create_question(question)

    db.execute.assert_called_once()
    db.add.assert_not_called()
    db.commit.assert_not_called()
