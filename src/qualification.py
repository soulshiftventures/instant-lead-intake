"""
Claude API integration for lead qualification

Uses AI to:
- Score lead quality (0-100)
- Classify as Hot/Warm/Cold
- Generate personalized talking points
- Identify pain points from message
"""
import os
from anthropic import AsyncAnthropic
import logging
from typing import Dict
import json

logger = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

QUALIFICATION_PROMPT = """You are a B2B SaaS sales qualification AI. Analyze this lead and provide a structured assessment.

Lead Information:
- Name: {name}
- Title: {title}
- Company: {company}
- Email: {email}
- Message: {message}

Company Enrichment Data:
{enrichment}

Your task:
1. Score this lead from 0-100 based on:
   - Title/seniority (decision maker?)
   - Company size and revenue
   - Industry fit
   - Message quality (specific pain point mentioned?)
   - Urgency indicators

2. Classify as:
   - HOT (70-100): High priority, likely to convert
   - WARM (40-69): Good potential, needs nurturing
   - COLD (0-39): Low priority or poor fit

3. Identify key pain points from their message

4. Generate 2-3 personalized talking points for sales team

Respond in JSON format:
{{
  "score": <0-100>,
  "classification": "HOT|WARM|COLD",
  "reasoning": "<why this score?>",
  "pain_points": ["<point1>", "<point2>"],
  "talking_points": ["<point1>", "<point2>"],
  "recommended_action": "<next step>",
  "urgency": "high|medium|low"
}}
"""

async def qualify_lead(lead_data: Dict, enrichment: Dict) -> Dict:
    """
    Qualify lead using Claude AI

    Args:
        lead_data: Lead submission data
        enrichment: Apollo enrichment data

    Returns:
        Dict with qualification results
    """
    try:
        # Format enrichment data for prompt
        enrichment_summary = json.dumps(enrichment, indent=2) if enrichment.get("enriched") else "No enrichment data available"

        # Create prompt
        prompt = QUALIFICATION_PROMPT.format(
            name=lead_data.get('name', 'Unknown'),
            title=lead_data.get('title', 'Unknown'),
            company=lead_data.get('company', 'Unknown'),
            email=lead_data.get('email', 'Unknown'),
            message=lead_data.get('message', 'No message provided'),
            enrichment=enrichment_summary
        )

        # Call Claude API
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            temperature=0.3,  # Lower temperature for more consistent scoring
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        content = response.content[0].text

        # Try to extract JSON from response
        try:
            # Find JSON in response (might have extra text)
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_str = content[json_start:json_end]
            qualification = json.loads(json_str)

            logger.info(f"Lead qualified: {qualification['classification']} ({qualification['score']}/100)")
            return qualification

        except json.JSONDecodeError:
            logger.error(f"Failed to parse Claude response as JSON: {content}")
            # Fallback qualification
            return {
                "score": 50,
                "classification": "WARM",
                "reasoning": "Unable to parse AI response, defaulting to WARM",
                "pain_points": [],
                "talking_points": [],
                "recommended_action": "Manual review required",
                "urgency": "medium",
                "raw_response": content
            }

    except Exception as e:
        logger.error(f"Error qualifying lead: {str(e)}")
        # Fallback qualification
        return {
            "score": 50,
            "classification": "WARM",
            "reasoning": f"Error during qualification: {str(e)}",
            "pain_points": [],
            "talking_points": [],
            "recommended_action": "Manual review required",
            "urgency": "medium",
            "error": str(e)
        }
