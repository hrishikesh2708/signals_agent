from pydantic import BaseModel, Field
import httpx
from typing import Any


_SF_TIMEOUT = httpx.Timeout(30.0)

RELATED_IDENTITY_OBJECT: dict[str, str] = {"Opportunity": "Contact"}
# Which related-object fields to surface as mappable identity sources.
RELATED_IDENTITY_FIELDS: list[str] = ["Email", "Phone", "MobilePhone", "FirstName", "LastName"]
# How the runtime joins source -> related object (recorded in the connector config).
RELATED_IDENTITY_JOIN: dict[str, dict] = {
    "Opportunity": {"object": "Contact", "via": "OpportunityContactRole", "filter": "IsPrimary = true"},
}
_SF_FIELD_WHITELIST = ("name", "label", "type", "custom", "picklist_values")
class SalesforceField(BaseModel):
    name: str
    label: str
    type: str
    custom: bool
    # For picklist fields: the available values (schema metadata, not record data).
    picklist_values: list[str] = Field(default_factory=list)

class SalesforceAuthError(RuntimeError):
    """Raised on a 401 from Salesforce so callers can refresh the access token."""

async def get_all_fields(
    instance_url: str, access_token: str, object_name: str
) -> list[SalesforceField]:
    async with httpx.AsyncClient(timeout=_SF_TIMEOUT) as client:
        response = await client.get(
            f"{instance_url}/services/data/v59.0/sobjects/{object_name}/describe",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code == 401:
        raise SalesforceAuthError("Salesforce access token expired")
    if response.status_code >= 400:
        raise RuntimeError(f"Salesforce describe failed: {response.text}")

    data = response.json()
    fields: list[SalesforceField] = []
    for field in data.get("fields", []):
        if field.get("type") in {"address", "location"}:
            continue
        picklist_values = [
            v["value"]
            for v in field.get("picklistValues", [])
            if v.get("active", True) and v.get("value")
        ]
        fields.append(
            SalesforceField(
                name=field["name"],
                label=field["label"],
                type=field["type"],
                custom=field.get("custom", False),
                picklist_values=picklist_values,
            )
        )
    return fields

def is_identity_field(field_name: str) -> bool:
    n = field_name.lower()
    return "email" in n or "phone" in n or "mobile" in n


def object_has_identity(field_names: list[str]) -> bool:
    return any(is_identity_field(n) for n in field_names)

def _pick(obj: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if isinstance(obj, dict):
        return {k: obj.get(k) for k in keys if k in obj}
    return {k: getattr(obj, k) for k in keys if hasattr(obj, k)}


def safe_sf_fields(fields: list[Any]) -> list[dict[str, Any]]:
    """Salesforce field metadata only (name/label/type/custom)."""
    return [_pick(f, _SF_FIELD_WHITELIST) for f in fields]

async def get_eligible_fields(fields: list[SalesforceField], object_name: str, instance_url: str, access_token: str) -> tuple[list[SalesforceField], str]:
        # If the chosen object has no person identity (e.g. Opportunity), surface the
        # related object's identity fields (e.g. primary Contact) as dotted source
        # fields the user can map; the join is recorded in the config at activation.
        related = RELATED_IDENTITY_OBJECT.get(object_name)
        if related and not object_has_identity([f.name for f in fields]):
            wanted = set(RELATED_IDENTITY_FIELDS)
            related_fields = await get_all_fields(instance_url, access_token, related)
            for rf in related_fields:
                if rf.name in wanted:
                    fields.append(SalesforceField(
                        name=f"{related}.{rf.name}", label=f"{related}: {rf.label}",
                        type=rf.type, custom=rf.custom,
                    ))

        safe = safe_sf_fields(fields)
        fingerprint = str(hash(tuple(sorted(f["name"] for f in safe))))
        return safe, fingerprint