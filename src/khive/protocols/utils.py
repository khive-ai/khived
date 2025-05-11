from pydantic import BaseModel


def validate_model_to_dict(cls, v):
    """Serialize a Pydantic model to a dictionary. kwargs are passed to model_dump."""

    if isinstance(v, BaseModel):
        return v.model_dump()
    if v is None:
        return {}
    if isinstance(v, dict):
        return v

    error_msg = "Input value for field <model> should be a `pydantic.BaseModel` object or a `dict`"
    raise ValueError(error_msg)