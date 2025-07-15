from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel
from typing import List , Optional, Literal, Annotated
from agents.llm import __llm
import agents.system_prompts as sp

class  BossOutputFormat(BaseModel):
    approved : Annotated[bool, "Weather all the data required in criterion is collected or not."]
    required : Annotated[Optional[List[str]], "Why is not approved"]

boss_template = ChatPromptTemplate(
    [
        ("system", f"{sp.supervisor_prompt}"),
        ("human", """
                    Context: {context} 
                    D/f Agent Responses : {agent_response}
                    User_Query : {query}
         """)
    ]
)

boss = boss_template | __llm.with_structured_output(BossOutputFormat)

if __name__ == "__main__":
    response = boss.invoke({"query": "nothing"})
    print(response)