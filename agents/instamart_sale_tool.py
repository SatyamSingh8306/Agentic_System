from motor.motor_asyncio import AsyncIOMotorClient
import logging
import asyncio
import json
from typing import List, Dict, Any, Optional, Annotated, Type
from langchain_ollama import OllamaEmbeddings
import re
from dateutil.relativedelta import relativedelta
from redis import Redis
from langchain.agents import initialize_agent, AgentType
from pydantic import BaseModel
from langchain_core.tools import BaseTool
from langchain.tools import tool
from langchain_openai.embeddings import OpenAIEmbeddings
import re
from pymongo import DESCENDING
import logging
import agents.system_prompts as sp
from dotenv import load_dotenv, find_dotenv
import logging
logging.basicConfig(level=logging.INFO)
# Load environment variables
load_dotenv(find_dotenv())
from os import getenv


embedding_model = OllamaEmbeddings(model="bge-m3", base_url = getenv("OLLAMA_BASE_URL"))
# embedding_model = OpenAIEmbeddings()
similarity_threshold = 0.7

client = AsyncIOMotorClient(getenv('DB'))
db = client['event_db']
instamart_collection = db['instamart_collection']

class SaleSearchInput(BaseModel):
    query: Annotated[Optional[str], 'The query of the user if no query then return " " '] = None
    max_price: Annotated[Optional[int], 'The maximum price set by the user'] = None



async def get_products(sale_inputs: SaleSearchInput):
    pipeline = []

    # Coerce dicts to Pydantic model if necessary
    if isinstance(sale_inputs, dict):
        sale_inputs = SaleSearchInput(**sale_inputs)

    max_price = sale_inputs.max_price
    query = sale_inputs.query

    logging.info(f"Received input → query: {query}, max_price: {max_price}")

    # If query exists, perform vector search
    if query:

        query_embedding = await embedding_model.aembed_query(query)

        pipeline.extend([
            {
                "$vectorSearch": {
                    "queryVector": query_embedding,
                    "path": "embedding",
                    "numCandidates": 1000,
                    "limit": 10,
                    "index": "instamart_index"
                }
            }
        ])

        if max_price is not None:
            pipeline.append({
                "$match": {
                    "price": {"$lte": max_price}
                }
            })

        pipeline.extend([
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "description": 1,
                    "price": 1,
                    "weight": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$sort": {"score": -1}
            },
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "description": 1,
                    "price": 1,
                    "weight": 1,
                    "score": 1
                }
            }
        ])
    else:        
        if max_price is not None:
            pipeline.append({
                "$match": {
                    "price": {"$lte": max_price}
                }
            })
         

        pipeline.append({
            "$project": {
                "_id": 1,
                "name": 1,
                "description": 1,
                "price": 1,
                "weight": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        })

    

    # Execute the aggregation pipeline
    try:
        cursor = instamart_collection.aggregate(pipeline)
        results = []
        async for doc in cursor:
            if doc.get("score", float("inf")) > similarity_threshold:
                results.append(doc)

        if not results:
            logging.warning("Aggregation returned no results")
    

        output = "\n".join(
            f"- {item['name']} ({item['weight']}) - ₹{item['price']}" for item in results
        )

        return {
            "output": output
        }

    except Exception as e:
        logging.error(f"Error during aggregation: {e}")
        return {
            "output": "An error occurred while fetching products."
        }
        

class InstamartSearchTool(BaseTool):
    name: str = "instamart_product_search"
    description: str = (
        "Use this tool whenever the user is looking for grocery products — "
        "whether they ask for vegetables, fruits or ingredients, mention a specific item"
        "It finds relevant products based on query and maximum price"
    )
    args_schema: Type[BaseModel] = SaleSearchInput
    return_direct: bool = True

    async def _arun(self, query: str, price: int) -> str:
        results = await get_products(query, price)
        if not results:
            return "No matching products found."
        
        res = results[:11]
        output = "\n".join(
            f"- {item['name']} ({item['weight']}) - ₹{item['price']}" for item in res
        )
        return output

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Use async version `_arun` for this tool.")

sales_tool = InstamartSearchTool()



if __name__ == "__main__":
    async def main():
        products = await get_products({"query":"cucumber"})
        print(products)

    asyncio.run(main())