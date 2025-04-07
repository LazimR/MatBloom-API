from pydantic import BaseModel

class ContentBase(BaseModel):
    name: str

class ContentCreate(ContentBase):
    pass

class Content(ContentBase):
    id: int

    class Config:
        from_attributes = True