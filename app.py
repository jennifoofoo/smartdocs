"""
SmartDocs - Personal AI Document Assistant

A privacy-first RAG system for intelligent document search and analysis.
All processing happens locally - your documents never leave your machine.

Installation:
    pip install chainlit

Start:
    chainlit run app.py -w
"""

import chainlit as cl
from typing import List, Dict
from src.core.milvus_mgmt import COLLECTION_NAME, dbClient
from src.utilities.chunk_embed import embed_texts, rerank_results
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate

# Load vector collection when the app starts
dbClient.load_collection(collection_name=COLLECTION_NAME)


def search_documents(query: str, limit: int = 5) -> List[Dict]:
    """Search for relevant documents in the vector database."""
    q_emb = embed_texts([query])[0]
    
    search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
    results = dbClient.search(
        collection_name=COLLECTION_NAME,
        data=[q_emb],
        anns_field="embedding",
        search_params=search_params,
        limit=limit,
        output_fields=[
            "supplier", "s3_file_key", "doc_name", "file_type",
            "chunk_id", "sender", "subject", "chunk", "element_type"
        ]
    )
    
    return results[0] if results else []


@cl.on_chat_start
async def start():
    """Called when the chat session starts."""

    # Welcome message
    await cl.Message(
        content="""# 📚 SmartDocs - Your Personal AI Document Assistant

Welcome! I can help you find information across all your documents using AI-powered semantic search.

**Example Questions:**
- Summarize the meeting notes from last week
- Find all invoices from Q4 2024
- What were the key decisions in document X?
- Who sent emails about project deadlines?
- Compare contract terms between documents

**How it works:**
Documents are split into "chunks" (text sections). The AI analyzes the most relevant chunks to answer your questions accurately.

🔐 **100% Private** - All processing happens locally on your machine!
"""
    ).send()
    
    # Persist initial settings
    settings = await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="model",
                label="LLM Model",
                values=["qwen2:7b", "gemma:2b"],
                initial_value="qwen2:7b",
            ),
            cl.input_widget.Slider(
                id="limit",
                label="Chunks to analyze",
                initial=8,
                min=3,
                max=15,
                step=1,
                description="How many text sections should the LLM analyze?"
            ),
            cl.input_widget.Switch(
                id="use_reranking",
                label="Enable re-ranking",
                initial=True,
                description="Fetches more chunks and selects the best ones (more accurate, slower)"
            ),
            cl.input_widget.Switch(
                id="show_sources",
                label="Show sources",
                initial=True,
            ),
        ]
    ).send()
    
    cl.user_session.set("settings", {
        "model": "qwen2:7b",
        "limit": 8,
        "use_reranking": True,
        "show_sources": True,
    })


@cl.on_settings_update
async def setup_agent(settings):
    """Called when chat settings are updated."""
    cl.user_session.set("settings", settings)


@cl.on_message
async def main(message: cl.Message):
    """Handles incoming chat messages."""

    # Retrieve current settings
    settings = cl.user_session.get("settings")
    model = settings.get("model", "qwen2:7b")
    limit = settings.get("limit", 8)
    use_reranking = settings.get("use_reranking", True)
    show_sources = settings.get("show_sources", True)

    # Search the vector database
    msg = cl.Message(content="🔍 Searching for relevant chunks in the database...")
    await msg.send()
    
    # Fetch more chunks when re-ranking is enabled
    # Use factor 3 to increase likelihood of relevant chunks
    search_limit = limit * 3 if use_reranking else limit
    initial_results = search_documents(message.content, search_limit)
    
    if not initial_results:
        msg.content = "❌ No relevant chunks found."
        await msg.update()
        return
    
    # Apply re-ranking if enabled
    if use_reranking:
        msg.content = f"🔄 Re-ranking: Evaluating {len(initial_results)} chunks, selecting top {limit}..."
        await msg.update()
        results = rerank_results(message.content, initial_results, top_k=limit)
        msg.content = f"✅ Top-{len(results)} chunks selected. Analyzing with {model}..."
    else:
        results = initial_results
        msg.content = f"✅ Found {len(results)} relevant chunks. Analyzing with {model}..."
    
    await msg.update()
    
    # Build context for the LLM
    context_parts = []
    source_elements = []
    unique_sources = set()  # Track unique sources for summary
    
    for i, hit in enumerate(results, 1):
        if isinstance(hit, dict):
            ent = hit.get('entity', hit)
            score = 1 - hit.get('distance', 0)
        else:
            ent = hit
            score = 0.0
        
        doc_name = ent.get('doc_name', 'Unknown')
        elem_type = ent.get('element_type', 'Unknown')
        chunk = ent.get('chunk', '')
        supplier = ent.get('supplier', 'Unknown')
        s3_file_key = ent.get('s3_file_key', 'Unknown')
        file_type = ent.get('file_type', 'Unknown')
        
        # Store unique sources
        unique_sources.add(f"{supplier}/{doc_name}")
        
        context_parts.append(f"Document {i} [{doc_name} - {elem_type}]:\n{chunk}")
        
        # Create source element for Chainlit
        if show_sources:
            # Show re-rank score when available, otherwise vector score
            rerank_score = ent.get('rerank_score', None)
            score_display = f"Re-Rank: {rerank_score:.3f}" if rerank_score else f"Vector: {score:.3f}"
            
            source_elements.append(
                cl.Text(
                    name=f"📄 {doc_name}",
                    content=f"""**📁 Filename:** {doc_name}
**📂 Path:** {s3_file_key}
**👤 Source:** {supplier}
**📝 Type:** {elem_type} ({file_type})
**📊 Score:** {score_display}
**#️⃣ Chunk:** {ent.get('chunk_id', '?')}

**Content:**
{chunk[:500]}{"..." if len(chunk) > 500 else ""}""",
                    display="side"
                )
            )
    
    context = "\n\n---\n\n".join(context_parts)
    
    # LLM Prompt
    template = """You are an intelligent document analysis assistant for SmartDocs.

IMPORTANT: Your task is ONLY to EXTRACT and summarize information from the provided documents. 
Do NOT write emails, use greetings, or speak on behalf of people.

The provided documents may include emails, meeting notes, invoices, contracts, or other business documents.
Extract only relevant facts and answer the question objectively.

USER QUESTION:
{question}

DOCUMENTS:
{context}

INSTRUCTIONS FOR YOUR ANSWER:
1. Answer ONLY the question asked - do not write emails or letters
2. Extract relevant facts, numbers, names, dates from the documents
3. Structure your answer with bullet points when multiple points are relevant
4. Cite the source (Document number) when helpful
5. If the information is not in the documents, say: "This information is not available in the provided documents."
6. Do NOT use closing phrases like "Best regards" or similar
7. Be concise and factual

YOUR FACTUAL ANSWER:"""
    
    prompt = PromptTemplate.from_template(template)
    
    try:
        llm = Ollama(model=model, temperature=0.1)
        
        # Stream the answer
        response_msg = cl.Message(content="")
        await response_msg.send()
        
        full_response = ""
        async for chunk in llm.astream(prompt.format(question=message.content, context=context)):
            full_response += chunk
            await response_msg.stream_token(chunk)
        
        # Post-processing: remove sign-off phrases
        for greeting in [
            "Mit freundlichen Grüßen",
            "Mit besten Grüßen",
            "Viele Grüße",
            "Best regards",
            "Kind regards",
            "Sincerely",
        ]:
            if greeting in full_response:
                full_response = full_response.split(greeting)[0].strip()
        
        # Append a source summary at the end
        if show_sources and unique_sources:
            sources_list = "\n".join([f"- {src}" for src in sorted(unique_sources)])
            full_response += f"\n\n---\n\n**📚 Sources used ({len(unique_sources)}):**\n{sources_list}"
            response_msg.content = full_response
        
        # Attach sources if enabled
        if show_sources and source_elements:
            response_msg.elements = source_elements
            await response_msg.update()
        
    except Exception as e:
        msg.content = f"LLM error: {e}\n\nMake sure Ollama is running: `ollama serve`"
        await msg.update()


if __name__ == "__main__":
    pass