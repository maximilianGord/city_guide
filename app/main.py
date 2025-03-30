import streamlit as st
from chains import Chain
from database_controller import WikiStorage,OverpassStorage,BuildingStorage
from utils import get_wiki_data,get_overpass_labels, get_overpass_building,get_wiki_summary,get_city_coordinates
import streamlit as st
from streamlit_folium import st_folium
import folium
import time





def create_streamlit_app(llm):
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
    
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom)
    st.text_area(label = "Your guide",value = st.session_state.recommendation, disabled=True,height=300)
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
  
    label_set={}
    #update location
    if place_button:
        city_coord = get_city_coordinates(place_input)
        st.session_state.clicked_location = city_coord
        st.session_state.map_center = city_coord
        time.sleep(0.1)
        st.rerun()

    if submit_button:
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
        # Select most interesting buildings
        label_storage = BuildingStorage(objects=st.session_state.buildings)
        label_storage.load_storage()
        results = label_storage.query_storage(user_input)
        #refine the description
        names=[]
        for result in results:
            try :
                result["document"]+=get_wiki_data(result["metadata"]["wiki_link"])
            except:
                pass
            names.append(result["metadata"]["name"])
        recommendation = llm.write_recommendation(names=names,description= [result["document"] for result in results],interests=user_input,search_item=place_input,language=language_field)
        st.session_state.recommendation = recommendation
        time.sleep(0.1)
        st.rerun()
    #     




if __name__ == "__main__":
    chain = Chain()
    st.set_page_config(layout="wide", page_title="City Guide", page_icon="🏙️")
    create_streamlit_app(chain)