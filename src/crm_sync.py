"""
HubSpot CRM integration

Creates or updates contact with:
- Lead data
- Enrichment data
- Qualification score
- Custom properties
"""
import os
import httpx
import logging
from typing import Dict

logger = logging.getLogger(__name__)

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
HUBSPOT_API_URL = "https://api.hubapi.com"

async def sync_to_hubspot(lead_data: Dict, enrichment: Dict, qualification: Dict) -> Dict:
    """
    Create or update contact in HubSpot CRM

    Args:
        lead_data: Lead submission data
        enrichment: Apollo enrichment data
        qualification: Claude qualification data

    Returns:
        Dict with HubSpot contact info
    """
    if not HUBSPOT_API_KEY:
        logger.warning("HubSpot API key not configured, skipping CRM sync")
        return {
            "synced": False,
            "error": "API key not configured"
        }

    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {HUBSPOT_API_KEY}",
                "Content-Type": "application/json"
            }

            # Prepare contact properties
            properties = {
                "email": lead_data['email'],
                "firstname": lead_data['name'].split()[0] if lead_data['name'] else "",
                "lastname": " ".join(lead_data['name'].split()[1:]) if len(lead_data['name'].split()) > 1 else "",
                "company": lead_data['company'],
                "jobtitle": lead_data.get('title', ''),
                "phone": lead_data.get('phone', ''),
                "website": lead_data.get('website', ''),
                "message": lead_data.get('message', ''),

                # Custom properties (create these in HubSpot first)
                "lead_source": "Instant Lead Intake System",
                "lead_score": qualification['score'],
                "lead_classification": qualification['classification'],
                "lead_urgency": qualification.get('urgency', 'medium'),
                "qualification_reasoning": qualification.get('reasoning', ''),
                "recommended_action": qualification.get('recommended_action', ''),
            }

            # Add enrichment data if available (only basic location fields)
            if enrichment.get('enriched'):
                properties.update({
                    "city": enrichment.get('city', ''),
                    "state": enrichment.get('state', ''),
                    "country": enrichment.get('country', ''),
                })
                # Note: industry, numberofemployees, annualrevenue removed
                # These properties don't exist in this HubSpot instance

            # Create or update contact
            payload = {"properties": properties}

            response = await client.post(
                f"{HUBSPOT_API_URL}/crm/v3/objects/contacts",
                json=payload,
                headers=headers,
                timeout=10.0
            )

            if response.status_code in [200, 201]:
                contact = response.json()
                logger.info(f"Created/updated HubSpot contact: {contact.get('id')}")
                return {
                    "synced": True,
                    "id": contact.get('id'),
                    "url": f"https://app.hubspot.com/contacts/{contact.get('id')}"
                }

            elif response.status_code == 409:
                # Contact already exists, update instead
                logger.info("Contact exists, updating...")

                # Get existing contact by email
                search_response = await client.post(
                    f"{HUBSPOT_API_URL}/crm/v3/objects/contacts/search",
                    json={
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": lead_data['email']
                            }]
                        }]
                    },
                    headers=headers,
                    timeout=10.0
                )

                if search_response.status_code == 200:
                    results = search_response.json().get('results', [])
                    if results:
                        contact_id = results[0]['id']

                        # Update contact
                        update_response = await client.patch(
                            f"{HUBSPOT_API_URL}/crm/v3/objects/contacts/{contact_id}",
                            json=payload,
                            headers=headers,
                            timeout=10.0
                        )

                        if update_response.status_code == 200:
                            logger.info(f"Updated HubSpot contact: {contact_id}")
                            return {
                                "synced": True,
                                "id": contact_id,
                                "updated": True,
                                "url": f"https://app.hubspot.com/contacts/{contact_id}"
                            }

            logger.warning(f"HubSpot API returned {response.status_code}: {response.text}")
            return {
                "synced": False,
                "error": f"API returned {response.status_code}",
                "details": response.text
            }

    except httpx.TimeoutException:
        logger.error("HubSpot API timeout")
        return {
            "synced": False,
            "error": "API timeout"
        }

    except Exception as e:
        logger.error(f"Error syncing to HubSpot: {str(e)}")
        return {
            "synced": False,
            "error": str(e)
        }
