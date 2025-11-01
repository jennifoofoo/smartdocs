# Zeigt gespeicherte Chunks in Milvus Lite an

from src.core.milvus_mgmt import COLLECTION_NAME, dbClient

def show_chunks(doc_name: str | None = None,
                s3_file_key: str | None = None,
                limit: int = 9999):
    # --- Debug: Pfad & Collections prüfen ---
    try:
        using_info = getattr(dbClient, "_using", None) or "unknown"
        print(f"📂 Using Milvus DB file: {using_info}")
        print(f"📚 Collections: {dbClient.list_collections()}")
        
        # Anzahl der Entities prüfen
        stats = dbClient.get_collection_stats(collection_name=COLLECTION_NAME)
        row_count = stats.get("row_count", 0)
        print(f"📊 Total entities in collection: {row_count}")
    except Exception as e:
        print(f"⚠️ Could not inspect DB connection: {e}")

    # --- Filter zusammenbauen ---
    flt = []
    if doc_name:
        flt.append(f'doc_name == "{doc_name}"')
    if s3_file_key:
        flt.append(f's3_file_key == "{s3_file_key}"')
    filter_expr = " and ".join(flt) if flt else None

    # --- Collection laden ---
    try:
        dbClient.load_collection(collection_name=COLLECTION_NAME)
    except Exception as e:
        print(f"⚠️ Could not load collection {COLLECTION_NAME}: {e}")
        return

    # --- Alle Datensätze abrufen ---
    try:
        # Wenn kein Filter gesetzt ist, verwende einen catch-all Filter
        if not filter_expr:
            filter_expr = "chunk_id >= 0"
        
        rows = dbClient.query(
            collection_name=COLLECTION_NAME,
            filter=filter_expr,
            output_fields=[
                "chunk_id", "element_type", "file_type",
                "doc_name", "s3_file_key", "chunk"
            ],
            limit=limit,
        )
    except Exception as e:
        print(f"❌ Query failed: {e}")
        print(f"   Filter was: {filter_expr}")
        return

    if not rows:
        print("\n=== 0 Chunks found ===")
        print("Filter:", filter_expr or "(no filter)")
        return

    # --- Sortieren nach chunk_id ---
    rows = sorted(rows, key=lambda r: r["chunk_id"])

    # --- Übersichtliche Ausgabe ---
    print(f"\n=== {len(rows)} Chunks in '{COLLECTION_NAME}' ===")
    if doc_name:
        print(f"📄 Document: {doc_name}")
    for r in rows:
        preview = (r["chunk"] or "").replace("\n", " ")[:160]
        print(f'[{r["chunk_id"]:04d}] {r.get("element_type","?"):>12} '
              f'| {len(r.get("chunk","")):5d} chars | {preview}…')
    print()

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Inspect stored document chunks in Milvus Lite")
    ap.add_argument("--doc", help="doc_name (Dateiname)", default=None)
    ap.add_argument("--key", help="s3_file_key (relativer Pfad unter DATA_PATH)", default=None)
    ap.add_argument("--limit", type=int, default=9999, help="Max number of chunks to show")
    args = ap.parse_args()
    show_chunks(doc_name=args.doc, s3_file_key=args.key, limit=args.limit)
