from pydantic import BaseModel, Field


class ErrorResponseSchema(BaseModel):
    err_code: str = Field(..., description="A unique string code for the error type.")
    message: str = Field(..., description="A human-readable error message.")
    details: dict = Field(default_factory=dict, description="Additional context about the error.")