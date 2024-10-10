import os
import json
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from app.models.competitor import Competitor, CompetitorList
from typing import List
from app.services.competitor import insert_competitors

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = instructor.from_openai(
    OpenAI(
        api_key=OPENAI_API_KEY
    ),
    mode=instructor.Mode.JSON
)


def send_openai_request(prompt: str) -> str:
    completion = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": prompt}], max_tokens=1000,  
    )
    content = completion.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response.")
    return content

async def find_competitors_openai(prompt: str) -> CompetitorList:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant that identifies business competitors based on given information."},
            {"role": "user", "content": prompt}
        ],
        response_model=CompetitorList,
        temperature=0.1,
        max_tokens=2000,
    )
    print(f"The direct response: \n\n{response}")
    await insert_competitors(response.competitors)
    return response

def lookup_competitor_openai(prompt: str) -> CompetitorList:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant that identifies business competitors based on given information."},
            {"role": "user", "content": prompt}
        ],
        response_model=CompetitorList,
        temperature=0.1,
        max_tokens=2000,
    )
    print(f"The direct response: \n\n{response}")
    return response
