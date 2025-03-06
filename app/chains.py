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
    def extract_jobs(self, web_text_cleaned, search_item):
        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPED TEXT FROM WEBSITE:
            {page_data}
            ### INSTRUCTION:
            The scraped text is from wikipedia site of {search}.
            Your job is to extract the places, buildings or cites which a tourist would find interesting. Return them in JSON format containing the 
            following keys: `name`, `type`, `description`, 'history'. The key "type" is a categorical key. The corresponding categories are : history, art, culture, architecture, general.
            Only return the valid JSON.
            ### VALID JSON (NO PREAMBLE):    
        """
        )
        chain_extract = prompt_extract | self.llm 
        try :
            res = chain_extract.invoke(input={'page_data':web_text_cleaned, 'search':search_item})
        except Exception as e:
            raise Exception("'Request too large for {}. The limit is {}.{} were found ".format(self.model, str(6000),len(web_text_cleaned)))
        #12847
        try:
            json_parser = JsonOutputParser()
            json_res = json_parser.parse(res.content)
        except OutputParserException:
            raise OutputParserException("Context too big. Unable to parse jobs.")
        return json_res if isinstance(json_res, list) else [json_res]
    
    def write_recommendation(self, places, interests, search_item):
        prompt_email = PromptTemplate.from_template(
            """
            ### Tourist Spot DESCRIPTION:
            {places}

            ### INSTRUCTION:
            You are Thomas, a city guide for the city {search_item}. Please recommend the given tourist spots to an user. It has to be clear to the Tourists which are the three mentioned spots and why they are interesting.
            Remember to keep the Tourists interests {interests} in mind.
            Also try to tell them about this spots in an interesting way, like a City Guide. 
            Do not provide a preamble.
            ### Recommendation (NO PREAMBLE):

            """
        )
        chain_email = prompt_email | self.llm
        res = chain_email.invoke({"interests": interests, "places": places, "search_item":search_item})
        return res.content
    
    
    