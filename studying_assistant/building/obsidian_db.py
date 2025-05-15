import os
import re
from langchain.document_loaders import DirectoryLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS 
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from omegaconf import DictConfig

def create_vector_db(cfg: DictConfig):
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")

    loader = DirectoryLoader(r"C:\Users\Youssef Atef\Desktop\ISLP", glob="**/*.md")
    documents = loader.load()

    def clean_page_content(doc: Document) -> Document:
        cleaned_text = re.sub(r"!\[\[.*?\]\]", "", doc.page_content)
        document_name = doc.metadata['source'].split("\\")[-1].split(".")[0]
        return Document(page_content=cleaned_text, metadata={'document_name':document_name})

    cleaned_documents = [clean_page_content(doc) for doc in documents]
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    split_docs = splitter.split_documents(cleaned_documents)

    embeddings = GoogleGenerativeAIEmbeddings(
        model=cfg.llm.embedding_model,
        google_api_key=google_api_key
    )

    db = FAISS.from_documents(split_docs, embeddings)
    db.save_local("obsidian_db")

if __name__ == "__main__":
    @hydra.main(config_path="conf", config_name="config")
    def main(cfg: DictConfig):
        print(OmegaConf.to_yaml(cfg))
        obsidian_db(cfg)
    
    main()