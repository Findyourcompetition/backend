import httpx
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

async def scrape_competitor_data(website: str) -> str:
    if not website:
        return "No website provided for scraping."

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(website, timeout=10.0)
            response.raise_for_status()
        except httpx.RequestError as e:
            return f"An error occurred while requesting {website}: {str(e)}"
        except httpx.HTTPStatusError as e:
            return f"Error response {e.response.status_code} while requesting {website}"

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract relevant information from the website
    title = soup.title.string if soup.title else "No title found"
    description = soup.find('meta', attrs={'name': 'description'})
    description = description['content'] if description else "No description found"
    
    # Extract main content (this is a simple example and might need adjustment)
    main_content = soup.find('main')
    if main_content:
        text_content = main_content.get_text(strip=True)[:500]  # Limit to 500 characters
    else:
        text_content = soup.get_text(strip=True)[:500]
        
    scraped_data = f"""
    Title: {title}
    Description: {description}
    Main Content Preview: {text_content}...
    """
    
    return scraped_data



async def scrape_logo(website: str) -> str:
    try:
        response = requests.get(website, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for common logo locations
        potential_logos = soup.select('img[src*=logo], a.logo img, .logo img, #logo img')
        
        if potential_logos:
            logo_src = potential_logos[0].get('src')
            if logo_src:
                return urljoin(website, logo_src)
            
        # If no logo found, return a default or empty string
        return ""
    except Exception as e:
        print(f"Error scraping logo from {website}: {str(e)}")
        return ""






