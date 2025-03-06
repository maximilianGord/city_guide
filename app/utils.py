import requests
import wikipedia
from bs4 import BeautifulSoup
import chromadb
import uuid





def get_wiki(search_item, interest):
        # set language to English (default is auto-detect)
        lang = "en"

        """
        fetching summary from wikipedia
        """
        # set language to English (default is auto-detect)
        #summary = wikipedia.summary(search_item, sentences = 5)

        """
        scrape wikipedia page of the requested query
        """

        # create URL based on user input and language
        url = f"https://{lang}.wikipedia.org/wiki/{search_item}"

        # send GET request to URL and parse HTML content
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # extract main content of page
        content_div = soup.find(id="mw-content-text")

         # Find all headers (h2, h3, etc.)
        headers = content_div.find_all(['h3'])

        chroma_client = chromadb.PersistentClient('vectorstore')
        collection = chroma_client.get_or_create_collection(name=search_item)
        for header in headers:
            collection.add(documents=header.get_text(strip=True),
                                ids=[str(uuid.uuid4())])
        selected_headers_names = collection.query(query_texts="Spots that could be interesting for a tourist. The tourist claims to have following interest : {}".format(interest), n_results=5).get('documents', [])
        selected_text = ""
        for header in headers:
            headline_text = header.get_text(strip=True)
            if headline_text in selected_headers_names[0]:
                section_text = [headline_text+" : "]
                sibling_count = 0
                for sibling in header.find_parent().find_next_siblings():
                    if (sibling.name and sibling.name.startswith('h')) or sibling_count>1:
                        break  # Stop if another header is found
                if sibling.name == 'p':
                    section_text.append(sibling.get_text())
                    if sibling.get_text() != "":
                        sibling_count+=1
                selected_text = selected_text.join(section_text)

        return selected_text

