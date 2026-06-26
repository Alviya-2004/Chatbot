import re

def evaluate_lead_score(message: str, current_score: int, current_page_url: str = "") -> int:
    msg_lower = message.lower()
    score = current_score
    
    # Lead scoring logic based on requirement Section 6
    # +30: Asked for counselor call
    if any(kw in msg_lower for kw in ["counselor", "counsellor", "call", "talk to human", "schedule a call", "book call", "booking"]):
        score += 30
    # +25: Shared phone number (regex for 10-digit indian numbers or standard formats)
    if re.search(r'\b\d{10}\b', message) or re.search(r'\b\+91\s?\d{10}\b', message):
        score += 25
    # +20: Asked for WhatsApp link
    if any(kw in msg_lower for kw in ["whatsapp", "wa.me", "wp", "group", "community"]):
        score += 20
    # +15: Asked about fee
    if any(kw in msg_lower for kw in ["fee", "cost", "price", "charge", "emi", "pricing", "fees", "how much"]):
        score += 15
    # +15: Asked about batch date
    if any(kw in msg_lower for kw in ["batch", "date", "when does it start", "start date", "schedule"]):
        score += 15
    # +10: Asked about course
    if any(kw in msg_lower for kw in ["course", "learn", "syllabus", "program", "duration"]):
        score += 10
    # +10: Asked about placement
    if any(kw in msg_lower for kw in ["placement", "job", "hiring", "guarantee", "career"]):
        score += 10
    # +10: Asked about certificate
    if any(kw in msg_lower for kw in ["certificate", "validity", "approved", "aicte", "fyugp"]):
        score += 10
    # +10: Visited pricing page
    if current_page_url and "pricing" in current_page_url.lower():
        score += 10
        
    return min(score, 100) # Cap at 100

def get_lead_category(score: int) -> str:
    """Classify lead temperature category based on score."""
    if score <= 30:
        return "Cold lead"
    elif score <= 60:
        return "Warm lead"
    elif score <= 80:
        return "Hot lead"
    else:
        return "High priority lead"
