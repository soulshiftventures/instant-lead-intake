"""
Apollo API integration for company enrichment

Enriches lead data with:
- Company size, industry, revenue
- Employee count
- Technologies used
- Social media profiles
"""
import os
import httpx
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
APOLLO_API_URL = "https://api.apollo.io/v1"

async def enrich_company(company_name: str, website: Optional[str] = None) -> Dict:
    """
    Enrich company data using Apollo API

    Args:
        company_name: Name of the company
        website: Company website URL (optional but improves accuracy)

    Returns:
        Dict with enriched company data
    """
    if not APOLLO_API_KEY:
        logger.warning("Apollo API key not configured, skipping enrichment")
        return {
            "enriched": False,
            "error": "API key not configured"
        }

    try:
        async with httpx.AsyncClient() as client:
            # Apollo API: Organization enrichment
            headers = {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": APOLLO_API_KEY
            }

            params = {
                "domain": website if website else None,
                "organization_name": company_name
            }

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            response = await client.get(
                f"{APOLLO_API_URL}/organizations/enrich",
                params=params,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                org = data.get("organization", {})

                enrichment = {
                    "enriched": True,
                    "company_name": org.get("name", company_name),
                    "domain": org.get("website_url"),
                    "industry": org.get("industry"),
                    "employee_count": org.get("estimated_num_employees"),
                    "annual_revenue": org.get("estimated_annual_revenue"),
                    "founded_year": org.get("founded_year"),
                    "city": org.get("city"),
                    "state": org.get("state"),
                    "country": org.get("country"),
                    "technologies": org.get("technologies", []),
                    "linkedin_url": org.get("linkedin_url"),
                    "facebook_url": org.get("facebook_url"),
                    "twitter_url": org.get("twitter_url")
                }

                logger.info(f"Successfully enriched {company_name}")
                return enrichment

            else:
                error_detail = response.text[:200] if response.text else "No error detail"
                logger.warning(f"Apollo API returned {response.status_code}: {error_detail}")
                return {
                    "enriched": False,
                    "error": f"API returned {response.status_code}: {error_detail}",
                    "company_name": company_name
                }

    except httpx.TimeoutException:
        logger.error(f"Apollo API timeout for {company_name}")
        return {
            "enriched": False,
            "error": "API timeout",
            "company_name": company_name
        }

    except Exception as e:
        logger.error(f"Error enriching {company_name}: {str(e)}")
        return {
            "enriched": False,
            "error": str(e),
            "company_name": company_name
        }
