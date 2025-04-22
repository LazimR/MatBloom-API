from pydantic import BaseModel

class ContentBase(BaseModel):
    name: str

class ContentCreate(ContentBase):
    pass

class Content(ContentBase):
    id: int

    model_config = {
        "from_attributes": True
    }