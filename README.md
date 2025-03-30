This repository contains an GenAI project that can recommend a user a sight in a city, given the location and personal preference

1) The next goal is to make the the conversation with a Chatbot more interactive. Right now the user gives fiels inputs, the programm searches for necessary information on Wikipedia and creates an answer. Aiming for a more chatbot like experience by using langgraph.
2) Search on more websites.
3) Give also a route through the city



How to run this project

1) Clone this project and navigate into the city_guide folder
2) Go to groq.com and get an API Key. 
3) create a file called .env in the App folder and write GROQ_API_KEY="your api key here"
4) pip install poetry
5) poetry lock if you add something to pyproject.toml
5) poetry sync --no-root
6) Install streamlit with : pip install streamlit_chat 
7) Run this project by running poetry run streamlit run app/main.py
