from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

# Standard library imports
import getpass
import os
import sys
from typing import Annotated, Literal
from uuid import uuid4

# Third-party imports
from IPython.display import Image, display
from pydantic import BaseModel, Field
from typing import Literal
from typing_extensions import TypedDict
from tavily import TavilyClient

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import (
    Graph,
    MessagesState,
    StateGraph,
    START,
    END
)
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# Local imports
app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(app_path)






from dotenv import load_dotenv
load_dotenv()

class Chain:
    def __init__(self):
        self.model = "llama-3.1-8b-instant"
        self.llm = ChatGroq(
            model=self.model,
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        # Set up Tavily Search
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.search_client = TavilyClient(api_key=self.tavily_api_key)

    def online_search(self, object, user_preferences):
        # Use Tavily to search the web
        search_results = self.search_client.search(query="Can you tell me information about {}, considering an interest in {}".format(object,user_preferences), max_results=3)

        # Format the web results for LLM input
        sources = "\n".join(f"{i+1}. {r['title']}: {r['url']}" for i, r in enumerate(search_results["results"]))
        context = "\n\nSearch Results:\n" + sources
        return context


    
    
    def write_recommendation(self, names,description, interests, search_item, language):

        # Use Tavily to search the web
        search_results = self.search_client.search(query="Provide information about {} connected to {}".format(search_item,interests), max_results=3)

        # Format the web results for LLM input
        sources = "\n".join(f"{i+1}. {r['title']}: {r['url']}" for i, r in enumerate(search_results["results"]))
        general_context = "\n" + sources


        prompt_email = PromptTemplate.from_template(
            """
            ### General city context:
            {general_context}

            ### Tourist Spot Place names:
            {names}

            ### Tourist Spot Place names:
            {description}

            ### INSTRUCTION:
            You are  a friendly city guide for the city {search_item}. Choose a common local name for youself .You guide people that speak the language {language}. Talk to them in {language}. Please recommend the given tourist spots to an user. It has to be clear to the Tourists which are the three mentioned spots and why they are interesting.
            Remember to keep the Tourists interests {interests} in mind.
            Also try to tell them about this spots in an interesting way, like a City Guide. 
            Start with an introduction about the city. Mention general information, that could be interesting for the tourist or import when mentioning spots later.
            Then give information about every individual spot. Try to connect every Spot to th cities history or to each other.

            Do not provide a preamble.Do not visit spots twice !
            ### Recommendation (NO PREAMBLE):

            """
        )
        chain_email = prompt_email | self.llm
        res = chain_email.invoke({"interests": str(interests), "names": str(names),"description":description, "search_item":search_item,"language":language,"general_context":general_context})
        return res.content
    
class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

########## Edges


def choose_tools(state) -> Literal["ROUTEPLANNING", "CHAT", "SEARCH"]:
    """
    Determines which tools are necessary for the request.
    Now properly handles tool calls and adds SEARCH option.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # 1. First check for tool-related messages
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls'):
        print("---CHECK Tools--- Found tool calls")
        return "SEARCH"
    
    # if isinstance(last_message, ToolMessage):
    #     print("---CHECK Tools--- Processing tool results")
    #     return "CHAT"  # After tools, continue to chatbot
    
    # 2. Only do LLM classification for human messages and tool calls
    #if isinstance(last_message, HumanMessage):
    class Choice(BaseModel):
        """Tool selection decision."""
        cat_score: Literal["ROUTEPLANNING", "CHAT"] = Field(
            description="Either 'ROUTEPLANNING' or 'CHAT'"
        )

    model = llm.with_structured_output(Choice)
    
    prompt = PromptTemplate(
        template="""Analyze the user request:
        {context}
        
        Return 'ROUTEPLANNING' only if:
        - User asks for navigation help
        - Requests a guided tour
        - Asks for directions
        - Needs a you to be a city guide !
        - Needs information about places
        Key words to look out for : Guide, tour, itinerary
        
        Return 'CHAT' only if 'ROUTEPLANNING' is not selected And the User wants:
        - General information questions
        - Historical facts
        - Descriptions of places
        Key words to look out for : Tell, Explain 

        You evaluate by first checking 'ROUTEPLANNING' and only if it is False check 'CHAT'. This order is important !
        Before you submit 'ROUTEPLANNING' make sure that it should only be submitted if the User needs location based data  !

        EXAMPLES
        Question : Can you tell me how old the townhall is ? Answer : 'CHAT
        Question : What will be the weather tomorrow ? Answer : 'CHAT
        Question : I want you to give me a tour through the historic city center ! Answer : 'ROUTEPLANNING'
        Question : I need someone to guide me through the district ! Answer : 'ROUTEPLANNING'
        Question : Can you navigate me through the center. I want to know about the sport ! Answer : 'ROUTEPLANNING'

        """,
        input_variables=["context"]
    )
    
    chain = prompt | model
    result = chain.invoke({"context": last_message.content})
    decision = result.cat_score
    print(f"---CHECK Tools--- Decision: {decision}")
    return decision
    
    # 3. Default fallback
    print("---CHECK Tools--- Defaulting to CHAT")
    return "CHAT"



####Nodes
def filter(state):
    """
    Filter information from the query

    Args:
        state (messages): The current state

    Returns:
        dict: The updated state with re-phrased question
    """

    print("---Filter QUERY---")
    messages = state["messages"]
    question = messages[0].content

    class Attributes(BaseModel):
        """Dict with relevant fields."""

        place: str = Field(description="Name of a city")
        preference: str = Field(description="description of the interests of the human")

    prompt = PromptTemplate(
        template=""" You need to filter out information from the User query ! Return the place and preference from the query.
        A place is the name of a location, it can me a city name. A preference is what the User is searching for
        Here is the User query : \n\n {context} \n\n

        Examples : Query :"I want a city tour through Munich, I am interested in history." place : 'Munich', preferences : 'historic buildings'\n
        Query: "I am in Munich and want you to guide me through the most important places." place : 'Berlin',preferences : 'most important places' """,
        input_variables=["context"]
    )
    model = llm.with_structured_output(Attributes)

    chain = prompt | model

    messages = state["messages"]
    last_message = messages[-1].content

    attributes = chain.invoke({"context": last_message})
    print("returns places{} and preference{}".format(attributes.place,attributes.preference))
    return {
        "messages": [
            AIMessage(
                content=f"Create tour for {attributes.place} with respect to {attributes.preference}",
                # Include metadata if needed:
                metadata={
                    "place": attributes.place,
                    "preference": attributes.preference
                }
            )
        ]
    }

# def chatbot(state: State):
#     return {"messages": [llm.invoke(state["messages"])]}

tavily_tool = TavilySearchResults(max_results=2)

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

def webbot(state: State):
    llm_with_tools = llm.bind_tools([tavily_tool])
    messages = state["messages"]
    last_message = messages[-1]
    
    # Handle new human input
    if isinstance(last_message, HumanMessage):
        print("Processes human input : {}".format(last_message))
        response = llm_with_tools.invoke(messages)
        
        # If LLM wants to use tools
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Create proper tool invocation messages
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_messages.append({
                    "role": "tool",
                    "name": tool_call['name'],
                    "content": str(tool_call['args']),
                    "tool_call_id": tool_call['id']
                })
                print("Call tool {}".format(tool_call['name']))
            return {"messages": [response] + tool_messages}  # Pass both
        
        # If regular response
        return {"messages": [response]}
    
    # Handle tool responses (already formatted)
    if any(isinstance(m, ToolMessage) for m in messages):
        original_query = next(m for m in messages if isinstance(m, HumanMessage))
        tool_result = next(m for m in messages if isinstance(m, ToolMessage))
        final_response = llm.invoke([
            original_query,
            tool_result,
            "Generate a concise answer for the user based on the tool results"
        ])
        return {"messages": [final_response]}
    
    # Handle other cases
    return {"messages": [llm_with_tools.invoke(messages)]}

retrieve = ToolNode([tavily_tool])

class ToolWorkflow:
    def __init__(self):
        # init LLM
        self.model = "llama-3.1-8b-instant"
        self.llm = ChatGroq(
            model=self.model,
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        #init StateGraph
        self.workflow = StateGraph(State)
        self.workflow.add_node("chatbot",webbot)
        self.workflow.add_node("respond",webbot)
        self.workflow.add_node("retrieve", retrieve)
        self.workflow.add_node("filter",filter)
        self.workflow.add_edge(START, "chatbot")

        self.workflow.add_conditional_edges(
            "chatbot",
            # Assess agent decision
            choose_tools,
            {
                # Translate the condition outputs to nodes in our graph
                "ROUTEPLANNING": "filter",
                "CHAT":"respond",
                "SEARCH": "retrieve"  # New path for tools

            },
        )

        # workflow.add_edge("retrieve", END)
        self.workflow.add_edge("filter", END)
        self.workflow.add_edge("retrieve", "respond")
        self.workflow.add_edge("respond", END)
        self.memory = MemorySaver()
        self.graph = self.workflow.compile(
            checkpointer=self.memory
        )
    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": f"thread_{uuid4()}"}}
        return_msg = ""
        for event in self.graph.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config
        ):
            for node, value in event.items():
                if "messages" in value:
                    if len(value["messages"])>0:
                        last_msg = value["messages"][-1]
                        if isinstance(last_msg, AIMessage) and last_msg.content:
                            return_msg = str(last_msg.content)
                            print(return_msg)
                        if isinstance(last_msg, AIMessage) and hasattr(last_msg,'metadata'):
                            return last_msg.metadata
                        elif hasattr(last_msg, 'tool_calls'):
                            print("Assistant is searching")
                        elif isinstance(last_msg, ToolMessage):
                            continue  # Don't show tool messages directly
        return return_msg
    










print("Enter loop")
# while True:
#     try:
#         print("Show user input")
#         user_input = input("User: ")
#         if user_input.lower() in ["quit", "exit", "q"]:
#             print("Goodbye!")
#             break
#         stream_graph_updates(user_input)
#     except:
#         # fallback if input() is not available
#         user_input = "What do you know about LangGraph?"
#         print("User: " + user_input)
#         stream_graph_updates(user_input)
#         break
    