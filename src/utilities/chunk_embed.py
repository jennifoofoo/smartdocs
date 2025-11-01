# -*- coding: utf-8 -*-
"""
SmartDocs - Chunk & Embed Module

Collection of functions to chunk and embed texts for semantic search.

This module handles:
- Document chunking with overlap
- Text embedding using sentence-transformers
- Re-ranking with cross-encoders
- Email and document processing

"""

import io
import os
import tempfile
from datetime import datetime, timezone
from typing import List

from sentence_transformers import SentenceTransformer, CrossEncoder
from unstructured.partition.auto import partition

from src.datatypes.emails_types import (EmailAttachment, EmlEmailMessage,
                                        MsgEmailMessage)
from src.utilities.logger_config import logger
from src.utilities.parser_tools import (has_valid_extension, is_image_mimetype,
                                        is_unsupported_mimetype)

encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# CrossEncoder für Re-Ranking (lazy loading)
_reranker = None

def get_reranker():
    """Lazy loading des CrossEncoder-Modells."""
    global _reranker
    if _reranker is None:
        logger.info("Loading CrossEncoder for re-ranking...")
        _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _reranker


def fill_row_with(chunks, embeds,
                  meta_data: dict) -> List[dict]:
    result = []

    for id, (chunk, emb) in enumerate(zip(chunks, embeds)):
        row = meta_data.copy()
        row["chunk_id"] = id 
        row["chunk"] = chunk
        row["embedding"] = emb
        result.append(row)

    return result


def chunk_text(text: str,
               chunk_size: int = 600,
               overlap: int = 100) -> List[str]:
    text = text or ""
    if chunk_size <= 0:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap if overlap > 0 else end
        if start < 0:
            start = 0
    return chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    # normalize_embeddings=True makes cosine distance work well
    return encoder.encode(texts, normalize_embeddings=True).tolist()


def rerank_results(query: str, results: List[dict], top_k: int = 8) -> List[dict]:
    """
    Re-rankt Suchergebnisse mit einem CrossEncoder.
    
    Args:
        query: Die Suchanfrage
        results: Liste von Milvus-Suchergebnissen (dicts mit 'entity' und 'distance')
        top_k: Anzahl der zu behaltenden Top-Ergebnisse
    
    Returns:
        Top-K re-ranked Ergebnisse sortiert nach Score
    """
    if not results or len(results) == 0:
        return results
    
    reranker = get_reranker()
    
    pairs = []
    for result in results:
        if isinstance(result, dict):
            chunk = result.get('entity', result).get('chunk', '')
        else:
            chunk = result.get('chunk', '')
        pairs.append([query, chunk])
    
    scores = reranker.predict(pairs)
    
    for result, score in zip(results, scores):
        if isinstance(result, dict):
            result['rerank_score'] = float(score)
        else:
            result.rerank_score = float(score)
    
    sorted_results = sorted(
        results, 
        key=lambda x: x.get('rerank_score', 0) if isinstance(x, dict) else getattr(x, 'rerank_score', 0),
        reverse=True
    )
    
    return sorted_results[:top_k]


def to_epoch_seconds(dt: datetime | str) -> int:
    if dt is None:
        dt = datetime.now()
    if isinstance(dt, str):
        dt = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


from nltk import sent_tokenize, download
import re
download('punkt', quiet=True)

def process_elements(elements, meta_data, filename, mimetype, full_path=None) -> List[dict]:
    import re
    from nltk import sent_tokenize

    smart_chunks: list[tuple[str, str]] = []
    MIN_SIZE = 250
    MAX_SIZE = 1200

    if mimetype == "application/pdf" and full_path:
        try:
            import pdfplumber
            with pdfplumber.open(full_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [cell.strip() if cell else "" for cell in row]
                            cleaned_table.append(" | ".join(cleaned_row))
                        table_text = "\n".join(cleaned_table)
                        if len(table_text.strip()) > 0:
                            smart_chunks.append((table_text, "PDFTable"))
                            print(f"[{filename}] page={page_num} extracted PDFTable (len={len(table_text)})")
        except Exception as e:
            logger.warning(f"⚠️ PDF table extraction failed for {filename}: {e}")

    buffer_text = ""
    buffer_type = None
    chunks = []

    def flush_buffer():
        nonlocal buffer_text, buffer_type
        text = buffer_text.strip()
        if not text:
            return
        if len(text) > MAX_SIZE:
            sentences = sent_tokenize(text)
            current = ""
            for s in sentences:
                if len(current) + len(s) < MAX_SIZE:
                    current += " " + s
                else:
                    chunks.append((current.strip(), buffer_type))
                    current = s
            if current.strip():
                chunks.append((current.strip(), buffer_type))
        else:
            chunks.append((text, buffer_type))
        buffer_text, buffer_type = "", None

    for el in elements:
        text = (el.text or "").strip()
        if not text:
            continue

        category = getattr(el, "category", None) or "Unknown"
        category = str(category).lower()

        if category == "table":
            flush_buffer()
            chunks.append((text, "Table"))
            continue

        if category in ["title", "header"] and buffer_type is not None:
            buffer_text += " " + text
            continue

        if buffer_type == category or len(buffer_text) + len(text) < MIN_SIZE:
            buffer_text += " " + text
        else:
            flush_buffer()
            buffer_text = text
            buffer_type = category

    flush_buffer()

    smart_chunks.extend(chunks)

    if not smart_chunks:
        combined_text = " ".join([(el.text or "").strip() for el in elements if (el.text or "").strip()])
        if combined_text:
            smart_chunks = [(combined_text[:MAX_SIZE], "Unknown")]
            logger.debug(f"⚙️ Fallback: single chunk created for {filename}")
        else:
            logger.warning(f"⚠️ No textual content extracted from {filename}")
            return []

    print(f"\n📘 {filename}: {len(smart_chunks)} Chunks erzeugt")
    for i, (txt, cat) in enumerate(smart_chunks[:10]):
        safe_txt = (txt or "")
        safe_cat = (cat or "Unknown")
        preview = re.sub(r"\s+", " ", safe_txt[:120])
        print(f"   [{i:02d}] {safe_cat:<10} | {len(safe_txt):4} Zeichen | {preview}")

    texts = [t for t, _ in smart_chunks if t.strip()]
    embeds = embed_texts(texts)
    if len(embeds) != len(texts):
        raise Exception("Length mismatch between embeddings and chunks")

    data_sets = []
    for idx, ((text, category), emb) in enumerate(zip(smart_chunks, embeds)):
        safe_category = category or "Unknown"
        if safe_category.strip().lower() == "none":
            safe_category = "Unknown"

        row = meta_data.copy()
        row["doc_name"] = filename
        row["file_type"] = mimetype
        row["chunk_id"] = idx
        row["chunk"] = text or ""
        row["embedding"] = emb
        row["element_type"] = safe_category
        data_sets.append(row)

    return data_sets


def deal_with_attachment(attachment: EmailAttachment, meta_data: dict, file_key: str) -> List[dict]:
    filename = attachment.filename
    mimetype = attachment.mimetype
    logger.debug(f'attachment name: {filename}')
    logger.debug(f'attachment type: {mimetype}')

    if is_image_mimetype(mimetype):
        logger.debug('Images as attachments not supported')
        return []
    if is_unsupported_mimetype(mimetype):
        logger.debug(f'MimeType {mimetype} as attachments not supported')
        return []
    if not has_valid_extension(filename):
        logger.debug(f'Filename {filename} not supported by extension rules')
        return []

    attached_file = io.BytesIO()
    attached_file.write(attachment.payload)

    elements = partition(file=attached_file, content_type=mimetype)

    full_path = None
    if mimetype == "application/pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(attachment.payload)
            full_path = tmp.name
            logger.debug(f"Temporary PDF saved at {full_path}")

    return process_elements(elements, meta_data, filename, mimetype, full_path)



def deal_with_email(email: EmlEmailMessage | MsgEmailMessage,
                    file_key: str) -> List[dict]:
    dirname = os.path.dirname(file_key)
    filename = os.path.basename(file_key)
    supplier = dirname.split('/')[0]

    if email.body == '' or len(email.body) == 0 or email.body is None:
        logger.warning('No body found in email, use subject for chunking')
        to_chunk = email.subject
    else:
        to_chunk = email.body

    chunks = chunk_text(to_chunk, chunk_size=600, overlap=100)
    embeds = embed_texts(chunks)

    if len(embeds) != len(chunks) or len(embeds) == 0:
        logger.error(
            f"Länge embeddings {len(embeds)} und chunks {len(chunks)} unterschiedlich oder 0")
        raise Exception("Length error")

    meta_data = {
        "doc_name": filename,
        "file_type": 'email',
        "num_attachments": len(email.attachments),
        "recipients": f"to: {email.receivers}, cc: {email.ccReceivers}, bcc: {email.bccReceivers}",
        "s3_file_key": file_key,
        "sender": email.senderAddress,
        "sent_at": to_epoch_seconds(email.sent_date),
        "subject": email.subject,
        "supplier": supplier,
    }
    data_sets = fill_row_with(chunks, embeds, meta_data)
    for row in data_sets:
        row["element_type"] = "EmailBody"

    for attachment in email.attachments:
        att_data_sets = deal_with_attachment(attachment, meta_data, file_key) or []
        data_sets += att_data_sets
    
    return data_sets

def deal_with_document(document: bytes, file_key: str) -> List[dict]:
    import tempfile
    
    dirname = os.path.dirname(file_key)
    filename = os.path.basename(file_key)
    supplier = dirname.split('/')[0]

    try:
        elements = partition(file=document)
        
    except Exception as e:
        logger.error(f"partition() failed for {filename}: {e}")
        elements = []
    logger.debug(f"🔍 partition() returned {len(elements)} elements for {filename}")
    for e in elements[:5]:
        logger.debug(f" - {type(e).__name__} | category={getattr(e, 'category', '?')} | text={(e.text or '')[:80]}")

    if not elements:
        logger.warning(f"⚠️ No elements extracted via unstructured for {filename}")

    file_type = elements[0].metadata.filetype if elements else "unknown"
    sent_date = elements[0].metadata.last_modified if elements else None

    meta_data = {
        "doc_name": filename,
        "file_type": file_type,
        "num_attachments": 0,
        "recipients": '',
        "s3_file_key": file_key,
        "sender": '',
        "sent_at": to_epoch_seconds(sent_date),
        "subject": filename,
        "supplier": supplier,
    }

    full_path = os.path.join(os.getenv("DATA_PATH", "."), file_key)
    if not os.path.exists(full_path):
        # Temporäre Datei schreiben, damit pdfplumber sie verarbeiten kann
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp.write(document)
            full_path = tmp.name
            logger.debug(f"🧩 Temp file for {filename} saved at {full_path}")
    print(f"\n🔍 {filename}: {len(elements)} elements parsed via unstructured")
    for e in elements[:10]:
        print(f" - type={type(e).__name__}, category={getattr(e, 'category', 'n/a')}, "
              f"text='{(e.text or '')[:80].replace(chr(10), ' ')}'")

    data_sets = process_elements(elements, meta_data, filename, file_type, full_path)

    if not data_sets:
        logger.warning(f"⚠️ process_elements returned 0 chunks for {filename}")

    return data_sets or []

