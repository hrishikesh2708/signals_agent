from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OAuthSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_path: str


class DestinationField(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    type: str = "string"
    required: bool = False
    recommended: bool = False
    description: str = ""
    enum_values: tuple[str, ...] = ()
    constraints: dict[str, Any] = Field(default_factory=dict)
    source_mode_hint: str | None = None


class RequiredMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    secret: bool = False


class PerStageSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    fill: str


class Destination(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    version: str = "1.0"
    enabled: bool = True
    display_name: str
    short_label: str
    detail: str = ""
    aliases: tuple[str, ...] = ()
    connector: str | None = None
    oauth: OAuthSpec
    product_group: str | None = None
    group_default: bool = False
    disambiguators: tuple[str, ...] = ()
    signal_types: tuple[str, ...] = ()
    event_destination: bool = False
    match_keys: tuple[str, ...] = ()
    required_metadata: tuple[RequiredMetadata, ...] = ()
    per_stage: dict[str, PerStageSpec] = Field(default_factory=dict)
    fields: tuple[DestinationField, ...] = ()

    @property
    def oauth_path(self) -> str:
        return self.oauth.start_path

    @property
    def channel_display_name(self) -> str:
        return self.short_label

    @property
    def platform(self) -> str | None:
        if self.product_group:
            return self.product_group
        if self.id == "meta_capi":
            return "meta"
        return None
