import streamlit as st
from chains import ToolWorkflow, Chain
from database_controller import WikiStorage,OverpassStorage,BuildingStorage
from utils import get_wiki_data,get_overpass_labels, get_overpass_building,get_wiki_summary,get_city_coordinates
import streamlit as st
from streamlit_folium import st_folium
import folium
import time





def create_streamlit_app(llm, chat_flow):
    #setup all fields
    st.title("📧 City introduction")
    col1, col2, col3 = st.columns(3)

    with col1:
        place_input = st.text_input("Enter a City:", value="München")
        radius_input = st.text_input("how far away in meters:", value=250)

        place_button = st.button("Update City")
    with col3:
        language_field = st.selectbox("Choose a language:",["Deutsch","English","Français","हिन्दी","Italiano","Português","Español","ไทย","中国人","Русский"])
    with col2:
        user_input = st.text_input("Tell me about your interests:", value="I like buildings with a cool modern design")
        submit_button = st.button("Submit")

    default_location = get_city_coordinates(place_input)
    default_zoom = 12
    if "map_center" not in st.session_state:
        st.session_state.map_center = default_location

    if "map_zoom" not in st.session_state:
        st.session_state.map_zoom = default_zoom

    if "recommendation" not in st.session_state:
        st.session_state.recommendation = "Ask for guidance"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom)
    
    st.text_area(label = "Your guide",value = st.session_state.recommendation, disabled=False,height=300)
    st.title("Map")

    #init session_state
    if "clicked_points" not in st.session_state:
        st.session_state.clicked_points = []
    if "buildings" not in st.session_state:
        st.session_state.buildings = []
    else:
        for bui in st.session_state.buildings:
            folium.PolyLine(locations = bui["geometry"],popup=bui['name'], tooltip=bui['name']).add_to(m)
    
    if "clicked_location" not in st.session_state:
        st.session_state.clicked_location = default_location

    if st.session_state.clicked_location:
        folium.Marker(
            st.session_state.clicked_location, popup="Selected Location", tooltip="Click again to change"
        ).add_to(m)
    
    map_data = st_folium(m, width=700, height=500)

    # Create a scrollable container for chat messages

    # Custom styles
    st.markdown("""
        <style>
        .scroll-box {
            height: 300px;
            overflow-y: auto;
            border: 1px solid #ccc;
            padding: 10px;
            border-radius: 10px;
            background-color: #f9f9f9;
            margin-bottom: 20px;
        }
        .message-user {
            text-align: right;
            color: blue;
            margin: 5px 0;
        }
        .message-bot {
            text-align: left;
            color: green;
            margin: 5px 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # Scrollable chat box
    with st.container():
        chat_html = '<div class="scroll-box">'
        for msg in st.session_state.messages:
            role_class = "message-user" if msg["role"] == "user" else "message-bot"
            chat_html += f'<div class="{role_class}"><b>{msg["role"].capitalize()}:</b> {msg["content"]}</div>'
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)

    # Input box
    chat_input = st.chat_input("What would you like to know...")

    if chat_input:
        st.session_state.messages.append({"role": "user", "content": chat_input})
        response = chat_flow.stream_graph_updates(chat_input)
        if isinstance(response,str):
            st.session_state.messages.append({"role": "assistant", "content": response})
        elif isinstance(response, dict):
            st.session_state.messages.append({"role": "assistant", "content": "Generated tour, see field above"})
            st.session_state.recommendation = generate_tour(radius_input, response["preference"], response["place"],language_field,llm)
        st.rerun()
        #Check if the user clicked and update the map with a marker

    if map_data and "last_clicked" in map_data and map_data["last_clicked"]:
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lng = map_data["last_clicked"]["lng"]
        st.session_state.clicked_location = (clicked_lat, clicked_lng)
        if "center" in map_data and map_data["center"]:
            st.session_state.map_center = [map_data["center"]["lat"], map_data["center"]["lng"]]
        if "zoom" in map_data and map_data["zoom"]:
            st.session_state.map_zoom = map_data["zoom"]
        time.sleep(0.1)
        st.rerun()
  
    #update location
    if place_button:
        city_coord = get_city_coordinates(place_input)
        st.session_state.clicked_location = city_coord
        st.session_state.map_center = city_coord
        time.sleep(0.1)
        st.rerun()

    if submit_button:
        print(user_input)
        st.session_state.recommendation = generate_tour(radius_input, user_input, place_input,language_field,llm)
        time.sleep(0.1)
        st.rerun()
    #     

def generate_tour(radius_input, user_input,place_input,language_field,llm):
    print(user_input)
    label_set={}
    obj_list = []
    radius = int(radius_input)
    while len(obj_list)<4:  
        label_set = get_overpass_labels(st.session_state.clicked_location,radius)
        

        #Collect information and links about interesting places nearby
        cleaned_user_input = user_input.replace("ä","ae").replace("ö","oe").replace("ü","ue").replace(" ","_")
        label_storage = OverpassStorage(label_set,name=cleaned_user_input)
        label_storage.load_storage()
        best_lables = label_storage.query_storage(user_input)
        obj_list = get_overpass_building(st.session_state.clicked_location,best_lables[0],area_name = user_input,radius=radius)
        radius +=250

    # Visualize 
    st.session_state.buildings = []
    for obj in obj_list:
        if "geometry" in obj.keys():
            st.session_state.buildings.append(obj)
    print("visualization ready")
    # Prepare for LLM 
    for bui in st.session_state.buildings:
        if "wikipedia" in bui.keys():
            if "description" in bui.keys():
                try : 
                    bui["description"] += get_wiki_summary(bui["wikipedia"])
                except:
                    pass
            else:
                try:
                    bui["description"] = get_wiki_summary(bui["wikipedia"])
                except:
                    bui["description"] = bui["name"]
        else:
            bui["wikipedia"]=""
            if "description" not in bui.keys():
                bui["description"] = bui["name"]
    print("ready for LLM")
    # Select most interesting buildings
    label_storage = BuildingStorage(objects=st.session_state.buildings)
    label_storage.load_storage()
    results = label_storage.query_storage(user_input)
    #At this point, the buildings are only described by their wikipedia. Description
    names=[]
    for result in results:
        try :
            result["document"]+=llm.online_search(result["metadata"]["name"],user_input)
        except:
            pass
        names.append(result["metadata"]["name"])
    recommendation = llm.write_recommendation(names=names,description= [result["document"] for result in results],interests=user_input,search_item=place_input,language=language_field)
    return recommendation

if __name__ == "__main__":
    workflow = ToolWorkflow()
    chain = Chain()
    st.set_page_config(layout="wide", page_title="City Guide", page_icon="🏙️")
    create_streamlit_app(chain, workflow)