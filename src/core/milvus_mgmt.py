# -*- coding: utf-8 -*-
"""
SmartDocs - Milvus Database Management

Collection of functions to handle requests to the Milvus vector database.

Manages:
- Collection creation and schema
- Vector search operations
- Index configuration
- Database connections

"""

import os
from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient
from src.utilities.logger_config import logger


DATA_PATH = os.getenv(
    "DATA_PATH", "./data"
)
os.makedirs(DATA_PATH, exist_ok=True)

database_file = os.path.abspath(os.path.join(DATA_PATH, "milvus_demo.db"))

if os.getenv("MILVUS_LOCAL", "True") == "True":

    if not os.path.exists(os.path.dirname(database_file)):
        os.makedirs(os.path.dirname(database_file), exist_ok=True)

    logger.debug(f"🔗 Using Milvus Lite database file: {database_file}")
    dbClient = MilvusClient(database_file)
    logger.debug(f"✅ Connected to local Milvus Lite at {database_file}")
else:
    MILVUS_HOST = os.getenv("MILVUS_HOST", "Missing Environment")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "Missing Environment")
    MILVUS_USERID = os.getenv("MILVUS_USERID", "Missing Environment")
    MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD", "Missing Environment")

    dbClient = MilvusClient(
        uri=f"https://{MILVUS_HOST}:{MILVUS_PORT}",
        user=MILVUS_USERID,
        password=MILVUS_PASSWORD,
        db_name="default",
        secure=True,
        server_pem_path=os.path.join(DATA_PATH, "milvus.crt")
    )
    logger.debug("✅ Connected to remote Milvus server")


def reconnect_client():
    """Reconnects to local Milvus Lite if socket crashed or locked."""
    global dbClient
    try:
        dbClient.close()
    except Exception:
        pass
    dbClient = MilvusClient(database_file)
    logger.info("🔁 Reconnected to local Milvus Lite")
    return dbClient

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "allMiniLML6v2_dim384_miso")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

fields = [
    FieldSchema(name="id",              dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="chunk_id",        dtype=DataType.INT64),
    FieldSchema(name="chunk",           dtype=DataType.VARCHAR, max_length=2048),
    FieldSchema(name="doc_name",        dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="embedding",       dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
    FieldSchema(name="file_type",       dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="num_attachments", dtype=DataType.INT32),
    FieldSchema(name="recipients",      dtype=DataType.VARCHAR, max_length=16384),
    FieldSchema(name="s3_file_key",     dtype=DataType.VARCHAR, max_length=2048),
    FieldSchema(name="sender",          dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="sent_at",         dtype=DataType.INT64),
    FieldSchema(name="subject",         dtype=DataType.VARCHAR, max_length=1024),
    FieldSchema(name="supplier",        dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="element_type",    dtype=DataType.VARCHAR, max_length=256)
]

schema = CollectionSchema(fields, description="Document chunks for RAG")


if COLLECTION_NAME in dbClient.list_collections():
    if os.getenv("DELETE_OLD_COLLECTION", "False") == "True":
        dbClient.drop_collection(COLLECTION_NAME)
        dbClient.create_collection(
            collection_name=COLLECTION_NAME, schema=schema, consistency_level="Session"
        )
        logger.warning(f"⚠️ Recreated collection: {COLLECTION_NAME}")
    else:
        logger.warning(f"📚 Using existing collection: {COLLECTION_NAME}")
else:
    dbClient.create_collection(
        collection_name=COLLECTION_NAME, schema=schema, consistency_level="Session"
    )
    logger.debug(f"🆕 Created collection: {COLLECTION_NAME}")


def create_index_for_collection(collection_name: str = COLLECTION_NAME):
    """Erstellt Index für die Collection."""
    index_params = dbClient.prepare_index_params()

    if os.getenv("MILVUS_LOCAL", "True") == "True":
        index_params.add_index(
            field_name="embedding",
            index_type="FLAT",
            metric_type="COSINE"
        )
    else:
        index_params.add_index(
            field_name="embedding",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200}
        )

    try:
        dbClient.create_index(collection_name=collection_name, index_params=index_params)
        logger.debug(f"✅ Created index on 'embedding' for {collection_name}.")
    except Exception as e:
        logger.warning(f"⚠️ Index creation skipped or already exists: {e}")

create_index_for_collection()