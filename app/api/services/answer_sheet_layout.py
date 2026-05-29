from dataclasses import dataclass
from math import ceil

from app.core.exceptions import ValidationError

MAX_QUESTIONS_PER_BLOCK = 10
MAX_BLOCK_COLUMNS = 2
WARP_CELL_WIDTH = 267
WARP_CELL_HEIGHT = 193
WARP_BLOCK_GAP = 80


@dataclass(frozen=True)
class AnswerSheetBlock:
    start_index: int
    question_count: int
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class AnswerSheetLayout:
    rows_per_block: int
    block_columns: int
    block_rows: int
    block_width: int
    block_height: int
    total_width: int
    total_height: int
    blocks: list[AnswerSheetBlock]


def build_answer_sheet_layout(num_questions: int, num_alternatives: int) -> AnswerSheetLayout:
    if num_questions <= 0:
        raise ValidationError("O número de questões deve ser maior que zero.")
    if num_alternatives <= 0:
        raise ValidationError("O número de alternativas deve ser maior que zero.")
    if num_alternatives > 5:
        raise ValidationError("A correção automática suporta no máximo 5 alternativas por questão.")

    rows_per_block = min(MAX_QUESTIONS_PER_BLOCK, num_questions)
    block_count = ceil(num_questions / rows_per_block)
    block_columns = 1 if block_count == 1 else min(MAX_BLOCK_COLUMNS, block_count)
    block_rows = ceil(block_count / block_columns)

    block_width = WARP_CELL_WIDTH * num_alternatives
    block_height = WARP_CELL_HEIGHT * rows_per_block
    total_width = block_columns * block_width + (block_columns - 1) * WARP_BLOCK_GAP
    total_height = block_rows * block_height + (block_rows - 1) * WARP_BLOCK_GAP

    blocks: list[AnswerSheetBlock] = []
    remaining_questions = num_questions
    start_index = 0

    for block_index in range(block_count):
        row = block_index // block_columns
        column = block_index % block_columns
        question_count = min(rows_per_block, remaining_questions)
        blocks.append(
            AnswerSheetBlock(
                start_index=start_index,
                question_count=question_count,
                x=column * (block_width + WARP_BLOCK_GAP),
                y=row * (block_height + WARP_BLOCK_GAP),
                width=block_width,
                height=block_height,
            )
        )
        start_index += question_count
        remaining_questions -= question_count

    return AnswerSheetLayout(
        rows_per_block=rows_per_block,
        block_columns=block_columns,
        block_rows=block_rows,
        block_width=block_width,
        block_height=block_height,
        total_width=total_width,
        total_height=total_height,
        blocks=blocks,
    )
