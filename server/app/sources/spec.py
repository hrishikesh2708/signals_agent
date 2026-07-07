from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OAuthSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_path: str
    callback_path: str
    pkce: bool
    client_id_env: str
    client_secret_env: str
    redirect_uri_env: str
    scope_env: str
    authorize_url: str
    token_url: str
    login_url_env: str | None = None
    default_login_url: str | None = None
    accounts_url_env: str | None = None
    default_accounts_url: str | None = None


class SchemaSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    skip_types: tuple[str, ...] = ()
    expose: tuple[str, ...] = Field(min_length=1)
    identity_field_patterns: tuple[str, ...] = ()
    api_version: str | None = None


class RelatedIdentityJoin(BaseModel):
    model_config = ConfigDict(frozen=True)

    object: str
    via: str
    filter: str | None = None


class RelatedIdentitySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    related_object: str
    surface_fields: tuple[str, ...] = Field(min_length=1)
    join: RelatedIdentityJoin


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    category: str
    display_name: str
    aliases: tuple[str, ...] = ()
    enabled: bool = True
    connector: str | None = None
    oauth: OAuthSpec
    objects_discover: bool = False
    objects_common: tuple[str, ...] = Field(min_length=1)
    schema_: SchemaSpec = Field(alias="schema")
    related_identity: dict[str, RelatedIdentitySpec] = Field(default_factory=dict)
    automap_synonyms: str | None = None

    def related_identity_for(self, object_name: str) -> RelatedIdentitySpec | None:
        return self.related_identity.get(object_name)

    @property
    def schema(self) -> SchemaSpec:
        return self.schema_
