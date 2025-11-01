###
# Ensure that the environment variables are set this way, before running the
# script. Otherwise the database is reset and you will not receive any answer.
#
# DELETE_OLD_COLLECTION = False
#


# %%
from typing import List

from src.core.milvus_mgmt import COLLECTION_NAME, dbClient
from src.utilities.chunk_embed import embed_texts

dbClient.load_collection(collection_name=COLLECTION_NAME)


def process_query(user_query: str, limit: int = 10) -> List[List[dict]]:

    q_emb = embed_texts([user_query])[0]

    search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
    results = dbClient.search(
        collection_name=COLLECTION_NAME,
        data=[q_emb],
        anns_field="embedding",
        search_params=search_params,
        limit=limit,
        output_fields=["supplier", "s3_file_key", "doc_name", "file_type",
                       "chunk_id", "sender", "subject", "chunk", "element_type" ]
    )

    return results


if __name__ == "__main__":
    import argparse

    # parse command line arguments
    arg_parser = argparse.ArgumentParser(description='')
    arg_parser.add_argument(
        '--question', '-q',
        help='Stelle eine Frage an die Dokumente. Nutze Anführungszeichen!',
        default='Welche Dokumente weisen auf entstehende Mehrkosten hin?'
    )
    args = arg_parser.parse_args()

    question = args.question

    results = process_query(user_query=question)

    for hit in results[0]:
        ent = hit.entity
        print(
            f"- START -\nsupplier={ent.get('supplier')} sender={ent.get('sender')}\n--")
        print(f"score={1-hit.distance:.4f} file_type={ent.get('file_type')}")
        print(f"chunk_id={ent.get('chunk_id')}\n--")
        print(f"s3_file_key={ent.get('s3_file_key')}\n")
        print(
            f"doc_name={ent.get('doc_name')}\n\tsubject={ent.get('subject')}")
        print(f"element_type={ent.get('element_type')}\n--")
        print(f"chunk:\n{ent.get('chunk')}\n- END -\n")
