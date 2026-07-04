from collections import defaultdict
from pathlib import Path
from typing import List

from pydantic import BaseModel
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from dotenv import load_dotenv
from models import get_embedding_model,get_reranker_model,get_llm_model
from prompts import reranker_prompt,semantic_prompt,bm25_prompt,llm_risk_prompt

load_dotenv()

class QueriesStructure(BaseModel):
    queries: List[str]


mainPath = Path(__file__).resolve().parent.parent

embedding_model = get_embedding_model()
llm = get_llm_model()
hf_cross_encoder = get_reranker_model()
llm_with_tools = llm.with_structured_output(QueriesStructure)

def reciprocal_rank_fusion(chunk_lists, k=60, verbose=True):
    if verbose:
        print("\n" + "=" * 60)
        print("APPLYING RECIPROCAL RANK FUSION")
        print("=" * 60)
        print(f"\nUsing k={k}")
        print("Calculating RRF scores...\n")

    # Data structures for RRF calculation
    rrf_scores = defaultdict(float)  # Will store: {chunk_content: rrf_score}
    all_unique_chunks = {}  # Will store: {chunk_content: actual_chunk_object}

    # For verbose output - track chunk IDs
    chunk_id_map = {}
    chunk_counter = 1

    # Go through each retrieval result
    for query_idx, chunks in enumerate(chunk_lists, 1):
        if verbose:
            print(f"Processing Query {query_idx} results:")

        # Go through each chunk in this query's results
        for position, chunk in enumerate(chunks, 1):  # position is 1-indexed
            # Use chunk content as unique identifier
            chunk_content = chunk.page_content

            # Assign a simple ID if we haven't seen this chunk before
            if chunk_content not in chunk_id_map:
                chunk_id_map[chunk_content] = f"Chunk_{chunk_counter}"
                chunk_counter += 1

            chunk_id = chunk_id_map[chunk_content]

            # Store the chunk object (in case we haven't seen it before)
            all_unique_chunks[chunk_content] = chunk

            # Calculate position score: 1/(k + position)
            position_score = 1 / (k + position)

            # Add to RRF score
            rrf_scores[chunk_content] += position_score

            if verbose:
                print(
                    f"  Position {position}: {chunk_id} +{position_score:.4f} (running total: {rrf_scores[chunk_content]:.4f})")
                print(f"    Preview: {chunk_content[:80]}...")

        if verbose:
            print()

    # Sort chunks by RRF score (highest first)
    sorted_chunks = sorted(
        [(all_unique_chunks[chunk_content], score) for chunk_content, score in rrf_scores.items()],
        key=lambda x: x[1],  # Sort by RRF score
        reverse=True  # Highest scores first
    )

    if verbose:
        print(f"✅ RRF Complete! Processed {len(sorted_chunks)} unique chunks from {len(chunk_lists)} queries.")

    return sorted_chunks

def process_query(db, docs, n_retrieve_chunks=20, n_rrf_chunks=80, n_chunks=10, user_query: str = ''):
    faiss_retriever = db.as_retriever(search_kwargs={'k': n_retrieve_chunks})
    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = n_retrieve_chunks
    query_responses = []

    if user_query == '':
        bm25_keywords = [

            # === HIDDEN / UNCAPPED LIABILITY ===
            "indemnify indemnification indemnitor indemnitee hold harmless defend",
            "unlimited liability uncapped liability joint and several liability vicarious liability",
            "consequential damages indirect damages incidental damages punitive damages special damages",
            "third party claims legal costs defense costs attorney fees",

            # === LIABILITY LIMITATIONS & EXCLUSIONS ===
            "limitation of liability liability cap exclude liability waive liability",
            "gross negligence willful misconduct fraud intentional act carve out",
            "exclusive remedy sole remedy limited remedy",

            # === PENALTIES & INDEMNIFICATION ===
            "liquidated damages penalty clause financial penalty",
            "indemnify and defend at its sole cost and expense",
            "service credit penalty for non-performance",

            # === ONE-SIDED / UNILATERAL OBLIGATIONS ===
            "sole discretion absolute discretion at its option may determine",
            "unilateral amendment unilateral modification without consent",
            "deemed accepted silence as acceptance passive consent",
            "right to modify right to change without notice",
            "not obligated may elect may choose has no obligation",

            # === TERMINATION RISKS ===
            "termination for convenience without cause at will termination",
            "termination for cause material breach notice to cure cure period",
            "automatic termination insolvency bankruptcy change of control",
            "termination notice period wind-down costs surviving obligations",
            "suspension of work suspend services right to suspend",

            # === AUTO-RENEWAL TRAPS ===
            "automatic renewal auto-renewal evergreen renewal",
            "opt-out notice deadline renewal notice window",
            "successive term renews automatically unless terminated",

            # === PAYMENT RISKS ===
            "withhold payment suspend payment no obligation to pay set-off deduct",
            "delayed payment late payment penalty interest on late payment",
            "milestone payment contingent payment conditional payment",
            "clawback refund repayment overpayment recovery advance recovery",
            "price adjustment escalation variation order change order unilateral fee",
            "currency exchange rate foreign currency forex fluctuation",

            # === IP OWNERSHIP ===
            "assign assignment intellectual property IP ownership transfer",
            "work for hire work made for hire",
            "moral rights waiver authorship rights",
            "background IP foreground IP pre-existing IP",
            "license grant royalty-free irrevocable sublicense field of use",
            "data ownership data rights output ownership derived data",
            "open source GPL LGPL MIT Apache copyleft",

            # === CONFIDENTIALITY ISSUES ===
            "confidential information non-disclosure NDA proprietary information trade secret",
            "confidentiality obligation duration scope exceptions",
            "survival of confidentiality post-termination disclosure restriction",

            # === DATA & PRIVACY RISKS ===
            "data breach notification data processor data controller",
            "cross-border data transfer data retention data deletion",
            "GDPR CCPA data protection personal data processing",

            # === JURISDICTION / DISPUTE RESOLUTION ===
            "arbitration binding arbitration mandatory arbitration JAMS AAA ICC",
            "governing law choice of law jurisdiction venue",
            "class action waiver jury trial waiver",
            "limitation period time-bar claim notification deadline",

            # === REGULATORY & COMPLIANCE EXPOSURE ===
            "anti-bribery anti-corruption FCPA UK Bribery Act AML",
            "export controls sanctions compliance debarred suspended blacklisted",
            "conflict of interest collusion anti-competitive",

            # === EXCLUSIVITY & NON-COMPETE ===
            "exclusivity exclusive dealing minimum purchase take-or-pay",
            "non-compete non-solicitation restrictive covenant",
            "right of first refusal most favored customer",

            # === WARRANTY DISCLAIMERS ===
            "represents warrants representation warranty breach of warranty",
            "as-is no warranty disclaimer of warranties merchantability fitness for purpose",
            "warranty period remedy cure no service level agreement",

            # === FORCE MAJEURE ABUSE ===
            "force majeure act of God beyond reasonable control",
            "change in law regulatory change compliance cost burden",
            "material adverse change MAC material adverse effect MAE",
            "risk of loss transfer of title delivery risk Incoterms",

            # === UNFAIR OBLIGATIONS & TIMELINES ===
            "best efforts reasonable endeavors commercially reasonable efforts",
            "service level agreement SLA KPI key performance indicator",
            "time is of the essence strict deadline",
            "step-in right right to step in replace subcontractor",
            "subcontracting approval prohibited subcontracting",

            # === AUDIT & RECORDS ===
            "audit rights right to audit access to records books accounts",
            "record retention document retention seven years",
            "reporting obligation notification obligation disclosure requirement",

            # === CONTRADICTORY / INCONSISTENT CLAUSES ===
            "notwithstanding anything to the contrary",
            "in the event of conflict in case of inconsistency order of precedence",
            "entire agreement merger clause supersedes prior agreements",

            # === MANIPULATIVE / BOILERPLATE LEGAL WORDING ===
            "without limitation including but not limited to",
            "severability invalid provision unenforceable",
            "waiver no waiver cumulative remedies",
            "at any time without prior notice without reason",
            "irrevocable perpetual worldwide royalty-free unconditional absolute",

            # === FUNDING & DONOR COMPLIANCE ===
            "donor terms donor funding pass-through conditions grant compliance",
            "government contract public procurement value for money",
            "subject to funding contingent on funding availability",
            "cost reimbursement allowable costs unallowable costs cost principles",
            "flow-down provisions subrecipient monitoring match funding cost share",
        ]
        semantic_queries = [

            # === HIDDEN / UNCAPPED LIABILITY ===
            "clauses where one party must cover the other party's losses, legal costs, or damages arising from the contract or third-party claims, with liability that is unlimited or very broadly defined",
            "situations where a party is protected from liability even for serious wrongdoing, or where standard liability protections such as caps or exclusions are removed through carve-outs",

            # === LIABILITY LIMITATIONS & EXCLUSIONS ===
            "provisions that cap, restrict, or exclude what one party can recover for losses, including exclusions for lost profits, business disruption, or indirect damages",

            # === PENALTIES & INDEMNIFICATION ===
            "financial penalties, liquidated damages, or cost-recovery mechanisms that disproportionately burden one party, including penalties framed as pre-estimated compensation",

            # === ONE-SIDED / UNILATERAL OBLIGATIONS ===
            "provisions giving one party the power to change, override, or decide key contract terms without needing the other side's agreement, or where silence is treated as consent",

            # === TERMINATION RISKS ===
            "provisions allowing a party to end the contract without needing to show wrongdoing, including short or no notice requirements",
            "clauses defining what counts as a serious enough breach to end the contract, how much time is given to fix it, and which obligations continue once the contract ends",

            # === AUTO-RENEWAL TRAPS ===
            "clauses that renew the contract automatically unless a party opts out within a narrow window, especially where the renewal notice deadline is easy to miss",

            # === PAYMENT RISKS ===
            "payment conditions that depend on external approvals, disputed performance, or unilateral judgment calls, creating uncertainty about whether or when payment will occur",
            "clauses that allow previously paid money to be reclaimed, or that let one party adjust prices or costs without the other side's agreement",

            # === IP OWNERSHIP ===
            "clauses that transfer ownership of creative work, inventions, or developed materials to the other party, or grant broad, permanent usage rights without ongoing compensation",
            "clauses determining who owns data generated or processed during the contract, and risks from incorporating open-source components that could restrict future use or commercialization",

            # === CONFIDENTIALITY ISSUES ===
            "obligations to keep information secret, including how long those obligations last after the contract ends, what information is covered, and the consequences of disclosure",

            # === DATA & PRIVACY RISKS ===
            "requirements for how personal data is collected, processed, stored, or deleted, and who is responsible if a data breach occurs",

            # === JURISDICTION / DISPUTE RESOLUTION ===
            "provisions requiring disputes to be resolved through arbitration or in a specific location, or that limit a party's ability to bring or join legal action",

            # === REGULATORY & COMPLIANCE EXPOSURE ===
            "obligations to comply with anti-bribery, sanctions, export control, or other regulatory requirements that go beyond the core subject matter of the contract",

            # === EXCLUSIVITY & NON-COMPETE ===
            "restrictions that prevent a party from working with competitors, soliciting employees, or offering similar goods or services during or after the contract",

            # === WARRANTY DISCLAIMERS ===
            "language disclaiming standard warranties or limiting remedies for defective performance, including 'as-is' provisions or unusually short warranty periods",

            # === FORCE MAJEURE ABUSE ===
            "provisions excusing a party from performance due to external events, including how broadly those events are defined and whether they could be used to avoid normal obligations",

            # === UNFAIR OBLIGATIONS & TIMELINES ===
            "performance obligations described in vague or subjective terms, or deadlines and service levels that are difficult to meet and carry financial consequences if missed",

            # === AUDIT & RECORDS ===
            "rights allowing one party to examine the other's financial records or operational data, including how long that access continues after the contract ends",

            # === CONTRADICTORY / INCONSISTENT CLAUSES ===
            "sections of the contract that appear to conflict with each other, or language stating that one clause overrides others without clearly resolving the inconsistency",

            # === MANIPULATIVE / BOILERPLATE LEGAL WORDING ===
            "standard-looking boilerplate language that, on closer reading, significantly shifts risk, removes recourse, or creates obligations disproportionate to the purpose of the contract",

            # === FUNDING & DONOR COMPLIANCE ===
            "situations where the contract's obligations or payments depend on external funding, such as a grant or government award, that may not materialize or could be reduced or withdrawn",
            "additional reporting, audit, cost-allowability, or procurement compliance obligations imposed because the contract is funded by a grant, donor, or government program, including requirements that flow down from the original funding source",
        ]
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
        response = llm.invoke(llm_prompt)
    except Exception as e:
        raise RuntimeError(f'Error occurred during risk report generation\nError: {e}')
    return response.content


