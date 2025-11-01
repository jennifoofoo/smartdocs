# %% [markdown]
# ## Iterate through local files
#
# %% [markdown]
# ### Prepare all files and ingest them into Milvus
#
# The core functions originate from the "FileIngestion" notebook.
# Support for certain formats may still require further improvements.
#
# **PITFALLS**:
#
# 1. Some formats are only partially supported and might produce limited text.

import os
from typing import List

os.environ["MILVUS_EMBEDDED_MODE"] = "true"

# %%
from src.core.milvus_mgmt import COLLECTION_NAME, DATA_PATH, dbClient, schema, create_index_for_collection
from src.datatypes.emails_types import EmlEmailMessage, MsgEmailMessage
from src.utilities.chunk_embed import deal_with_document, deal_with_email
from src.utilities.logger_config import logger


def insert_data(data: List[dict], max_message_size: int = 512) -> int:
    insert_count = 0
    start = 0
    while start < len(data):
        end = min(len(data), start + max_message_size)
        try:
            res = dbClient.insert(collection_name=COLLECTION_NAME, data=data[start:end])
            insert_count += res["insert_count"]
        except Exception as e:
            logger.error(f"Insert batch failed ({start}-{end}): {e}")
        start += max_message_size

    logger.debug(f"Inserted {insert_count} rows into memory buffer (flush required for persistence)")
    return insert_count


def clear_collection():
    if COLLECTION_NAME in dbClient.list_collections():
        logger.info(f"🗑️ Dropping collection '{COLLECTION_NAME}'...")
        dbClient.drop_collection(collection_name=COLLECTION_NAME)

    # Recreate collection using the imported schema
    dbClient.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        consistency_level="Session"
    )

    create_index_for_collection(COLLECTION_NAME)

    logger.info(f"✅ Collection '{COLLECTION_NAME}' recreated and empty.")

# %%
def process_file(suppliers: List[str]):
    try:
        dbClient.load_collection(collection_name=COLLECTION_NAME)
        logger.info(f"✅ Collection '{COLLECTION_NAME}' loaded into memory.")
    except Exception as e:
        logger.warning(f"⚠️ Could not load collection (may already be loaded): {e}")

    count = 0
    for root, dirs, files in os.walk(DATA_PATH):
        print(root)
        for file in files:
            print(file)
            # Skip DBs, macOS meta files, and Office lock files (~$...)
            if (
                file in ['milvus_demo.db', '.DS_Store', '.milvus_demo.db.lock']
                or file.startswith("~$")
            ):
                print("skip temp/lock file:", file)
                continue

            file_path = os.path.join(root, file)
            file_key = file_path[len(DATA_PATH)+1:]
            supplier = file_key.split('/')[0]
            if suppliers and supplier.lower() not in suppliers:
                continue

            _, ext = os.path.splitext(file)
            ext = ext.lower()

            result = []
            try:
                # --- Emails ---
                if ext in ['.eml', '.msg']:
                    with open(file_path, 'rb') as f:
                        if ext == ".eml":
                            email = EmlEmailMessage(f.read())
                        elif ext == ".msg":
                            email = MsgEmailMessage(f.read())

                    logger.debug(f"Processing {file_key}")
                    result = deal_with_email(email, file_key)

                # --- Documents ---
                elif ext in ['.xlsx', '.docx', '.pptx', '.pdf']:
                    with open(file_path, 'rb') as f:
                        logger.info(f"Processing {file_key}")
                        result = deal_with_document(f, file_key)

                else:
                    logger.warning(f"Unsupported file type: {file}")
                    continue

                if not result or len(result) == 0:
                    logger.warning(f"No chunks generated for {file_key}")
                    continue

                logger.info(f"{file_key} → {len(result)} chunks generated")
                if len(result) > 0:
                    print("\n=== 🔍 Schema preview for", file_key, "===")
                    first = result[0]
                    for key, value in first.items():
                        print(f"  {key:<15} | Type: {type(value).__name__:<10} | Example: {str(value)[:80]}")
                    print("  ...")
                    print(f"Total chunks: {len(result)}")
                    print("===============================\n")
                else:
                    print(f"⚠️ No chunks generated for {file_key}")

                try:
                    logger.debug(f"{count:04d}: {file_key} at {os.path.dirname(file_key)}")
                    insert_count = insert_data(result)
                    count += insert_count
                except Exception as insert_err:
                    logger.error(f"Failed to insert {file_key}: {insert_err}")
                    continue

            except Exception as e:
                logger.error(f"Skipping {file_key} due to error: {e}")
                continue

    try:
        dbClient.release_collection(COLLECTION_NAME)
        logger.info(f"💾 Released collection - {count} entities persisted to disk.")
    except Exception as e:
        logger.error(f"❌ Release failed: {e}")

    logger.debug(f"{count} entities inserted in total")


if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser(description='')
    arg_parser.add_argument(
        '--suppliers', '-s',
        help='Comma-separated list of suppliers to process (first level in data directory).',
        default='carsten.ikemeyer,wolfgang.schneider6,roland.stühmer,iris.diederich,markus.pawlak')
    arg_parser.add_argument(
        '--clear-collection', '-c',
        help=f'Clear the {COLLECTION_NAME}',
        action='store_true'
    )

    args = arg_parser.parse_args()

    suppliers = args.suppliers.lower()
    suppliers = suppliers.split(',')

    if args.clear_collection:
        clear_collection()

    process_file(suppliers)

    logger.fatal("Done!")
    try:
        dbClient.close()
        logger.info("🔒 Milvus Lite database closed cleanly.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to close Milvus client: {e}")
