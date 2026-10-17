import re
import httpx
from bs4 import BeautifulSoup
from typing import Tuple, Optional

def fetch_and_clean_job_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetches job description text from a URL, removes scripts/styles/tags,
    and returns (cleaned_text, error_message).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            if response.status_code != 200:
                return None, f"Could not fetch this job page (Status code {response.status_code}). Please paste the job description instead."
            
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted tags
            for elem in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
                elem.extract()

            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned_text = "\n".join(lines)

            if len(cleaned_text) < 50:
                return None, "The fetched job page had insufficient text. Please paste the job description directly."

            return cleaned_text, None
    except Exception as e:
        return None, f"Failed to connect to job URL ({str(e)}). Please paste the job description instead."
