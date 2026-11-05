from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Response schema that can be built straight from an ORM object (`return orm_obj`)."""

    model_config = ConfigDict(from_attributes=True)
