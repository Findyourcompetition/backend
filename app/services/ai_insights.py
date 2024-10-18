from app.models.competitor import Competitor, CompetitorList
from app.utils.data_scraper import scrape_competitor_data, scrape_logo
from app.services.competitor import insert_competitors
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
    insights = [insight.strip() for insight in insights if insight.strip()]
    
    return insights[:5]  # Return up to 5 insights


async def process_competitor(competitor: Competitor) -> Competitor:
    if competitor.website:
        logo_url = await scrape_logo(competitor.website)
        if logo_url:
            competitor.logo = logo_url
    return competitor

async def find_competitors_ai(business_description: str, location: str) -> CompetitorList:
    prompt = f"""
        Given the following business description and location, identify the top 6 competitors:
        Business: {business_description}
        Location: {location}

        If you cannot find the valid logo url for the competitor, make sure you provide the cometitor's website favicon.
        """
    response = await find_competitors_openai(prompt)
    # Process each competitor to scrape their logo
    tasks = [process_competitor(competitor) for competitor in response.competitors]
    updated_competitors = await asyncio.gather(*tasks)
    
    response.competitors = updated_competitors
    await insert_competitors(response.competitors)
    return response



async def lookup_competitor_ai(name_or_url: str) -> CompetitorList:
    prompt = f"""
        Given the following name or link about a business, return the top 5 competitors of the business, including the business as the first item.
        Name or URL: {name_or_url}

        If you cannot find the valid logo url for the competitor, make sure you provide the cometitor's website favicon.
        """
    response = lookup_competitor_openai(prompt)
    tasks = [process_competitor(competitor) for competitor in response.competitors] 
    updated_competitors = await asyncio.gather(*tasks)              
    response.competitors = updated_competitors
    return response
