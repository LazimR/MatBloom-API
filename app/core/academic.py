from enum import StrEnum


class ClassroomShift(StrEnum):
    MORNING = "manha"
    AFTERNOON = "tarde"
    EVENING = "noite"
    FULL_DAY = "integral"
    MORNING_AFTERNOON = "matutino_vespertino"


class TestTargetType(StrEnum):
    INDIVIDUAL = "individual"
    CLASS = "turma"


class TestKind(StrEnum):
    TEMPLATE = "template"
    APPLICATION = "application"


class TestVisibility(StrEnum):
    PRIVATE = "private"
    SHARED = "shared"
    LIBRARY = "library"
