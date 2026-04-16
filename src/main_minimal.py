"""
Instant Lead Intake System - Step 2: Webhook with Apollo Enrichment
Receives form submissions, enriches with company data, and logs them.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Dict, Optional
import logging
from datetime import datetime
import uuid
from src.enrichment import enrich_company
from src.qualification import qualify_lead
from src.crm_sync import sync_to_hubspot
from src.email_sender import send_response_email, send_sales_notification

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Instant Lead Intake",
    description="Complete: Webhook + Apollo + Claude + HubSpot + SendGrid",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LeadSubmission(BaseModel):
    """Lead form data"""
    name: str
    email: EmailStr
    company: str
    title: str | None = None
    website: str | None = None
    message: str | None = None
    phone: str | None = None

class LeadResponse(BaseModel):
    """Webhook response"""
    status: str
    lead_id: str
    message: str
    timestamp: str
    enrichment: Optional[Dict] = None
    qualification: Optional[Dict] = None
    hubspot: Optional[Dict] = None
    email_lead: Optional[Dict] = None
    email_sales: Optional[Dict] = None

@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "Instant Lead Intake",
        "version": "1.0.0",
        "status": "operational",
        "features": ["webhook", "apollo_enrichment", "claude_qualification", "hubspot_crm", "sendgrid_email"],
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook/lead-intake"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "instant-lead-intake",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/webhook/lead-intake", response_model=LeadResponse)
async def lead_intake_webhook(lead: LeadSubmission):
    """
    Webhook endpoint for lead form submissions
    Step 3: Enriches with Apollo + qualifies with Claude AI
    """
    # Generate unique lead ID
    lead_id = f"lead_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.utcnow().isoformat()

    # Log the received lead
    logger.info(f"[{lead_id}] Lead received:")
    logger.info(f"  Name: {lead.name}")
    logger.info(f"  Email: {lead.email}")
    logger.info(f"  Company: {lead.company}")
    if lead.title:
        logger.info(f"  Title: {lead.title}")
    if lead.website:
        logger.info(f"  Website: {lead.website}")
    if lead.phone:
        logger.info(f"  Phone: {lead.phone}")
    if lead.message:
        logger.info(f"  Message: {lead.message}")

    # Enrich company data with Apollo
    enrichment_data = await enrich_company(
        company_name=lead.company,
        website=lead.website
    )

    logger.info(f"[{lead_id}] Enrichment: {enrichment_data.get('enriched', False)}")
    if enrichment_data.get('enriched'):
        logger.info(f"  Industry: {enrichment_data.get('industry')}")
        logger.info(f"  Employees: {enrichment_data.get('employee_count')}")

    # Qualify lead with Claude AI
    lead_dict = {
        'name': lead.name,
        'email': lead.email,
        'company': lead.company,
        'title': lead.title,
        'message': lead.message,
        'phone': lead.phone,
        'website': lead.website
    }

    qualification_data = await qualify_lead(lead_dict, enrichment_data)

    logger.info(f"[{lead_id}] Qualification: {qualification_data.get('classification')} ({qualification_data.get('score')}/100)")
    if qualification_data.get('classification'):
        logger.info(f"  Recommended: {qualification_data.get('recommended_action')}")

    # Sync to HubSpot CRM
    hubspot_data = await sync_to_hubspot(lead_dict, enrichment_data, qualification_data)

    logger.info(f"[{lead_id}] HubSpot sync: {hubspot_data.get('synced', False)}")
    if hubspot_data.get('synced'):
        logger.info(f"  Contact ID: {hubspot_data.get('id')}")
        if hubspot_data.get('updated'):
            logger.info(f"  Updated existing contact")
        else:
            logger.info(f"  Created new contact")

    # Send confirmation email to lead
    email_lead_data = await send_response_email(lead_dict, qualification_data)

    logger.info(f"[{lead_id}] Lead email: {email_lead_data.get('sent', False)}")
    if email_lead_data.get('sent'):
        logger.info(f"  To: {email_lead_data.get('to')}")

    # Send notification to sales team
    email_sales_data = await send_sales_notification(lead_dict, enrichment_data, qualification_data, hubspot_data)

    logger.info(f"[{lead_id}] Sales email: {email_sales_data.get('sent', False)}")
    if email_sales_data.get('sent'):
        logger.info(f"  To: {email_sales_data.get('to')}")

    # Return success response with all data
    return LeadResponse(
        status="received",
        lead_id=lead_id,
        message="Lead successfully received, enriched, qualified, synced, and emailed",
        timestamp=timestamp,
        enrichment=enrichment_data,
        qualification=qualification_data,
        hubspot=hubspot_data,
        email_lead=email_lead_data,
        email_sales=email_sales_data
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
