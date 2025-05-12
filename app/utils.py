import requests
import wikipedia
from bs4 import BeautifulSoup
import chromadb
import uuid





import chromadb
import uuid
import urllib.parse


def get_wiki_summary(search):
    # set language to English (default is auto-detect)
    lang = "en"

    """
    fetching summary from wikipedia
    """
    # Extract language and article title
    lang, page = search.split(":", 1)
    # set language to English (default is auto-detect)
    summary = wikipedia.summary(page, sentences = 3)

    return summary

def get_wiki_data(title):
    if title == None or title == "":
        return ""
    # set language to English (default is auto-detect)
    lang = "en"

    """
    fetching summary from wikipedia
    """
    # set language to English (default is auto-detect)
    #summary = wikipedia.summary(search, sentences = 5)

    """
    scrape wikipedia page of the requested query
    """

    # create URL based on user input and language


    # Extract language and article title
    lang, page = title.split(":", 1)

    # URL encode the page title
    encoded_page = urllib.parse.quote(page)

    # Construct the Wikipedia URL
    wiki_url = f"https://{lang}.wikipedia.org/wiki/{encoded_page}"


    # send GET request to URL and parse HTML content
    response = requests.get(wiki_url)
    soup = BeautifulSoup(response.content, "html.parser")

    # extract main content of page
    content_div = soup.find(id="mw-content-text")

    # Find all headers (h2, h3, etc.)
    headers = content_div.find_all(['h3'])

    chroma_client = chromadb.PersistentClient('vectorstore')
    collection = chroma_client.get_or_create_collection(name=encoded_page.replace("ä","ae").replace("ö","oe").replace("ü","ue"))
    for header in headers:
            collection.add(documents=header.get_text(strip=True),
                                ids=[str(uuid.uuid4())])
    selected_headers_names = collection.query(query_texts="Which information could be interesting for a tourist, who is interested in  {}".format("history"), n_results=2).get('documents', [])
    selected_text = ""
    for header in headers:
        headline_text = header.get_text(strip=True)
        print(headline_text)
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

def fill_wikipedia(objects):
    for object in objects:
        if "wikipedia" in object.keys():
            object["wikipedia"] = get_wiki_data(object["wikipedia"])


def get_overpass_labels(coord,radius):
    query = """[out:json];nwr(around:{}, {}, {});out body;""".format(radius,coord[0],coord[1])
    response = requests.get("http://overpass-api.de/api/interpreter", params={"data": query})
    data = response.json()

    tags = set()

    # Extract all unique tags
    for element in data["elements"]:
        if "tags" in element:
            for key in element["tags"].keys():
                if key.split(":")[0] in ["historic","heritage","amenity","building","building","tourism","leisure","artwork_type"]:
                    tags.update([key])
    return tags

def get_overpass_building(coord,tags,area_name,radius):            
    url = "http://overpass-api.de/api/interpreter?data="

    # Define Overpass QL query (find all historic buildings in Munich)
    relation_str=""
    for tag in tags:
        relation_str+='relation["{}"](around:{},{},{});'.format(tag,radius,coord[0],coord[1])
    query = """
    [out:json];
    area["name"="{}"]->.searchArea;(
    {}
    );
    out body;
    >;
    out skel qt;
    """.format(area_name,relation_str)

    # Send request
    response = requests.get(url, params={"data": query})

    obj_list = []
    # Parse response
    if response.status_code == 200:
        data = response.json()
        #print(data)
        for object in data["elements"]:
            if object["type"]=="relation" and "name" in object['tags']:
                object_dict = {}
                object_dict["name"] = object['tags']["name"]
                if "website" in object["tags"]:
                    object_dict["website"] = object["tags"]["website"]
                if "wikipedia" in object["tags"]:
                    object_dict["wikipedia"] = object["tags"]["wikipedia"]
                if "description" in object["tags"]:
                    object_dict["description"] = object["tags"]["description"]
                
                temp_query ="""[out:json];
                    relation({});  
                    out geom;""".format(object["id"])
                temp_resp = requests.get(url, params={"data": temp_query})
                temp_data = temp_resp.json()
                if "geometry" in temp_data["elements"][0]["members"][0].keys():
                    coords = []
                    for coord in temp_data["elements"][0]["members"][0]["geometry"]:
                        coords.append([coord["lat"],coord["lon"]])
                    object_dict["geometry"] = coords
                obj_list.append(object_dict)
    else:
        print(f"Error: {response.status_code}")
    return obj_list

def get_city_coordinates(city:str = "München"):

    url = "http://overpass-api.de/api/interpreter?data="
    query = """
    [out:json];
    area["name"="{}"]->.searchArea;
    node(area.searchArea)["place"="city"];
    out center;
    """.format(city)
    print("The city is "+city)
    response = requests.get(url, params={"data": query})
    data = response.json()
    print(data)
    return [data["elements"][0]["lat"],data["elements"][0]["lon"]]

