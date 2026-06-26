import requests

API_URL = "http://localhost:8000/api/admin/knowledge/url"

# We will use the text upload mechanism. Wait, the API only has /upload for files and /url for URLs.
# Let's create a local file and upload it.
import os

fact_sheet_content = """
# Portfolio Builders - Official Fact Sheet

## Company Overview
Portfolio Builders is an EdTech and Career Guidance platform. We specialize in helping students and early-career professionals build their career portfolios. WE ARE NOT A FINANCE COMPANY. We do not deal with stocks, investments, or financial portfolios.

## Core Services
1. **UI/UX Portfolio Building Program**: A comprehensive course to learn UI/UX design and build a professional design portfolio.
2. **Full Stack Development Course**: Learn modern web development to build scalable applications.
3. **Internship Support**:
   - **AICTE Internship Support**: Guidance and projects for AICTE mandated internships.
   - **FYUGP Internship Support**: Support for Four Year Undergraduate Program internships.
4. **Free Portfolio & Resume Review**: Expert feedback on your current career materials.

## Contact Information
- WhatsApp / Phone: +91 7994721792
- Target Audience: Students, Graduates, and Career Switchers.
"""

file_path = os.path.join(os.path.dirname(__file__), "company_facts.txt")
with open(file_path, "w", encoding="utf-8") as f:
    f.write(fact_sheet_content)

print("Created company_facts.txt")

# Now upload it using requests
upload_url = "http://localhost:8000/api/admin/knowledge/upload"
with open(file_path, "rb") as f:
    files = {"file": ("company_facts.txt", f, "text/plain")}
    data = {"category": "general"}
    response = requests.post(upload_url, files=files, data=data)
    
print(f"Upload status: {response.status_code}")
print(response.text)
