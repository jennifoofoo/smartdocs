"""
Query the Milvus database with optional LLM integration.

For simple vector search without an LLM see QueryDataBase.py

Usage examples:
  python QueryDataBase_LLM.py -q "Your question here"                   # Vector search only
  python QueryDataBase_LLM.py -q "Your question here" --use-llm         # With LLM (recommended)
  python QueryDataBase_LLM.py -q "Your question here" --use-llm --model gemma:2b
  python QueryDataBase_LLM.py -q "Your question here" --use-llm --debug
"""

from typing import List
from src.core.milvus_mgmt import COLLECTION_NAME, dbClient
from src.utilities.chunk_embed import embed_texts, rerank_results

dbClient.load_collection(collection_name=COLLECTION_NAME)


def search_documents(user_query: str, limit: int = 10, use_reranking: bool = True) -> List[dict]:
    """
    Execute a vector similarity search in the database.

    Args:
        user_query: The search query string.
        limit: Maximum number of results to return.
        use_reranking: Whether to run re-ranking for better precision (default: True).

    Returns:
        List of document chunks with metadata.
    """
    q_emb = embed_texts([user_query])[0]

    # Fetch more documents when re-ranking is enabled to increase coverage
    search_limit = limit * 3 if use_reranking else limit

    search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
    results = dbClient.search(
        collection_name=COLLECTION_NAME,
        data=[q_emb],
        anns_field="embedding",
        search_params=search_params,
        limit=search_limit,
        output_fields=[
            "supplier", "s3_file_key", "doc_name", "file_type",
            "chunk_id", "sender", "subject", "chunk", "element_type"
        ]
    )

    # MilvusClient.search() returns a list of lists.
    # Each entry contains 'id', 'distance', and 'entity' (the stored fields).
    initial_results = results[0] if results else []

    # Apply re-ranking if enabled
    if use_reranking and initial_results:
        return rerank_results(user_query, initial_results, top_k=limit)

    return initial_results[:limit]


def answer_with_llm(user_query: str, limit: int = 5, model: str = "qwen2:7b", debug: bool = False) -> str:
    try:
        from langchain_community.llms import Ollama
        from langchain.prompts import PromptTemplate
    except ImportError:
        return "❌ LangChain is not installed. Install with: pip install langchain langchain-community"

    # Retrieve relevant documents
    results = search_documents(user_query, limit)

    if debug:
        print("\n" + "="*100)
        print("🔍 DEBUG: Documents retrieved for context")
        print("="*100)

    # Build the context
    context_parts = []
    for i, hit in enumerate(results, 1):
        if isinstance(hit, dict):
            ent = hit.get('entity', hit)
            score = 1 - hit.get('distance', 0)
        elif hasattr(hit, 'entity'):
            ent = hit.entity
            score = 1 - hit.distance
        else:
            ent = hit
            score = 0.0

        doc_name = ent.get('doc_name', 'Unknown')
        elem_type = ent.get('element_type', 'Unknown')
        chunk = ent.get('chunk', '')

        if debug:
            print(f"\n[{i}] {doc_name} ({elem_type}) - Score: {score:.3f}")
            print(f"    Chunk: {chunk[:200]}...")

        context_parts.append(f"Document {i} [{doc_name} - {elem_type}]:\n{chunk}")

    context = "\n\n---\n\n".join(context_parts)

    if debug:
        print(f"\n{'='*100}")
        print(f"📝 Context length: {len(context)} characters")
        print(f"🤖 Using model: {model}")
        print("="*100 + "\n")

    # Prompt template
    template = """You are a document analysis assistant for SmartDocs.

IMPORTANT: Your task is ONLY to EXTRACT and summarize information from the provided documents.
Do NOT write emails, use greetings, or speak on behalf of people.

The provided documents may include emails, meeting notes, delivery notes, or other business documents.
Extract only the relevant facts and answer the question objectively.

USER QUESTION:
{question}

DOCUMENTS:
{context}

INSTRUCTIONS FOR YOUR ANSWER:
1. Answer ONLY the question that was asked – do not write an email.
2. Extract relevant facts, numbers, names, dates from the documents.
3. Structure your answer with bullet points when multiple items are relevant.
4. Cite the source (document name) when helpful.
5. If the information is not in the documents, say: "This information is not available in the provided documents."
6. Do NOT use closing phrases such as "Best regards".

YOUR FACTUAL ANSWER:"""

    prompt = PromptTemplate.from_template(template)

    try:
        # Low temperature for factual, deterministic answers
        llm = Ollama(model=model, temperature=0.1)
        response = llm.invoke(prompt.format(question=user_query, context=context))

        # Post-processing: remove typical email artefacts if they appear
        response = response.strip()

        # Remove closing greetings at the end
        for greeting in ["Mit freundlichen Grüßen", "Mit besten Grüßen", "Viele Grüße",
                        "Best regards", "Kind regards", "Grüße"]:
            if greeting in response:
                response = response.split(greeting)[0].strip()

        return response
    except Exception as e:
        return f"❌ LLM error: {e}\nEnsure that Ollama is running: ollama serve"


def print_results(hits: List, show_chunks: bool = True):
    """Pretty-print the search results."""
    print(f"\n{'='*100}")
    print(f"📊 {len(hits)} results found")
    print(f"{'='*100}\n")

    for i, hit in enumerate(hits, 1):
        # MilvusClient.search() returns dicts with 'id', 'distance', 'entity'
        if isinstance(hit, dict):
            ent = hit.get('entity', hit)  # entity holds the fields
            score = 1 - hit.get('distance', 0)
        elif hasattr(hit, 'entity'):
            ent = hit.entity
            score = 1 - hit.distance
        else:
            ent = hit
            score = 0.0

        print(f"[{i}] Score: {score:.4f} | {ent.get('doc_name', 'N/A')}")
        print(f"    📁 Supplier: {ent.get('supplier', 'N/A')}")
        print(f"    📧 Sender: {ent.get('sender', 'N/A')}")
        print(f"    📝 Subject: {ent.get('subject', 'N/A')}")
        print(f"    🏷️  Type: {ent.get('element_type', 'N/A')}")
        print(f"    📄 File: {ent.get('s3_file_key', 'N/A')}")

        if show_chunks:
            chunk = ent.get('chunk', '')[:300]
            print(f"    💬 Chunk: {chunk}...")

        print()


if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser(
        description='Query the document database.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    arg_parser.add_argument(
        '--question', '-q',
        help='Question to ask the indexed documents.',
        default='Which documents mention additional costs?'
    )
    arg_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=10,
        help='Maximum number of results (default: 10).'
    )
    arg_parser.add_argument(
        '--use-llm',
        action='store_true',
        help='Use an LLM for the answer (requires Ollama).'
    )
    arg_parser.add_argument(
        '--model',
        default='qwen2:7b',
        help='Ollama model for LLM mode (default: qwen2:7b, alternative: gemma:2b).'
    )
    arg_parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug information in LLM mode.'
    )
    arg_parser.add_argument(
        '--no-reranking',
        action='store_true',
        help='Disable re-ranking (faster but less accurate).'
    )
    arg_parser.add_argument(
        '--no-chunks',
        action='store_true',
        help='Only show metadata, omit chunk content.'
    )

    args = arg_parser.parse_args()

    use_reranking = not args.no_reranking

    print(f"\n🔍 Question: {args.question}")
    if use_reranking:
        print(f"🔄 Re-ranking: Enabled")

    if args.use_llm:
        print(f"\n🤖 Using LLM ({args.model}) to generate answer...\n")
        answer = answer_with_llm(args.question, args.limit, model=args.model, debug=args.debug)
        print(f"\n{'='*100}")
        print("🤖 LLM Answer:")
        print(f"{'='*100}\n")
        print(answer)
        print()
    else:
        results = search_documents(args.question, args.limit, use_reranking=use_reranking)
        print_results(results, show_chunks=not args.no_chunks)
