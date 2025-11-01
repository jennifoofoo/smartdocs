"""
Abfrage der Milvus-Datenbank mit LLM-Integration.

Für einfache Vektorsuche ohne LLM siehe QueryDataBase.py

Verwendung:
  python QueryDataBase_LLM.py -q "Deine Frage hier"                    # Nur Vektorsuche
  python QueryDataBase_LLM.py -q "Deine Frage hier" --use-llm          # Mit LLM (empfohlen)
  python QueryDataBase_LLM.py -q "Deine Frage hier" --use-llm --model gemma:2b
  python QueryDataBase_LLM.py -q "Deine Frage hier" --use-llm --debug
"""

from typing import List
from src.core.milvus_mgmt import COLLECTION_NAME, dbClient
from src.utilities.chunk_embed import embed_texts, rerank_results

dbClient.load_collection(collection_name=COLLECTION_NAME)


def search_documents(user_query: str, limit: int = 10, use_reranking: bool = True) -> List[dict]:
    """
    Führt eine Vektor-Ähnlichkeitssuche in der Datenbank durch.
    
    Args:
        user_query: Die Suchanfrage
        limit: Maximale Anzahl der Ergebnisse
        use_reranking: Ob Re-Ranking verwendet werden soll (Standard: True)
    
    Returns:
        Liste von Dokumenten-Chunks mit Metadaten
    """
    q_emb = embed_texts([user_query])[0]

    # Hole mehr Dokumente wenn Re-Ranking aktiviert
    # Faktor 3 für bessere Coverage der relevanten Dokumente
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

    # MilvusClient.search() gibt eine Liste von Listen zurück
    # Jedes Element ist ein dict mit 'id', 'distance' und 'entity' (die Felder)
    initial_results = results[0] if results else []
    
    # Re-Ranking wenn aktiviert
    if use_reranking and initial_results:
        return rerank_results(user_query, initial_results, top_k=limit)
    
    return initial_results[:limit]


def answer_with_llm(user_query: str, limit: int = 5, model: str = "qwen2:7b", debug: bool = False) -> str:
    try:
        from langchain_community.llms import Ollama
        from langchain.prompts import PromptTemplate
    except ImportError:
        return "❌ LangChain nicht installiert. Installiere mit: pip install langchain langchain-community"

    # Relevante Dokumente suchen
    results = search_documents(user_query, limit)

    if debug:
        print("\n" + "="*100)
        print("🔍 DEBUG: Gefundene Dokumente für Kontext")
        print("="*100)
    
    # Kontext zusammenstellen
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
        
        context_parts.append(f"Dokument {i} [{doc_name} - {elem_type}]:\n{chunk}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    if debug:
        print(f"\n{'='*100}")
        print(f"📝 Kontext-Länge: {len(context)} Zeichen")
        print(f"🤖 Verwende Modell: {model}")
        print("="*100 + "\n")

    # Verbesserter Prompt
    template = """Du bist ein Dokumenten-Analyse-Assistent für ein deutsches Unternehmen. 

WICHTIG: Deine Aufgabe ist es NUR, Informationen aus den bereitgestellten Dokumenten zu EXTRAHIEREN und zusammenzufassen. 
Du sollst KEINE E-Mails schreiben, keine Grußformeln verwenden, und nicht im Namen von Personen sprechen.

Die bereitgestellten Dokumente können E-Mails, Protokolle, Lieferscheine oder andere Geschäftsdokumente sein.
Extrahiere nur die relevanten Fakten und beantworte die Frage sachlich.

FRAGE DES NUTZERS:
{question}

DOKUMENTE:
{context}

ANLEITUNG FÜR DEINE ANTWORT:
1. Antworte NUR auf die gestellte Frage - schreibe keine E-Mail
2. Extrahiere relevante Fakten, Zahlen, Namen, Daten aus den Dokumenten
3. Strukturiere die Antwort mit Aufzählungen, wenn mehrere Punkte relevant sind
4. Nenne die Quelle (Dokumentname), wenn hilfreich
5. Wenn die Information nicht in den Dokumenten steht, sage: "Diese Information ist in den bereitgestellten Dokumenten nicht vorhanden."
6. Verwende KEINE Grußformeln wie "Mit freundlichen Grüßen" oder ähnliches

DEINE SACHLICHE ANTWORT:"""
    
    prompt = PromptTemplate.from_template(template)

    try:
        # Niedrige Temperatur für faktische, deterministische Antworten
        llm = Ollama(model=model, temperature=0.1)
        response = llm.invoke(prompt.format(question=user_query, context=context))
        
        # Post-processing: Entferne typische E-Mail-Artefakte falls sie doch auftauchen
        response = response.strip()
        
        # Entferne Grußformeln am Ende
        for greeting in ["Mit freundlichen Grüßen", "Mit besten Grüßen", "Viele Grüße", 
                        "Best regards", "Kind regards", "Grüße"]:
            if greeting in response:
                response = response.split(greeting)[0].strip()
        
        return response
    except Exception as e:
        return f"❌ LLM-Fehler: {e}\nStelle sicher, dass Ollama läuft: ollama serve"


def print_results(hits: List, show_chunks: bool = True):
    """Gibt die Suchergebnisse formatiert aus."""
    print(f"\n{'='*100}")
    print(f"📊 {len(hits)} Ergebnisse gefunden")
    print(f"{'='*100}\n")
    
    for i, hit in enumerate(hits, 1):
        # MilvusClient.search() gibt dicts mit 'id', 'distance', 'entity' zurück
        if isinstance(hit, dict):
            ent = hit.get('entity', hit)  # entity enthält die Felder
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
        description='Abfrage der Dokumenten-Datenbank',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    arg_parser.add_argument(
        '--question', '-q',
        help='Die Frage an die Dokumente',
        default='Welche Dokumente weisen auf entstehende Mehrkosten hin?'
    )
    arg_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=10,
        help='Maximale Anzahl der Ergebnisse (Standard: 10)'
    )
    arg_parser.add_argument(
        '--use-llm',
        action='store_true',
        help='Nutze ein LLM für die Antwort (benötigt Ollama)'
    )
    arg_parser.add_argument(
        '--model',
        default='qwen2:7b',
        help='Das Ollama-Modell für LLM-Modus (default: qwen2:7b, alternativ: gemma:2b)'
    )
    arg_parser.add_argument(
        '--debug',
        action='store_true',
        help='Zeige Debug-Informationen im LLM-Modus'
    )
    arg_parser.add_argument(
        '--no-reranking',
        action='store_true',
        help='Deaktiviere Re-Ranking (schneller aber schlechter)'
    )
    arg_parser.add_argument(
        '--no-chunks',
        action='store_true',
        help='Zeige nur Metadaten, keine Chunk-Inhalte'
    )
    
    args = arg_parser.parse_args()

    use_reranking = not args.no_reranking

    print(f"\n🔍 Frage: {args.question}")
    if use_reranking:
        print(f"🔄 Re-Ranking: Aktiviert")
    
    if args.use_llm:
        print(f"\n🤖 Verwende LLM ({args.model}) für Antwort...\n")
        answer = answer_with_llm(args.question, args.limit, model=args.model, debug=args.debug)
        print(f"\n{'='*100}")
        print("🤖 LLM-Antwort:")
        print(f"{'='*100}\n")
        print(answer)
        print()
    else:
        results = search_documents(args.question, args.limit, use_reranking=use_reranking)
        print_results(results, show_chunks=not args.no_chunks)
