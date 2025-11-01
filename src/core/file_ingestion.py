# -*- coding: utf-8 -*-
"""
SmartDocs - File Ingestion

Ingest files or emails into vector database.

Handles:
- Document loading
- Text splitting and chunking
- Metadata extraction

"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_unstructured.document_loaders import UnstructuredLoader


# Function to load and split the data from the PDF file
def load_and_split_data(file_path):
    # Load the PDF file and split the data into chunks
    loader = UnstructuredLoader(file_path=file_path)
    data = loader.load()
    # chunk_size=600, overlap=100
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=7500, 
                                                   chunk_overlap=100)
    chunks = text_splitter.split_documents(data)

    return chunks
