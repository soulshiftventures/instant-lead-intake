"""
SendGrid integration for personalized email responses

Sends instant personalized email to lead based on qualification
"""
import os
import httpx
import logging
from typing import Dict

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "hello@deepdivesystems.io")
FROM_NAME = os.getenv("FROM_NAME", "Deep Dive Systems")

def generate_email_content(lead_data: Dict, qualification: Dict) -> tuple[str, str]:
    """
    Generate personalized email based on qualification

    Returns:
        (subject, html_body)
    """
    name = lead_data['name'].split()[0]  # First name
    company = lead_data['company']
    classification = qualification['classification']

    # Personalize based on lead quality
    if classification == "HOT":
        subject = f"Quick response for {company}"
        html_body = f"""
        <p>Hi {name},</p>

        <p>Thanks for reaching out! I reviewed your message and {company}'s situation.</p>

        <p>Based on what you shared, I think we can help. I'd love to jump on a quick 15-minute call this week to walk through a few ideas.</p>

        <p><strong>Here's what caught my attention:</strong></p>
        <ul>
        {"".join(f"<li>{point}</li>" for point in qualification.get('pain_points', []))}
        </ul>

        <p>I have a few time slots available:
        <br>• Tomorrow at 2pm
        <br>• Thursday at 10am
        <br>• Friday at 3pm</p>

        <p>Just reply with what works best for you, and I'll send over a calendar invite.</p>

        <p>Looking forward to connecting,<br>
        {FROM_NAME}</p>
        """

    elif classification == "WARM":
        subject = f"Re: {company} - here's what I'm thinking"
        html_body = f"""
        <p>Hi {name},</p>

        <p>Thanks for getting in touch! I took a look at {company} and your message.</p>

        <p>I have a few thoughts on how we might be able to help. Before we jump on a call, I wanted to share a quick resource that addresses what you mentioned:</p>

        <ul>
        {"".join(f"<li>{point}</li>" for point in qualification.get('talking_points', []))}
        </ul>

        <p>Would you be open to a brief 15-minute call next week to explore this further? Happy to work around your schedule.</p>

        <p>Best,<br>
        {FROM_NAME}</p>
        """

    else:  # COLD
        subject = f"Thanks for reaching out, {name}"
        html_body = f"""
        <p>Hi {name},</p>

        <p>Thanks for contacting us about {company}!</p>

        <p>I've received your message and will review it with our team. We'll get back to you within 24-48 hours with next steps.</p>

        <p>In the meantime, feel free to check out our resources at deepdivesystems.io.</p>

        <p>Best,<br>
        {FROM_NAME}</p>
        """

    return subject, html_body

async def send_sales_notification(lead_data: Dict, enrichment: Dict, qualification: Dict, hubspot_data: Dict) -> Dict:
    """
    Send internal notification to sales team

    Args:
        lead_data: Lead submission data
        enrichment: Apollo enrichment data
        qualification: Claude qualification data
        hubspot_data: HubSpot sync result

    Returns:
        Dict with email send status
    """
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid API key not configured, skipping sales notification")
        return {
            "sent": False,
            "error": "API key not configured"
        }

    try:
        # Email subject based on classification
        classification = qualification['classification']
        score = qualification['score']
        company = lead_data['company']

        subject = f"🔥 {classification} Lead ({score}/100): {company}"

        # Build HTML email with all intelligence data
        html_body = f"""
        <h2>New {classification} Lead: {lead_data['name']}</h2>

        <h3>📊 Quick Stats</h3>
        <ul>
            <li><strong>Score:</strong> {score}/100</li>
            <li><strong>Classification:</strong> {classification}</li>
            <li><strong>Urgency:</strong> {qualification.get('urgency', 'medium')}</li>
        </ul>

        <h3>👤 Contact Info</h3>
        <ul>
            <li><strong>Name:</strong> {lead_data['name']}</li>
            <li><strong>Email:</strong> {lead_data['email']}</li>
            <li><strong>Company:</strong> {company}</li>
            <li><strong>Title:</strong> {lead_data.get('title', 'N/A')}</li>
            <li><strong>Phone:</strong> {lead_data.get('phone', 'N/A')}</li>
            <li><strong>Website:</strong> {lead_data.get('website', 'N/A')}</li>
        </ul>

        <h3>🏢 Company Data (Apollo)</h3>
        <ul>
            <li><strong>Industry:</strong> {enrichment.get('industry', 'N/A')}</li>
            <li><strong>Employees:</strong> {enrichment.get('employee_count', 'N/A')}</li>
            <li><strong>Location:</strong> {enrichment.get('city', '')}, {enrichment.get('state', '')} {enrichment.get('country', '')}</li>
            <li><strong>Founded:</strong> {enrichment.get('founded_year', 'N/A')}</li>
        </ul>

        <h3>💬 Their Message</h3>
        <p><em>"{lead_data.get('message', 'No message provided')}"</em></p>

        <h3>🤖 AI Analysis</h3>
        <p><strong>Why this score:</strong><br>
        {qualification.get('reasoning', 'N/A')}</p>

        <p><strong>Pain Points:</strong></p>
        <ul>
        {"".join(f"<li>{point}</li>" for point in qualification.get('pain_points', []))}
        </ul>

        <p><strong>Talking Points:</strong></p>
        <ul>
        {"".join(f"<li>{point}</li>" for point in qualification.get('talking_points', []))}
        </ul>

        <h3>✅ Recommended Action</h3>
        <p><strong>{qualification.get('recommended_action', 'Follow up within 24 hours')}</strong></p>

        <h3>🔗 HubSpot Contact</h3>
        <p><a href="{hubspot_data.get('url', '#')}">{hubspot_data.get('url', 'Not synced')}</a></p>

        <hr>
        <p><small>Generated by Instant Lead Intake System</small></p>
        """

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            }

            # Send to sales team email (could be configured)
            sales_email = os.getenv("SALES_EMAIL", FROM_EMAIL)

            payload = {
                "personalizations": [{
                    "to": [{
                        "email": sales_email,
                        "name": "Sales Team"
                    }],
                    "subject": subject
                }],
                "from": {
                    "email": FROM_EMAIL,
                    "name": "Lead Intake System"
                },
                "content": [{
                    "type": "text/html",
                    "value": html_body
                }]
            }

            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 202:
                logger.info(f"Sales notification sent for {company}")
                return {
                    "sent": True,
                    "to": sales_email,
                    "subject": subject
                }
            else:
                logger.warning(f"SendGrid returned {response.status_code}: {response.text}")
                return {
                    "sent": False,
                    "error": f"API returned {response.status_code}",
                    "details": response.text
                }

    except Exception as e:
        logger.error(f"Error sending sales notification: {str(e)}")
        return {
            "sent": False,
            "error": str(e)
        }

async def send_response_email(lead_data: Dict, qualification: Dict) -> Dict:
    """
    Send personalized response email via SendGrid

    Args:
        lead_data: Lead submission data
        qualification: Claude qualification data

    Returns:
        Dict with email send status
    """
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid API key not configured, skipping email")
        return {
            "sent": False,
            "error": "API key not configured"
        }

    try:
        # Generate personalized content
        subject, html_body = generate_email_content(lead_data, qualification)

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "personalizations": [{
                    "to": [{
                        "email": lead_data['email'],
                        "name": lead_data['name']
                    }],
                    "subject": subject
                }],
                "from": {
                    "email": FROM_EMAIL,
                    "name": FROM_NAME
                },
                "content": [{
                    "type": "text/html",
                    "value": html_body
                }],
                "tracking_settings": {
                    "click_tracking": {"enable": True},
                    "open_tracking": {"enable": True}
                }
            }

            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 202:
                logger.info(f"Email sent to {lead_data['email']}")
                return {
                    "sent": True,
                    "to": lead_data['email'],
                    "subject": subject
                }
            else:
                logger.warning(f"SendGrid returned {response.status_code}: {response.text}")
                return {
                    "sent": False,
                    "error": f"API returned {response.status_code}",
                    "details": response.text
                }

    except httpx.TimeoutException:
        logger.error("SendGrid API timeout")
        return {
            "sent": False,
            "error": "API timeout"
        }

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return {
            "sent": False,
            "error": str(e)
        }
