import pandas as pd
import chromadb
import uuid


from langchain_core.prompts import PromptTemplate


class WikiStorage:
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
    
class OverpassStorage:
    def __init__(self, label_set:set = {"historic"},name:str = "position"):
        self.label_set = label_set
        self.chroma_client = chromadb.PersistentClient('vectorstore')
        self.collection = self.chroma_client.get_or_create_collection(name=name)
           
    def load_storage(self):
        if not self.collection.count():
            for elem in self.label_set:
                self.collection.add(documents=elem,
                                    ids=[str(uuid.uuid4())])
    def query_storage(self, interests):
        return self.collection.query(query_texts=interests, n_results=4).get('documents', [])
class BuildingStorage:
    def __init__(self, objects:list):
        self.objects = objects
        self.chroma_client = chromadb.PersistentClient('vectorstore')
        self.delete_collection("buildings_in_sight")
        self.collection = self.chroma_client.get_or_create_collection(name="buildings_in_sight")
           
    def load_storage(self):
        if not self.collection.count():
            for obj in self.objects:
                self.collection.add(documents=obj["name"]+" : "+obj["description"],
                                    metadatas={"wiki_link":obj["wikipedia"],
                                               "name":obj["name"]},
                                    ids=[str(uuid.uuid4())])
    def query_storage(self, interests):
        results = self.collection.query(query_texts=interests, n_results=3)
        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])
    

        return      [{"document": doc, "metadata": meta} for doc, meta in zip(documents[0], metadatas[0])]

    
    def delete_collection(self, name: str):
        """Deletes the collection to reuse the name."""
        try:
            # Attempt to delete the collection if it exists
            self.chroma_client.delete_collection(name)
            print(f"Collection '{name}' deleted successfully.")
        except Exception as e:
            # Handle case where collection might not exist or another error
            print(f"Error deleting collection '{name}': {e}")
    
