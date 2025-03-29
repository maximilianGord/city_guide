from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException




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
    
    
    
    def write_recommendation(self, names,description, interests, search_item, language):
        prompt_email = PromptTemplate.from_template(
            """
            ### Tourist Spot Place names:
            {names}
            ### Tourist Spot Place names:
            {description}

            ### INSTRUCTION:
            You are  a friendly city guide for the city {search_item}. Choose a common local name for youself .You guide people that speak the language {language}. Talk to them in {language}. Please recommend the given tourist spots to an user. It has to be clear to the Tourists which are the three mentioned spots and why they are interesting.
            Remember to keep the Tourists interests {interests} in mind.
            Also try to tell them about this spots in an interesting way, like a City Guide. 
            Do not provide a preamble.
            ### Recommendation (NO PREAMBLE):

            """
        )
        chain_email = prompt_email | self.llm
        res = chain_email.invoke({"interests": str(interests), "names": str(names),"description":description, "search_item":search_item,"language":language})
        return res.content
    
    
    