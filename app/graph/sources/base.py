from pydantic import BaseModel
from typing import List

class Sources(BaseModel):
    id: str
    catagory: str
    display_name: str


class Destinations(BaseModel):
    id: str
    display_name: str
    channel_display_name: str
    alias: List[str]
    details: str


sources = [
    Sources(id='salesforce', catagory='CRM', display_name='Salesforce'),
    Sources(id='hubspot', catagory='CRM', display_name='HubSpot'),
    Sources(id='zoho', catagory='CRM', display_name='Zoho')
]

destinations = [
    Destinations(id='meta_capi', display_name='Meta Conversions API', channel_display_name='Meta', alias=["meta", "facebook", "instagram", "fb"], details='CRM Conversions API'),
    Destinations(id='google_offline_conversions', display_name='Google Offline Conversions', channel_display_name='Google (Offline)', alias=["google", "google ads", "adwords", "youtube"], details='Offline Conversions'),
    Destinations(id='google_customer_match', display_name='Google Customer Match', channel_display_name='Google (Audience)', alias=["google", "google ads", "adwords", "youtube"], details='Customer Match audience')
]