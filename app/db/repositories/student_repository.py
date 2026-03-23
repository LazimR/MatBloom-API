from sqlalchemy.orm import Session

from app.api.schemas.student import Student as StudentSchema, StudentCreate, StudentUpdate
from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.models import Classroom as ClassroomModel
from app.db.models.models import Student as StudentModel


class StudentRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_student_model(self, student_id: int) -> StudentModel | None:
        return self.db_session.query(StudentModel).filter(StudentModel.id == student_id).first()

    def list_students(self, classroom_ids: set[int] | None = None) -> list[StudentSchema]:
        query = self.db_session.query(StudentModel)
        if classroom_ids is not None:
            query = query.filter(StudentModel.classroom_id.in_(classroom_ids))
        students = query.all()
        return [StudentSchema.model_validate(student) for student in students]

    def get_student(self, student_id: int) -> StudentSchema:
        student = self.get_student_model(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} does not exist.")
        return StudentSchema.model_validate(student)

    def create_student(self, student: StudentCreate) -> StudentSchema:
        if self.db_session.query(StudentModel).filter(StudentModel.registration == student.registration).first():
            raise ConflictError(f"Student with registration '{student.registration}' already exists.")

        classroom = self.db_session.query(ClassroomModel).filter(ClassroomModel.id == student.classroom_id).first()
        if not classroom:
            raise NotFoundError(f"Classroom with ID {student.classroom_id} does not exist.")

        db_student = StudentModel(**student.model_dump())
        self.db_session.add(db_student)
        self.db_session.commit()
        self.db_session.refresh(db_student)
        return StudentSchema.model_validate(db_student)

    def update_student(self, student_update: StudentUpdate) -> StudentSchema:
        student = self.get_student_model(student_update.id)
        if not student:
            raise NotFoundError(f"Student with ID {student_update.id} does not exist.")

        if student_update.registration is not None:
            existing = self.db_session.query(StudentModel).filter(StudentModel.registration == student_update.registration).first()
            if existing and existing.id != student.id:
                raise ConflictError(f"Student with registration '{student_update.registration}' already exists.")
            student.registration = student_update.registration

        if student_update.classroom_id is not None:
            classroom = self.db_session.query(ClassroomModel).filter(ClassroomModel.id == student_update.classroom_id).first()
            if not classroom:
                raise NotFoundError(f"Classroom with ID {student_update.classroom_id} does not exist.")
            student.classroom_id = student_update.classroom_id

        if student_update.name is not None:
            student.name = student_update.name
        if student_update.active is not None:
            student.active = student_update.active

        self.db_session.commit()
        self.db_session.refresh(student)
        return StudentSchema.model_validate(student)

    def delete_student(self, student_id: int) -> bool:
        student = self.get_student_model(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} does not exist.")

        self.db_session.delete(student)
        self.db_session.commit()
        return True
