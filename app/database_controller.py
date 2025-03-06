import pandas as pd
import chromadb
import uuid


from langchain_core.prompts import PromptTemplate


class Storage:
    def __init__(self, data, search_item="Garching"):
        self.actual_search_item = search_item
        self.data = data
        self.chroma_client = chromadb.PersistentClient('vectorstore')
        self.collection = self.chroma_client.get_or_create_collection(name=search_item)
           
    def load_storage(self):
        if not self.collection.count():
            for row in self.data:
                self.collection.add(documents=row["description"]+row["history"],
                                    metadatas={"type": row["type"]},
                                    ids=[str(uuid.uuid4())])
    def query_storage(self, interests):
        return self.collection.query(query_texts=interests, n_results=3).get('documents', [])