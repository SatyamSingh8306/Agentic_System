from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel
from typing import List , Optional, Literal, Annotated
from agents.llm import _llm
import agents.system_prompts as sp

class BossOutputFormat(BaseModel):
    approved: Annotated[
        bool,
        "Whether all required data and criteria are sufficiently met. If most key points are satisfied, set to True."
    ]
    required: Annotated[
        Optional[List[str]],
        "If 'approved' is False, list the missing or incomplete points that need to be addressed."
    ]
    ans: Annotated[
        str,
        "A clear, friendly, and polished final message to be sent to the user. This should be based on the user's original query and the draft reply from other agents."
    ]


boss_template = ChatPromptTemplate(
    [
        ("system", f"{sp.boss_system_prompt}"),
        ("human", """
                    FORCED APPROVED : {force_approve}
                    Context: {context} 
                    D/f Agent Responses : {agent_response}
                    User_Query : {query}
         
         """)
    ]
)

boss = boss_template | _llm.with_structured_output(BossOutputFormat)

if __name__ == "__main__":
    response = boss.invoke({"query": "nothing"})
    print(response)