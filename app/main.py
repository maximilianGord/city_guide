import streamlit as st
from langchain_community.document_loaders import WebBaseLoader

from chains import Chain
from database_controller import Storage
from utils import get_wiki

def create_streamlit_app(llm):
    st.title("📧 City introduction")
    place_input = st.text_input("Enter a City:", value="Garching")
    user_input = st.text_input("Tell me about your interests:", value="I like building with a cool modern design")
    submit_button = st.button("Submit")

    if submit_button:
        try:
            # get all the interesting places in place_input and store them in chroma
            full_text = get_wiki(place_input, user_input)
            data = llm.extract_jobs(full_text,place_input)
            storage = Storage(data, search_item=place_input)
            storage.load_storage()
            #
            top_places = storage.query_storage(user_input)
            rec = llm.write_recommendation(top_places,user_input,place_input)
            st.code(rec, language='markdown')

        except Exception as e:
            st.error(f"An Error Occurred: {e}")


if __name__ == "__main__":
    chain = Chain()
    st.set_page_config(layout="wide", page_title="Cold Email Generator", page_icon="📧")
    create_streamlit_app(chain)