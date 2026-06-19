import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class PortfolioBuildersSpider:
    def __init__(self, base_url="https://portfoliobuilders.in"):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls = set()
        self.urls_to_visit = [base_url]
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

    def _get_category_from_url(self, url: str) -> str:
        """Determines the data category based on the URL path."""
        path = urlparse(url).path.lower()
        if "/course" in path or "/program" in path:
            return "courses"
        elif "/internship" in path or "/fyugp" in path or "/aicte" in path:
            return "internships"
        else:
            return "general"

    def _get_filename_from_url(self, url: str) -> str:
        """Creates a clean filename from the URL."""
        path = urlparse(url).path.strip('/')
        if not path:
            return "homepage.md"
        
        # Replace slashes and hyphens with underscores
        filename = path.replace('/', '_').replace('-', '_')
        return f"{filename}.md"

    def crawl_and_extract(self, url: str):
        """Fetches the URL, extracts links, and parses structured content."""
        if url in self.visited_urls:
            return
        
        print(f"Crawling: {url}")
        self.visited_urls.add(url)
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch {url}: {e}")
            return

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Discover new links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(url, href)
            
            # Only follow links within the same domain, ignore anchors and mailto
            parsed_full = urlparse(full_url)
            if parsed_full.netloc == self.domain and "#" not in href and "mailto" not in href:
                clean_url = f"{parsed_full.scheme}://{parsed_full.netloc}{parsed_full.path}"
                if clean_url not in self.visited_urls and clean_url not in self.urls_to_visit:
                    self.urls_to_visit.append(clean_url)

        # 2. Extract and structure content
        self._save_structured_data(url, soup)

    def _save_structured_data(self, url: str, soup: BeautifulSoup):
        """Parses semantic HTML into Markdown with Metadata."""
        category = self._get_category_from_url(url)
        filename = self._get_filename_from_url(url)
        
        target_dir = os.path.join(self.data_dir, category)
        os.makedirs(target_dir, exist_ok=True)
        
        filepath = os.path.join(target_dir, filename)
        
        # Extract title
        title_tag = soup.find('title')
        page_title = title_tag.get_text(strip=True) if title_tag else "Portfolio Builders Page"
        
        # Remove junk elements
        for element in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
            element.extract()
            
        content_lines = []
        
        # Add Metadata (Frontmatter) for LlamaIndex
        content_lines.append("---")
        content_lines.append(f"url: {url}")
        content_lines.append(f"title: {page_title}")
        content_lines.append(f"category: {category}")
        content_lines.append("---")
        content_lines.append("\n")
        
        # Parse headings and paragraphs systematically to maintain structure
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table']):
            text = tag.get_text(separator=' ', strip=True)
            if not text:
                continue
                
            if tag.name == 'h1':
                content_lines.append(f"# {text}\n")
            elif tag.name == 'h2':
                content_lines.append(f"## {text}\n")
            elif tag.name == 'h3':
                content_lines.append(f"### {text}\n")
            elif tag.name == 'h4':
                content_lines.append(f"#### {text}\n")
            elif tag.name in ['ul', 'ol']:
                # Basic list extraction
                for li in tag.find_all('li'):
                    li_text = li.get_text(separator=' ', strip=True)
                    if li_text:
                        content_lines.append(f"- {li_text}")
                content_lines.append("\n")
            else:
                # Paragraphs or tables
                content_lines.append(f"{text}\n")
                
        # Join and save
        final_markdown = "\n".join(content_lines)
        
        # Only save if there's actual content beyond metadata
        if len(content_lines) > 6: 
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(final_markdown)
            print(f"  -> Saved structured data to {category}/{filename}")

    def run(self, max_pages=15):
        """Executes the spider for a limited number of pages to avoid infinite loops."""
        print(f"Starting spider at {self.base_url}")
        pages_crawled = 0
        
        while self.urls_to_visit and pages_crawled < max_pages:
            current_url = self.urls_to_visit.pop(0)
            self.crawl_and_extract(current_url)
            pages_crawled += 1
            
        print(f"\nSpider finished. Crawled {pages_crawled} pages.")
        print(f"Data saved in: {self.data_dir}")

if __name__ == "__main__":
    # Create the data structure explicitly
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for folder in ['courses', 'internships', 'general']:
        os.makedirs(os.path.join(base_dir, 'data', folder), exist_ok=True)
        
    spider = PortfolioBuildersSpider()
    # Limit to 15 pages for testing/MVP phase. Can be increased for full production scrape.
    spider.run(max_pages=15)
