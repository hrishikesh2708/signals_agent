
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field

class SignalType(BaseModel):
    id: str = Field(..., description="The ID of the signal type")
    display_name: str = Field(..., description="The display name of the signal type")
    aliases: tuple[str, ...] = Field(..., description="The aliases of the signal type")
    active: bool = Field(..., description="Whether the signal type is active")
    class Config:
        frozen = True

class SignalTypesConfig(BaseModel):
    signal_types: List[SignalType]

class CanonicalField(BaseModel):
    name: str = Field(..., description="The name of the canonical field")
    type: str = Field(...,default="string", description="The type of the canonical field") # Defaults to string if missing
    required: bool = Field(..., default=False, description="Whether the canonical field is required")
    description: str = Field(...,default="", description="The description of the canonical field")
    enum_values: Tuple[str, ...] = Field(default_factory=tuple, description="The enum values of the canonical field")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="The constraints of the canonical field")

    # Replaces the legacy manual stripping logic
    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: Any) -> str:
        cleaned = str(value or "").strip()
        if not cleaned:
            raise ValueError("Field name cannot be empty")
        return cleaned

    # Replaces the manual tuple casting for enums
    @field_validator("enum_values", mode="before")
    @classmethod
    def cast_enum_values(cls, value: Any) -> Tuple[str, ...]:
        if not value:
            return ()
        return tuple(str(v) for v in value)

class CanonicalSchemaConfig(BaseModel):
    destination_type: str
    version: str
    fields: List[CanonicalField]