from sqlalchemy.orm import Session, joinedload

from app.api.schemas.question import Question as QuestionSchema
from app.api.schemas.test import Test as TestSchema
from app.api.schemas.test import TestApplicationCreate, TestCreate
from app.core.academic import TestKind, TestVisibility
from app.core.exceptions import NotFoundError, ValidationError
from app.core.roles import UserRole
from app.db.models.models import Classroom as ClassroomModel
from app.db.models.models import Question as QuestionModel
from app.db.models.models import Test as TestModel
from app.db.models.models import TestQuestion


class TestRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_test(self, test_id: int) -> TestSchema:
        db_test = self._get_test_model(test_id)
        return self._build_test_schema(db_test)

    def get_all_tests(
        self,
        current_user: dict | None = None,
        accessible_classroom_ids: set[int] | None = None,
        kind: str | None = None,
    ) -> list[TestSchema]:
        query = self._base_query()

        if kind:
            query = query.filter(TestModel.kind == kind)

        if current_user and current_user.get("role") == UserRole.TEACHER.value:
            user_id = current_user.get("user_id")
            query = query.filter(
                (
                    (TestModel.kind == TestKind.TEMPLATE.value)
                    & (
                        (TestModel.visibility == TestVisibility.LIBRARY.value)
                        | (TestModel.visibility == TestVisibility.SHARED.value)
                        | (TestModel.created_by_user_id == user_id)
                    )
                )
                | (
                    (TestModel.kind == TestKind.APPLICATION.value)
                    & TestModel.classroom_id.in_(accessible_classroom_ids or set())
                )
            )

        tests = query.order_by(TestModel.id).all()
        if not tests:
            raise NotFoundError("No tests found in the database.")

        return [self._build_test_schema(test) for test in tests]

    def create_test(self, test: TestCreate) -> TestSchema:
        db_test = TestModel(
            **test.model_dump(exclude={"questions"}),
            kind=TestKind.TEMPLATE.value,
            classroom_id=None,
            source_test_id=None,
            applied_by_user_id=None,
        )
        self.db_session.add(db_test)
        self.db_session.flush()
        self._attach_questions(db_test.id, test.questions)
        self.db_session.commit()
        return self.get_test(db_test.id)

    def apply_test_to_classroom(
        self,
        template_id: int,
        application: TestApplicationCreate,
        applied_by_user_id: int,
    ) -> TestSchema:
        template = self._get_test_model(template_id)
        if template.kind != TestKind.TEMPLATE.value:
            raise ValidationError("Somente modelos de prova podem ser aplicados a turmas.")

        classroom = (
            self.db_session.query(ClassroomModel)
            .filter(ClassroomModel.id == application.classroom_id)
            .first()
        )
        if not classroom:
            raise NotFoundError(f"Classroom with ID {application.classroom_id} does not exist.")

        db_test = TestModel(
            name=application.name or template.name,
            theme=template.theme,
            application_date=application.application_date,
            created_by_user_id=template.created_by_user_id,
            applied_by_user_id=applied_by_user_id,
            classroom_id=application.classroom_id,
            source_test_id=template.id,
            kind=TestKind.APPLICATION.value,
            visibility=template.visibility,
            target_type=application.target_type.value,
        )
        self.db_session.add(db_test)
        self.db_session.flush()
        self._attach_questions(db_test.id, [question.id for question in template.questions])
        self.db_session.commit()
        return self.get_test(db_test.id)

    def delete_test(self, test_id: int) -> bool:
        db_test = self._get_test_model(test_id)
        self.db_session.delete(db_test)
        self.db_session.commit()
        return True

    def _base_query(self):
        return self.db_session.query(TestModel).options(
            joinedload(TestModel.questions).joinedload(QuestionModel.contents),
            joinedload(TestModel.questions).joinedload(QuestionModel.dependencies),
        )

    def _get_test_model(self, test_id: int) -> TestModel:
        db_test = self._base_query().filter(TestModel.id == test_id).first()
        if not db_test:
            raise NotFoundError(f"Test with ID {test_id} does not exist.")
        if len(db_test.questions) == 0:
            raise ValidationError(f"Test with ID {test_id} has no questions.")
        return db_test

    def _attach_questions(self, test_id: int, question_ids: list[int]):
        for question_id in question_ids:
            question = (
                self.db_session.query(QuestionModel)
                .filter(QuestionModel.id == question_id)
                .first()
            )
            if not question:
                raise NotFoundError(f"Question with ID {question_id} does not exist.")
            self.db_session.add(TestQuestion(test_id=test_id, question_id=question_id))

    def _build_test_schema(self, db_test: TestModel) -> TestSchema:
        return TestSchema(
            id=db_test.id,
            name=db_test.name,
            theme=db_test.theme,
            application_date=db_test.application_date,
            created_by_user_id=db_test.created_by_user_id,
            applied_by_user_id=db_test.applied_by_user_id,
            classroom_id=db_test.classroom_id,
            source_test_id=db_test.source_test_id,
            kind=db_test.kind,
            visibility=db_test.visibility,
            target_type=db_test.target_type,
            created_at=db_test.created_at,
            questions=[self._build_question_schema(question) for question in db_test.questions],
        )

    def _build_question_schema(self, question: QuestionModel) -> QuestionSchema:
        return QuestionSchema(
            id=question.id,
            enunciation=question.enunciation,
            itens=question.itens,
            correct_item=question.correct_item,
            level=question.level,
            contents=[content.name for content in question.contents],
            dependencies=[dependency.id for dependency in question.dependencies],
            created_at=question.created_at,
        )
