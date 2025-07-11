#from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
import asyncio
import json
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Annotated
from datetime import datetime, timedelta,timezone
from langchain_huggingface import HuggingFaceEmbeddings
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
from llm import __llm
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

# embedding_model = HuggingFaceEmbeddings(model="BAAI/bge-m3")
embedding_model = None
similarity_threshold = 0.75

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
                "limit": 20
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
def search_tool(query:Annotated[Optional[str], 'The query of the user if no query then return "" '], 
                city:Annotated[Optional[str], 'City of the user (has to be an actual city) if no city then return "" '], 
                price: Annotated[Optional[str], "It can be 'under max price', 'above min price', 'min price - max price' if no price then return '' "], 
                date: Annotated[Optional[str], "date (string, optional) – Event date (YYYY-MM-DD) or (YYYY-MM-DD to YYYY-MM-DD) if no date then return '' "], 
                top_rated: Annotated[Optional[bool], "Whether we want top rated events or not, if no top_rated then return boolean False"] = False):
    """
    To search for events in based on d/f parmeters either single or multiple paramter 
    If User haevn't enter every parameter consider null or something.
    """
    

    logging.info(f"Searched with query: {query}, month: {date}, price: {price}, city: {city}, top_rated: {top_rated}")

    query = query if query else ""
    city = city.capitalize() if city else ""
    price = price if price else ""
    date = date if date else ""
    top_rated = top_rated if top_rated else False

    if query and isinstance(query, str) and query.lower() == "none" and query==" ":
        query = ''


    if city and isinstance(city, str) and city.lower() == "none" and city==" ":
        city = ''


    if isinstance(query,str) and 'agp' in query.lower():
        query = ''

    if not date:
        current_date = datetime.now()
        next_months_later = current_date + relativedelta(months=12)
        date = f"{current_date.strftime('%Y-%m-%d')} to {next_months_later.strftime('%Y-%m-%d')}"

    full_res = search_event(query=query, date=date, price=price,top_rated=top_rated)
    logging.info(f"Search results: {len(full_res)}")
    full_res.sort(key=lambda x: x['tickets_sold'], reverse=True)
    if city and isinstance(city, str):
        full_res = [event for event in full_res if city in event.get('theater_address', '')]
        
    elif city and isinstance(city, list):
        city = city[0]
        full_res = [event for event in full_res if city in event.get('theater_address', '')]
    
    filtered_results = []
    if query and isinstance(query, str):
    
        filtered_results = list(filter(lambda x: x['score'] > similarity_threshold, full_res))
        final_results = filtered_results
        # final_ids = [event['event_id'] for event in filtered_results]
    else:

        # final_ids = [event['event_id'] for event in full_res]
        final_results = full_res
    

    return {"output": f"{final_results}"}



# System prompt for the event agent
SYSTEM_PROMPT = """
You are an intelligent Event Dealing Agent that helps users discover, explore, and manage events. 
Your role is to:

1. **Show Events**: Display available events in a user-friendly format
2. **Search Events**: Help users find events based on their interests, location, date, or category
3. **Event Details**: Provide detailed information about specific events
4. **User Events**: Show events created by or relevant to specific users
5. **Recommendations**: Suggest events based on user preferences

**Guidelines:**
- Be friendly, helpful, and enthusiastic about events
- Use emojis to make responses more engaging
- Provide concise but informative responses
- When showing multiple events, limit to reasonable numbers (5-10)
- Always try to be helpful even if the exact request can't be fulfilled
- If a user asks about booking or payment, guide them appropriately
- Use the available tools to fetch real-time data from the database

**Available Tools:**
- search_tool: Search for events.

**Execute the function even with null values"

NOTE: If user does not provide arguments, then return their empty string.

Respond naturally and conversationally while being informative and helpful.
"""

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

sale_agent = initialize_agent(
            llm=__llm,
            tools=[
                search_tool
            ],
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            agent_kwargs={
                "system_message": SYSTEM_PROMPT
            }
        )

async def sale_agent_answer(query : str):
    agent = sale_agent
    response = await agent.arun(query)
    return response

def get_answer(query):
    return asyncio.run(sale_agent_answer(query=query))

if __name__ == "__main__":
    def main():
        agent = sale_agent
        
        # Test queries
        test_queries = [
            "Show me some events from lucknow",
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            response = agent.invoke(query)
            # agent.invoke(query)
            print(f"🤖 Response: {response}")
            # ans = search_tool.invoke({"query" : "", "city" : "lucknow", "date" : " ", "price" : "", "top_rated" : False})
            print(ans)
            
    main()



   
