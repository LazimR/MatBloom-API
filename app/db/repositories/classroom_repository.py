from sqlalchemy.orm import Session, joinedload

from app.api.schemas.classroom import ClassroomCreate, ClassroomUpdate, Classroom as ClassroomSchema
from app.core.exceptions import NotFoundError
from app.db.models.models import Classroom as ClassroomModel


class ClassroomRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_classroom_model(self, classroom_id: int) -> ClassroomModel | None:
        return (
            self.db_session.query(ClassroomModel)
            .options(joinedload(ClassroomModel.students), joinedload(ClassroomModel.users))
            .filter(ClassroomModel.id == classroom_id)
            .first()
        )

    def list_classrooms(self, classroom_ids: set[int] | None = None) -> list[ClassroomSchema]:
        query = self.db_session.query(ClassroomModel).options(
            joinedload(ClassroomModel.students),
            joinedload(ClassroomModel.users),
        )
        if classroom_ids is not None:
            query = query.filter(ClassroomModel.id.in_(classroom_ids))
        classrooms = query.all()
        return [ClassroomSchema.model_validate(classroom) for classroom in classrooms]

    def get_classroom(self, classroom_id: int) -> ClassroomSchema:
        classroom = self.get_classroom_model(classroom_id)
        if not classroom:
            raise NotFoundError(f"Classroom with ID {classroom_id} does not exist.")
        return ClassroomSchema.model_validate(classroom)

    def create_classroom(self, classroom: ClassroomCreate) -> ClassroomSchema:
        db_classroom = ClassroomModel(**classroom.model_dump())
        self.db_session.add(db_classroom)
        self.db_session.commit()
        self.db_session.refresh(db_classroom)
        return ClassroomSchema.model_validate(db_classroom)

    def update_classroom(self, classroom_update: ClassroomUpdate) -> ClassroomSchema:
        classroom = self.get_classroom_model(classroom_update.id)
        if not classroom:
            raise NotFoundError(f"Classroom with ID {classroom_update.id} does not exist.")

        for field in ("name", "school_year", "grade_level", "active"):
            value = getattr(classroom_update, field)
            if value is not None:
                setattr(classroom, field, value)

        if classroom_update.shift is not None:
            classroom.shift = classroom_update.shift.value

        self.db_session.commit()
        self.db_session.refresh(classroom)
        return ClassroomSchema.model_validate(classroom)

    def delete_classroom(self, classroom_id: int) -> bool:
        classroom = self.get_classroom_model(classroom_id)
        if not classroom:
            raise NotFoundError(f"Classroom with ID {classroom_id} does not exist.")

        self.db_session.delete(classroom)
        self.db_session.commit()
        return True
