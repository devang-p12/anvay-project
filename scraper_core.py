import trafilatura
import asyncio
import aiohttp
from typing import List, Dict

class ScraperCore:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def fetch_text(self, url: str) -> str:
        """
        Fetches and extracts clean text from a single URL.
        """
        if not url or not url.startswith("http"):
            return ""
            
        try:
            # Trafilatura's native fetch is synchronous, 
            # so we use aiohttp for async retrieval and then pass to trafilatura.
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return f"Error: Received status {response.status}"
                    html = await response.text()
                    
            content = trafilatura.extract(html)
            return content if content else "Warning: Content extraction yielded no text."
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"

    async def scrape_batch(self, urls: List[str]) -> Dict[str, str]:
        """
        Scrapes a batch of URLs in parallel.
        """
        tasks = [self.fetch_text(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return dict(zip(urls, results))

if __name__ == "__main__":
    # Quick standalone test
    async def main():
        scraper = ScraperCore()
        test_url = "https://theindianawaaz.com/india-condemns-pakistans-airstrike-on-omid-addiction-treatment-hospital-in-kabul/"
        print(f"Testing scraper on: {test_url}")
        text = await scraper.fetch_text(test_url)
        print("\n--- EXTRACTED CONTENT ---")
        print(text[:1000] + "...")
        
    asyncio.run(main())
