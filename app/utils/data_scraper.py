import httpx
from bs4 import BeautifulSoup

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

