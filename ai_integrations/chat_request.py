import os
import json
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from app.models.competitor import Competitor, CompetitorBaseList, SingleCompetitorSearchResult
from typing import List

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

async def find_competitors_openai(prompt: str) -> CompetitorBaseList:
    print("Step 3: AI engine running")
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant that identifies business competitors based on given information."},
            {"role": "user", "content": prompt}
        ],
        response_model=CompetitorBaseList,
        temperature=0.1,
        max_tokens=4060,
    )
    return response


async def lookup_competitor_openai(prompt: str) -> SingleCompetitorSearchResult:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant that identifies business competitors based on given information."},
            {"role": "user", "content": prompt}
        ],
        response_model=SingleCompetitorSearchResult,
        temperature=0.1,
        max_tokens=4060,
    )
    print(f"The direct response: \n\n{response}")
    return response
