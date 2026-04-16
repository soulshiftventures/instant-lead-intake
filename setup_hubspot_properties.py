#!/usr/bin/env python3
"""
Setup HubSpot Custom Properties for Lead Intelligence
Creates 6 custom properties needed for AI qualification data
"""
import os
import sys
import httpx

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
HUBSPOT_API_URL = "https://api.hubapi.com"

# Property definitions for AI-powered lead qualification
properties = [
    {
        "name": "lead_source",
        "label": "Lead Source",
        "type": "string",
        "fieldType": "text",
        "groupName": "contactinformation",
        "description": "Source system that generated this lead"
    },
    {
        "name": "lead_score",
        "label": "Lead Score",
        "type": "number",
        "fieldType": "number",
        "groupName": "contactinformation",
        "description": "AI-generated score 0-100"
    },
    {
        "name": "lead_classification",
        "label": "Lead Classification",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "description": "AI classification: HOT/WARM/COLD",
        "options": [
            {"label": "HOT", "value": "HOT"},
            {"label": "WARM", "value": "WARM"},
            {"label": "COLD", "value": "COLD"}
        ]
    },
    {
        "name": "lead_urgency",
        "label": "Lead Urgency",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "description": "Urgency level from AI analysis",
        "options": [
            {"label": "High", "value": "high"},
            {"label": "Medium", "value": "medium"},
            {"label": "Low", "value": "low"}
        ]
    },
    {
        "name": "qualification_reasoning",
        "label": "Qualification Reasoning",
        "type": "string",
        "fieldType": "textarea",
        "groupName": "contactinformation",
        "description": "AI explanation of qualification score"
    },
    {
        "name": "recommended_action",
        "label": "Recommended Action",
        "type": "string",
        "fieldType": "textarea",
        "groupName": "contactinformation",
        "description": "AI-recommended next steps for sales"
    }
]


def create_property(prop_def):
    """Create a single property via HubSpot API"""
    if not HUBSPOT_API_KEY:
        return {"created": False, "error": "API key not set", "name": prop_def['name']}

    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = httpx.post(
            f"{HUBSPOT_API_URL}/crm/v3/properties/contacts",
            json=prop_def,
            headers=headers,
            timeout=10.0
        )

        if response.status_code == 201:
            return {"created": True, "name": prop_def['name']}
        elif response.status_code == 409:
            # Property already exists - that's fine
            return {"created": False, "exists": True, "name": prop_def['name']}
        else:
            error_text = response.text[:200] if response.text else "Unknown error"
            return {"created": False, "error": f"{response.status_code}: {error_text}", "name": prop_def['name']}

    except httpx.TimeoutException:
        return {"created": False, "error": "API timeout", "name": prop_def['name']}
    except Exception as e:
        return {"created": False, "error": str(e), "name": prop_def['name']}


def main():
    if not HUBSPOT_API_KEY:
        print("❌ HUBSPOT_API_KEY not set")
        print("   Set it with: export HUBSPOT_API_KEY='your_key_here'")
        sys.exit(1)

    print("Creating HubSpot custom properties for AI lead qualification...\n")

    results = {"created": [], "existed": [], "failed": []}

    for prop in properties:
        result = create_property(prop)

        if result.get("created"):
            print(f"✅ Created: {result['name']}")
            results["created"].append(result['name'])
        elif result.get("exists"):
            print(f"✓  Exists: {result['name']}")
            results["existed"].append(result['name'])
        else:
            print(f"❌ Failed: {result['name']}")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            results["failed"].append(result['name'])

    print(f"\n📊 Summary:")
    print(f"   Created: {len(results['created'])}")
    print(f"   Already existed: {len(results['existed'])}")
    print(f"   Failed: {len(results['failed'])}")

    if results["failed"]:
        print("\n❌ Some properties failed to create")
        sys.exit(1)
    else:
        print("\n✅ All properties ready! HubSpot CRM sync will now work.")
        print("   View in HubSpot: Settings → Properties → filter by 'lead_'")


if __name__ == "__main__":
    main()
