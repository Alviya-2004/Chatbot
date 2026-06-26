import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

BASE_URL = "https://portfoliobuilders.in"
API_URL = "http://localhost:8000/api/admin/knowledge/url"
visited_urls = set()
urls_to_visit = set([BASE_URL])

def is_internal_url(url, base_domain):
    parsed = urlparse(url)
    return parsed.netloc == "" or parsed.netloc == base_domain

def crawl_and_index():
    base_domain = urlparse(BASE_URL).netloc
    indexed_count = 0

    print(f"Starting automated crawl of {BASE_URL}...")

    while urls_to_visit:
        current_url = urls_to_visit.pop()
        if current_url in visited_urls:
            continue
            
        visited_urls.add(current_url)
        print(f"Crawling: {current_url}")

        try:
            # 1. Fetch the page to find more links
            headers = {"User-Agent": "CarePilot-Crawler"}
            response = requests.get(current_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links on the page
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # Skip anchors and mailto/tel
                if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                    continue
                    
                full_url = urljoin(BASE_URL, href)
                
                # Check if it's an internal link
                if is_internal_url(full_url, base_domain):
                    # Clean up the URL (remove trailing slashes for consistency)
                    full_url = full_url.rstrip('/')
                    if full_url not in visited_urls:
                        urls_to_visit.add(full_url)
            
            # 2. Send the current URL to the backend API to index it in RAG
            # We determine category based on url
            category = "general"
            if "/course" in current_url.lower() or "/program" in current_url.lower():
                category = "courses"
            elif "/internship" in current_url.lower():
                category = "internships"
                
            api_response = requests.post(
                API_URL, 
                json={"url": current_url, "category": category},
                timeout=30
            )
            
            if api_response.status_code == 200:
                print(f"  [SUCCESS] Successfully indexed: {current_url}")
                indexed_count += 1
            else:
                print(f"  [FAILED] Failed to index: {current_url} (Status: {api_response.status_code})")
                
            # Sleep slightly to avoid overwhelming the server
            time.sleep(1)
            
        except Exception as e:
            print(f"  [ERROR] processing {current_url}: {str(e)}")

    print("-" * 40)
    print(f"Crawl Complete! Successfully discovered and indexed {indexed_count} pages.")

if __name__ == "__main__":
    crawl_and_index()
