from collections import defaultdict
from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from dotenv import load_dotenv
from models import get_embedding_model,get_reranker_model,get_llm_model
from prompts import reranker_prompt,semantic_prompt,bm25_prompt,llm_risk_prompt,bm25_default_keywords,semantic_default_queries

load_dotenv()

class RiskStructure(BaseModel):
    risk_title: str
    severity: Literal['Low','Medium','High','Critical']
    section: str
    clause: str
    page: str
    why_it_is_risky: str
    possible_consequences: str

class RiskResponseStructure(BaseModel):
    risks: List[RiskStructure]

class QueriesStructure(BaseModel):
    queries: List[str]


mainPath = Path(__file__).resolve().parent.parent

embedding_model = get_embedding_model()
llm = get_llm_model()
hf_cross_encoder = get_reranker_model()
llm_with_tools = llm.with_structured_output(QueriesStructure)
llm_structured_risk_analyzer = llm.with_structured_output(RiskResponseStructure)

def reciprocal_rank_fusion(chunk_lists, k=60, verbose=True):
    if verbose:
        print("\n" + "=" * 60)
        print("APPLYING RECIPROCAL RANK FUSION")
        print("=" * 60)
        print(f"\nUsing k={k}")
        print("Calculating RRF scores...\n")

    rrf_scores = defaultdict(float)
    all_unique_chunks = {}

    chunk_id_map = {}
    chunk_counter = 1

    for query_idx, chunks in enumerate(chunk_lists, 1):
        if verbose:
            print(f"Processing Query {query_idx} results:")

        for position, chunk in enumerate(chunks, 1):  # position is 1-indexed
            chunk_content = chunk.page_content

            if chunk_content not in chunk_id_map:
                chunk_id_map[chunk_content] = f"Chunk_{chunk_counter}"
                chunk_counter += 1

            chunk_id = chunk_id_map[chunk_content]

            all_unique_chunks[chunk_content] = chunk

            position_score = 1 / (k + position)

            rrf_scores[chunk_content] += position_score

            if verbose:
                print(
                    f"  Position {position}: {chunk_id} +{position_score:.4f} (running total: {rrf_scores[chunk_content]:.4f})")
                print(f"    Preview: {chunk_content[:80]}...")

        if verbose:
            print()

    sorted_chunks = sorted(
        [(all_unique_chunks[chunk_content], score) for chunk_content, score in rrf_scores.items()],
        key=lambda x: x[1],
        reverse=True
    )

    if verbose:
        print(f"✅ RRF Complete! Processed {len(sorted_chunks)} unique chunks from {len(chunk_lists)} queries.")

    return sorted_chunks

def process_query(db, docs, n_retrieve_chunks=20, n_rrf_chunks=80, n_chunks=15, user_query: str = ''):
    faiss_retriever = db.as_retriever(search_kwargs={'k': n_retrieve_chunks})
    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = n_retrieve_chunks
    query_responses = []

    if user_query == '':
        bm25_keywords = bm25_default_keywords
        semantic_queries = semantic_default_queries
    else:

        bm25_responses = llm_with_tools.invoke(bm25_prompt.format(user_query=user_query))
        bm25_keywords = bm25_responses.queries

        semantic_responses = llm_with_tools.invoke(semantic_prompt.format(user_query=user_query))
        semantic_queries = semantic_responses.queries

    for q in bm25_keywords:
        chunks = bm25_retriever.invoke(q)
        query_responses.append(chunks)
    for q in semantic_queries:
        chunks = faiss_retriever.invoke(q)
        query_responses.append(chunks)

    final_chunks = reciprocal_rank_fusion(query_responses, verbose=False)

    reranker = CrossEncoderReranker(model=hf_cross_encoder, top_n=n_chunks)
    reranked_chunks = reranker.compress_documents(documents=[c for (c,i) in final_chunks][:n_rrf_chunks], query=reranker_prompt)

    llm_prompt = llm_risk_prompt

    chunk_ids = set()
    for c in reranked_chunks:
        chunk_ids.add(c.metadata.get('chunk_id'))

    for i,c in enumerate(reranked_chunks):
        llm_prompt += f'CHUNK {i}:\n {c.page_content}\n'
        if c.metadata.get('tables'):
            for n,t in enumerate(c.metadata.get('tables')):
                llm_prompt += f'TABLE STRUCTURE {n}:\n {t}\n'
        llm_prompt += f"PAGE: {c.metadata.get('page', 'Undefined')}\n"
        if c.metadata.get("previous_chunk_id") is not None:
            if c.metadata.get("previous_chunk_id") not in chunk_ids:
                llm_prompt += f'PREVIOUS CHUNK:\n {docs[c.metadata.get("previous_chunk_id")].page_content}\n'
        if c.metadata.get("next_chunk_id") is not None:
            if c.metadata.get("next_chunk_id") not in chunk_ids:
                llm_prompt += f'NEXT CHUNK:\n {docs[c.metadata.get("next_chunk_id")].page_content}\n'

    try:
        response = llm_structured_risk_analyzer.invoke(llm_prompt)
    except Exception as e:
        raise RuntimeError(f'Error occurred during risk report generation\nError: {e}')

    for risk in response.risks:
        print(risk.severity, risk.risk_title, risk.section, risk.clause)
    return response


