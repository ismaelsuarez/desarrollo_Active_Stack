from pydantic import BaseModel, ConfigDict


class ReactivarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
