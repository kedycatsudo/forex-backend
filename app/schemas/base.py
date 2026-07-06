from pydantic import BaseModel, ConfigDict

class StrictRequestModel(BaseModel):
    model_config=ConfigDict(
        extra="forbid", # reject unknown keys
        str_strip_whitespace=True,
        validate_assignment=True
    )