from app.models.competitor import Competitor, CompetitorList, CompetitorBaseList, SingleCompetitorSearchResult
from app.utils.data_scraper import scrape_competitor_data, scrape_logo
from ai_integrations.chat_request import send_openai_request, find_competitors_openai, lookup_competitor_openai
from typing import List
import asyncio

async def generate_competitor_insights(competitor: Competitor) -> list[str]:
    # Scrape additional data about the competitor
    scraped_data = await scrape_competitor_data(competitor.website)
    
    # Prepare the prompt for OpenAI
    prompt = f"""
    Analyze the following competitor information and provide 3-5 key insights:
    
    Company: {competitor.name}
    Business Type: {competitor.business_type}
    Location: {competitor.location}
    Revenue: {competitor.revenue}
    Target Market: {competitor.target_market}
    Description: {competitor.description}
    
    Additional scraped data:
    {scraped_data}
    
    Please provide insights on their market position, strengths, weaknesses, and potential strategies.
    """
    
    # Get insights from OpenAI
    response = send_openai_request(prompt)
    
    # Parse the response into a list of insights
    insights = response.split('\n')
    insxights = [insight.strip() for insight in insights if insight.strip()]
    
    return insights[:5]  # Return up to 5 insights


async def find_competitors_ai(business_description: str, location: str) -> CompetitorList:
    prompt = f"""
        Given the following business description and location, identify the top 12 competitors:
        Business: {business_description}
        Location: {location}

        Return an empty string ("") in the logo field.
        """
    response = await find_competitors_openai(prompt)
    competitors = [Competitor(**comp.model_dump()) for comp in response.competitors]
    return competitors

async def lookup_competitor_ai(name_or_url: str) -> SingleCompetitorSearchResult:
    prompt = f"""
        Given the following name or website about a business, return the top 12 competitors of the business, including the business as the first item. Make sure to include the country(ies) in which the competitor operate, and instead of "global" for countries that operate globally, list the top 10 countries they operate in.
        Name or URL: {name_or_url}

        Return an empty string ("") in the logo field.
        """
    response = await lookup_competitor_openai(prompt)
    return response.competitors

