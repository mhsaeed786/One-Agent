import requests
from bs4 import BeautifulSoup

class WebScraperTool:
    """Tool for scraping web pages automatically."""
    def __init__(self):
        self.name = "web_scraper"
        self.description = "Scrapes data from websites."

    def execute(self, url: str) -> str:
        try:
            # Basic implementation for functional purposes
            if not url.startswith("http"):
                url = "https://" + url
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract text and remove excess whitespace
            text = ' '.join(soup.stripped_strings)
            return text[:1000] + "... (truncated)" if len(text) > 1000 else text
        except Exception as e:
            return f"Error scraping {url}: {str(e)}"
