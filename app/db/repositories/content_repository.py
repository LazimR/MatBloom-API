from sqlalchemy.orm import Session
from app.db.models.models import Content
from app.api.schemas.content import ContentCreate

class ContentRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_content(self, content_id: int):
        return self.db_session.query(Content).filter(Content.id == content_id).first()

    def get_all_contents(self):
        return self.db_session.query(Content).all()

    def create_content(self, content: ContentCreate):
        db_content = Content(**content.dict())
        self.db_session.add(db_content)
        self.db_session.commit()
        self.db_session.refresh(db_content)
        return db_content

    def update_content(self, content_id: int, content: ContentCreate):
        db_content = self.get_content(content_id)
        if db_content:
            db_content.name = content.name
            db_content.description = content.description
            self.db_session.commit()
            self.db_session.refresh(db_content)
        return db_content

    def delete_content(self, content_id: int):
        db_content = self.get_content(content_id)
        if db_content:
            self.db_session.delete(db_content)
            self.db_session.commit()
        return db_content