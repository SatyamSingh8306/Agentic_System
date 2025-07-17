#from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import logging
import asyncio
import json
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Annotated
from datetime import datetime, timedelta,timezone
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaEmbeddings
import re
from dateutil.relativedelta import relativedelta
from redis import Redis
from langchain.agents import initialize_agent, AgentType
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.tools import StructuredTool
from datetime import datetime, timedelta
import re
from pymongo import ASCENDING
import logging
from agents.llm import __llm
import agents.system_prompts as sp
from dotenv import load_dotenv, find_dotenv
logger = logging.getLogger(__name__)
# Load environment variables
load_dotenv(find_dotenv())
from os import getenv

redis_client = Redis(
    host=getenv('REDIS_HOST', "localhost"),
    port=getenv('REDIS_PORT'),
    username="default",
    password=getenv('REDIS_PASSWORD'),
)

embedding_model = OllamaEmbeddings(model="bge-m3", base_url = getenv("OLLAMA_BASE_URL"))
# embedding_model = None
similarity_threshold = 0

client = MongoClient(getenv('DB'))
db = client['event_db']
event_collection = db['events']
order_collection = db['orders']
chat_collection = db['agp_session']
offer_collection = db['offers']
user_collection = db['users']
retrieval_collection = db['retrieval_store']
new_event_collection = db['new_events']


async def get_events(

)->List:
    """To get all the list of events"""
    res = []
    cursor = new_event_collection.find({},{"embedding":0})
    async for data in cursor:
        res.append(data)
    return res


def get_event(event_id:Annotated[str, "A unique Identifier to a paricular event."]):
    """To get a paricular event pased on id"""
    try:
        return event_collection.find_one({"event_id":event_id})
    except Exception as e:
        logging.error(f"Error fetching event: {e}")
        return None
   
def update_booking_success(order_id:Annotated[str, "A unique id for user who have placed his order"]) -> dict:
    """To check the booking status of a person based on order id"""
    try:
        order_collection.update_one({"transaction_id":order_id},{"$set":{"payment_status":"completed"}})
        return {'status':'success'}
    except Exception as e:
        logging.error(f"Error updating booking success: {e}")
        return {'status':'failed'}


def search_event(query: Optional[str] = None, date: Optional[str] = None, price: Optional[str] = None, top_rated:bool = False,k: int = 3):
    """
    Search for events based on query, month, and price, sorted by upcoming event dates.

    Parameters:
    - query (Optional[str]): The user's search query containing keywords, genres, or event types.
    - date (Optional[str]): The preferred month for the event (e.g., "January 2025").
    - price (Optional[str]): The preferred price range for the event (e.g., "₹500-₹1000" or "under ₹1000").
    - k (int): The number of results to prioritize. Default is 3.

    Returns:
    - full_res (list): A list of full search results with additional details.
    """
    
    score_threshold = 0
    pipeline = []

    
    if query and isinstance(query, str) and embedding_model:  # If query exists, use vector search
        query_embedding = embedding_model.embed_query(query)
        pipeline.append({
            "$vectorSearch": {
                "index": "ten_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 100,
                "limit": 50
            }
        })

    if date:
        try:
            date = date.strip().lower()

            
            range_match = re.search(r"(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", date)
            
            # Check for single ISO format date
            iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", date)

            if range_match:
                start_date_str, end_date_str = range_match.groups()
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                current_date = datetime.now(timezone.utc)
                start_date = max(start_date, current_date)

                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

                logging.info(f"Range search: {start_date} to {end_date}")

                pipeline.append({
                    "$match": {
                        "event_date": {"$gte": start_date, "$lt": end_date}
                    }
                })

            elif iso_match:
                date_str = iso_match.group(1)
                start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                end_date = start_date + timedelta(days=1)

                logging.info(f"Single date search: {start_date} to {end_date}")

                pipeline.append({
                    "$match": {
                        "event_date": {"$gte": start_date, "$lt": end_date}
                    }
                })

            else:
                # Check for YYYY-MM
                date_matches = re.findall(r"(\d{4})-(\d{2})", date)
                logging.info(f"Date matches found: {date_matches}")

                if len(date_matches) == 1:
                    year, month = map(int, date_matches[0])
                    if 1 <= month <= 12:
                        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
                        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc) if month < 12 else datetime(year + 1, 1, 1, tzinfo=timezone.utc)

                        logging.info(f"Month search: {start_date} to {end_date}")

                        pipeline.append({
                            "$match": {
                                "event_date": {"$gte": start_date, "$lt": end_date}
                            }
                        })
                    else:
                        logging.error(f"Invalid month value: {month}. Must be 1–12.")

        except Exception as e:
            logging.error(f"Error parsing date: {e}")
            return [], []
    


    if price:
        try:
            if "-" in price:
                min_price, max_price = map(lambda x: int(re.sub(r"[^\d]", "", x)), price.split("-"))
                pipeline.append({"$match": {"cost": {"$gte": min_price, "$lte": max_price}}})
                logging.info(f"Filtering between {min_price} and {max_price}")
            elif "under" in price.lower():
                max_price = int(re.sub(r"[^\d]", "", price))
                pipeline.append({"$match": {"cost": {"$lte": max_price}}})
                logging.info(f"Filtering under {max_price}")
            elif "above" in price.lower():
                min_price = int(re.sub(r"[^\d]", "", price))
                pipeline.append({"$match": {"cost": {"$gte": min_price}}})
                logging.info(f"Filtering above {min_price}")

        except Exception as e:
            logging.error(f"Error parsing price: {e}")
            return [], []


    
    pipeline.append({
        "$project": {
            "event_id": 1, "event_name": 1, "event_date": 1, "event_time": 1,
            "theater_name": 1, "theater_address": 1, "highlights": 1, "cost": 1,
            "tickets_sold": 1,"score": {"$meta": "vectorSearchScore"}
        }
    })

    
    # Sorting by event date, and if query exists, prioritize score
    if query:
        pipeline.append({"$sort": {"parsed_event_date": ASCENDING, "score": -1}})
    else:
        pipeline.append({"$sort": {"parsed_event_date": ASCENDING}})



    results = new_event_collection.aggregate(pipeline).to_list(length=None)
    full_res = []
    res = []
    
    for result in results:
        event_id = result['event_id']
        score = result.get('score', 0)

        if not query or score >= score_threshold:
            res.append(event_id)
            full_res.append(result)

    return full_res

@tool
def search_tool(
    query: Annotated[Optional[str], 'The query of the user if no query then return " " '] = "",
    city: Annotated[Optional[str], 'City of the user (has to be an actual city) if no city then return " " '] ="",
    price: Annotated[Optional[str], "It can be 'under max price', 'above min price', 'min price - max price' if no price then return ' ' "] = "",
    date: Annotated[Optional[str], "date (string, optional) – Event date (YYYY-MM-DD) or (YYYY-MM-DD to YYYY-MM-DD) if no date then return ' ' "]= "",
    top_rated: Annotated[Optional[bool], "Whether we want top rated events or not, if no top_rated then return boolean False"] = False
):
    """
    Search for events based on user parameters and return compact Markdown-formatted output.
    """

    # logging.info(f"Searched with query: {query}, date: {date}, price: {price}, city: {city}, top_rated: {top_rated}")
    

    # Normalize inputs
    query = query.strip() if query else ""
    city = city.strip().capitalize() if city else ""
    price = price if price else ""
    date = date if date else ""
    top_rated = bool(top_rated)

    # Clean up
    if query.lower() in ["none", ""]:
        query = ""
    if city.lower() in ["none", ""]:
        city = ""
    if 'agp' in query.lower():
        query = ""

    # Default date range
    if not date:
        current_date = datetime.now()
        end_date = current_date + relativedelta(months=12)
        date = f"{current_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

    full_res = search_event(query=query, date=date, price=price, top_rated=top_rated)
    

    # Sort and filter
    full_res.sort(key=lambda x: x.get('tickets_sold', 0), reverse=True)
    
    if city:
        full_res = [event for event in full_res if city in event.get('theater_address', '')]

    if query:
        final_results = list(filter(lambda x: x.get('score', 0) > similarity_threshold, full_res))
    else:
        final_results = full_res

    # Keep only important keys
    important_keys = [
        'event_name', 'event_date', 'event_time', 'theater_name',
        'theater_address', 'cost', 'genre', 'city'
    ]

    # Convert to Markdown string
    markdown_output = "### 🎟 Upcoming Events\n\n"
    if not final_results:
        markdown_output += "No events found based on your criteria."
    else:
        for i, event in enumerate(final_results, 1):
            markdown_output += f"{i}. {event.get('event_name', 'Untitled Event')}\n"
            markdown_output += f"-Date: {event.get('event_date', 'N/A')} at {event.get('event_time', 'N/A')}\n"
            markdown_output += f"-Venue: {event.get('theater_name', 'Unknown')} – {event.get('theater_address', 'N/A')}\n"
            markdown_output += f"-Cost: ₹{event.get('cost', 'N/A')}\n"
            markdown_output += f"-Genre: {event.get('genre', 'N/A')} | City: {event.get('city', 'N/A')}\n\n"

    return {
        "output": markdown_output
    }



# System prompt for the event agent
# SYSTEM_PROMPT = """

# """

# Create the agent
# def create_event_agent():
#     """Create and configure the event dealing agent"""
#     try:
#         # Import your LLM here
#         from llm import __llm
        
#         # Create the agent with tools
#         agent = initialize_agent(
#             llm=__llm,
#             tools=[
#                 get_events
#             ],
#             agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
#             verbose=True,
#             agent_kwargs={
#                 "system_message": SYSTEM_PROMPT
#             }
#         )
        
#         return agent
#     except ImportError:
#         logger.error("Could not import LLM. Please ensure llm.py is available with __llm defined.")
#         return None

sale_agent = agent = initialize_agent(
    llm=__llm,
    tools=[search_tool],  # if needed
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=2,  # optional, default fine
    agent_kwargs={
        "prefix": sp.sale_system_prompt
    },
    early_stopping_method="generate"
)


async def sale_agent_answer(query : str):
    agent = sale_agent
    response = await agent.arun(query)
    return response

def get_answer(query):
    return asyncio.run(sale_agent_answer(query=query))

if __name__ == "__main__":
    def main():
        # agent = sale_agent
        
        # # Test queries
        # test_queries = [
        #     "Events in delhi"
        # ]
        
        # for query in test_queries:
        #     print(f"\n🔍 Query: {query}")
        #     response = agent.invoke(query)
        #     # agent.invoke(query)
            # print(f"🤖 Response: {response}")
            ans = search_tool.invoke({
                "query": "fun",
                "city": "Delhi"
            }, verbose=True)
            print(ans)
            
    main()



   
