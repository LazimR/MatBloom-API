from collections import Counter, defaultdict

from sqlalchemy.orm import Session, joinedload

from app.api.schemas.question import Question as QuestionSchema
from app.api.schemas.test import (
    Test as TestSchema,
    TestApplicationCreate,
    TestBloomLevelUsageMetric,
    TestCreate,
    TestLibraryUsageMetrics,
    TestTemplateUsageMetric,
    TestTemplateVersionCreate,
    TestThemeUsageMetric,
)
from app.core.academic import TestTargetType
from app.core.academic import TestKind, TestVisibility
from app.core.exceptions import NotFoundError, ValidationError
from app.core.roles import UserRole
from app.db.models.models import Classroom as ClassroomModel
from app.db.models.models import Question as QuestionModel
from app.db.models.models import Student as StudentModel
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
                    & (
                        TestModel.classroom_id.in_(accessible_classroom_ids or set())
                        | TestModel.student_id.in_(
                            self.db_session.query(StudentModel.id)
                            .filter(StudentModel.classroom_id.in_(accessible_classroom_ids or set()))
                        )
                    )
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
            student_id=None,
            source_test_id=None,
            template_group_id=None,
            version_number=1,
            applied_by_user_id=None,
        )
        self.db_session.add(db_test)
        self.db_session.flush()
        db_test.template_group_id = db_test.id
        self._attach_questions(db_test.id, test.questions)
        self.db_session.commit()
        return self.get_test(db_test.id)

    def get_library_usage_metrics(
        self,
        current_user: dict | None = None,
        accessible_classroom_ids: set[int] | None = None,
    ) -> TestLibraryUsageMetrics:
        templates = self._get_accessible_template_models(current_user, accessible_classroom_ids)
        if not templates:
            raise NotFoundError("No test templates found in the database.")

        template_ids = [template.id for template in templates]
        applications = self._get_template_application_models(template_ids)
        applications_by_template = defaultdict(list)
        for application in applications:
            applications_by_template[application.source_test_id].append(application)

        theme_application_counter = Counter()
        theme_template_counter = Counter()
        bloom_application_counter = Counter()
        bloom_question_counter = Counter()
        template_metrics = []
        used_templates = 0
        templates_with_individual_applications = 0

        for template in templates:
            template_applications = applications_by_template.get(template.id, [])
            application_count = len(template_applications)
            if application_count > 0:
                used_templates += 1
                theme_application_counter[template.theme] += application_count
            theme_template_counter[template.theme] += 1

            level_counts = Counter(question.level for question in template.questions)
            for level, question_count in level_counts.items():
                bloom_question_counter[level] += question_count
                bloom_application_counter[level] += question_count * application_count

            distinct_teacher_ids = {
                application.applied_by_user_id
                for application in template_applications
                if application.applied_by_user_id is not None
            }
            classroom_application_count = sum(
                1
                for application in template_applications
                if application.target_type == TestTargetType.CLASS.value
            )
            individual_application_count = sum(
                1
                for application in template_applications
                if application.target_type == TestTargetType.INDIVIDUAL.value
            )
            if individual_application_count > 0:
                templates_with_individual_applications += 1

            last_applied_at = max(
                (application.application_date for application in template_applications),
                default=None,
            )

            template_metrics.append(
                TestTemplateUsageMetric(
                    template_id=template.id,
                    template_group_id=template.template_group_id,
                    version_number=template.version_number,
                    name=template.name,
                    theme=template.theme,
                    visibility=template.visibility,
                    application_count=application_count,
                    distinct_teacher_count=len(distinct_teacher_ids),
                    classroom_application_count=classroom_application_count,
                    individual_application_count=individual_application_count,
                    last_applied_at=last_applied_at,
                    bloom_level_distribution=[
                        TestBloomLevelUsageMetric(
                            level=level,
                            application_count=question_count * application_count,
                            question_count=question_count,
                        )
                        for level, question_count in sorted(level_counts.items())
                    ],
                    is_unused=application_count == 0,
                )
            )

        template_metrics.sort(
            key=lambda metric: (
                -metric.application_count,
                -metric.distinct_teacher_count,
                metric.template_id,
            )
        )

        return TestLibraryUsageMetrics(
            total_templates=len(templates),
            used_templates=used_templates,
            unused_templates=len(templates) - used_templates,
            total_applications=len(applications),
            templates_with_individual_applications=templates_with_individual_applications,
            theme_distribution=[
                TestThemeUsageMetric(
                    theme=theme,
                    application_count=theme_application_counter[theme],
                    template_count=theme_template_counter[theme],
                )
                for theme in sorted(
                    theme_template_counter,
                    key=lambda current_theme: (
                        -theme_application_counter[current_theme],
                        -theme_template_counter[current_theme],
                        current_theme,
                    ),
                )
            ],
            bloom_level_distribution=[
                TestBloomLevelUsageMetric(
                    level=level,
                    application_count=bloom_application_counter[level],
                    question_count=bloom_question_counter[level],
                )
                for level in sorted(bloom_question_counter)
            ],
            templates=template_metrics,
        )

    def create_template_version(
        self,
        template_id: int,
        version_data: TestTemplateVersionCreate,
        created_by_user_id: int,
    ) -> TestSchema:
        template = self._get_test_model(template_id)
        if template.kind != TestKind.TEMPLATE.value:
            raise ValidationError("Somente modelos de prova podem gerar novas versões.")

        template_group_id = template.template_group_id or template.id
        latest_version_number = (
            self.db_session.query(TestModel.version_number)
            .filter(TestModel.template_group_id == template_group_id)
            .order_by(TestModel.version_number.desc())
            .first()
        )
        next_version = (latest_version_number[0] if latest_version_number else template.version_number) + 1

        question_ids = version_data.questions or [question.id for question in template.questions]
        db_test = TestModel(
            name=version_data.name or template.name,
            theme=version_data.theme or template.theme,
            application_date=None,
            created_by_user_id=created_by_user_id,
            applied_by_user_id=None,
            classroom_id=None,
            student_id=None,
            source_test_id=None,
            template_group_id=template_group_id,
            version_number=next_version,
            kind=TestKind.TEMPLATE.value,
            visibility=(version_data.visibility or template.visibility),
            target_type=template.target_type,
        )
        self.db_session.add(db_test)
        self.db_session.flush()
        self._attach_questions(db_test.id, question_ids)
        self.db_session.commit()
        return self.get_test(db_test.id)

    def apply_test(
        self,
        template_id: int,
        application: TestApplicationCreate,
        applied_by_user_id: int,
    ) -> TestSchema:
        template = self._get_test_model(template_id)
        if template.kind != TestKind.TEMPLATE.value:
            raise ValidationError("Somente modelos de prova podem gerar aplicações.")

        classroom_id = application.classroom_id
        student_id = application.student_id

        if application.target_type == TestTargetType.CLASS:
            if classroom_id is None:
                raise ValidationError("Aplicações para turma exigem classroom_id.")
            if student_id is not None:
                raise ValidationError("Aplicações para turma não devem informar student_id.")
            classroom = (
                self.db_session.query(ClassroomModel)
                .filter(ClassroomModel.id == classroom_id)
                .first()
            )
            if not classroom:
                raise NotFoundError(f"Classroom with ID {classroom_id} does not exist.")
        else:
            if student_id is None:
                raise ValidationError("Aplicações individuais exigem student_id.")
            student = (
                self.db_session.query(StudentModel)
                .filter(StudentModel.id == student_id)
                .first()
            )
            if not student:
                raise NotFoundError(f"Student with ID {student_id} does not exist.")
            classroom_id = student.classroom_id

        db_test = TestModel(
            name=application.name or template.name,
            theme=template.theme,
            application_date=application.application_date,
            created_by_user_id=template.created_by_user_id,
            applied_by_user_id=applied_by_user_id,
            classroom_id=classroom_id,
            student_id=student_id,
            source_test_id=template.id,
            template_group_id=template.template_group_id or template.id,
            version_number=template.version_number,
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

    def _get_accessible_template_models(
        self,
        current_user: dict | None = None,
        accessible_classroom_ids: set[int] | None = None,
    ) -> list[TestModel]:
        query = self.db_session.query(TestModel).options(
            joinedload(TestModel.questions)
        ).filter(TestModel.kind == TestKind.TEMPLATE.value)

        if current_user and current_user.get("role") == UserRole.TEACHER.value:
            user_id = current_user.get("user_id")
            query = query.filter(
                (TestModel.visibility == TestVisibility.LIBRARY.value)
                | (TestModel.visibility == TestVisibility.SHARED.value)
                | (TestModel.created_by_user_id == user_id)
            )

        return query.order_by(TestModel.id).all()

    def _get_template_application_models(self, template_ids: list[int]) -> list[TestModel]:
        if not template_ids:
            return []

        return (
            self.db_session.query(TestModel)
            .filter(
                TestModel.kind == TestKind.APPLICATION.value,
                TestModel.source_test_id.in_(template_ids),
            )
            .order_by(TestModel.id)
            .all()
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
            student_id=db_test.student_id,
            source_test_id=db_test.source_test_id,
            template_group_id=db_test.template_group_id,
            version_number=db_test.version_number,
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
