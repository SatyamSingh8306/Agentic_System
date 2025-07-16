from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel
from typing import List , Optional, Literal, Annotated
from agents.llm import ___llm
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
        MessagesPlaceholder(variable_name="prev"),
        ("human", """
                    FORCED APPROVED : {force_approve}
                    Context: {context} 
                    D/f Agent Responses : {agent_response}
                    User_Query : {query}
         
         """)
    ]
)

boss = boss_template | ___llm.with_structured_output(BossOutputFormat)

if __name__ == "__main__":
    response = boss.invoke({
    "force_approve": "False",
    "context": """[
        {
            "subtasks": [
                {
                    "agent_name": "search_tool_agent",
                    "query": ["Kabab Paratha Kabadhiya Dukan location"]
                },
                {
                    "agent_name": "customer_care_agent",
                    "query": ["Provide contact details for Kabab Paratha Kabadhiya Dukan"]
                }
            ],
            "understading": [
                {
                    "criteria": [],
                    "keywords": ["Kabab Paratha Kabadhiya Dukan", "Metrocity Gate No 2"]
                }
            ]
        }
    ]""",
    "agent_response": "Result By Different Agents\n"
                      "- Search Tool Agent: [{'input': 'Kabab Paratha Kabadhiya Dukan location', 'output': 'The location of Kabab Paratha Kabadhiya Dukan is Rajapul Mainpura Opposite gate no 32, near RGS green apartment in Patna.'}]\n"
                      "- Customer Care Agent: [AIMessage(content=\"Dear valued customer,\\n\\nThank you for your interest in our services. While I'm MochanD, a dedicated event organizer, I don't have direct access to specific business listings or databases. However, I can certainly assist you in finding the contact details for Kabab Paratha Kabadhiya Dukan. \\n\\nTo help you, could you please provide me with the location or city where this establishment is based? Once I have that information, I'll be able to guide you through various resources to find their contact details. \\n\\nIn the meantime, here are some general steps you can take:\\n\\n1. **Online Search**: Use a search engine like Google and enter the name of the restaurant along with the location. This usually provides direct contact information on the first results page.\\n2. **Business Directories**: Websites such as Yellow Pages or Justdial often have extensive business listings where you can find contact details.\\n3. **Social Media**: Check their official pages on platforms like Facebook, Instagram, or Twitter if they have one. Businesses often list their contact information there.\\n4.",
    "query" : "Hello"

})
    print(response)