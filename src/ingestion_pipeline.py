from typing import List

from langchain_core.documents import Document
from unstructured.partition.pdf import partition_pdf
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from pathlib import Path
from dotenv import load_dotenv
from models import get_embedding_model
from structure_builder import build_structure

load_dotenv()

mainPath = Path(__file__).resolve().parent.parent
defaultDBPath = mainPath / 'db/faiss_db'
defaultChunksPath = mainPath / 'db' / 'chunks.pkl'
defaultDocsPath = mainPath / 'docs' / 'SampleContract.pdf'
embedding_model = get_embedding_model()

def unstructured_load_documents(dir):
    elements = partition_pdf(filename=dir, strategy='hi_res', infer_table_structure=True,extract_images_in_pdf=True,skip_infer_table_types=[],extract_image_block_types=['Table'],extract_image_block_to_payload=True)
    return elements


def create_chunks(structure, max_words=400):
    chunks: List[Document] = []
    short_chunks = ''

    for sec in structure:
        title = sec["title"]
        body = sec["body"]
        clauses = sec["clauses"]
        page = sec['page']
        tables = sec.get('tables', None)

        current_chunk = f"SECTION: {title}\n"
        word_count = len(current_chunk.split())

        for b in body:
            if word_count + len(b.split()) > max_words:
                previous_chunk: Document | None = chunks[-1].metadata.get('chunk_id') if len(chunks) > 0  else None
                new_chunk = Document(short_chunks + current_chunk.strip(), metadata={'chunk_id': len(chunks), 'title': title, 'tables': tables, 'page': page, 'previous_chunk_id': previous_chunk})
                if len(chunks) > 0:
                    chunks[-1].metadata['next_chunk_id'] = new_chunk.metadata.get('chunk_id')
                chunks.append(new_chunk)
                current_chunk = f"SECTION: {title}\n"
                word_count = len(current_chunk.split())
                short_chunks = ''

            current_chunk += b + "\n"
            word_count += len(b.split())

        for c in clauses:
            if word_count + len(c.split()) > max_words:
                previous_chunk: Document | None = chunks[-1].metadata.get('chunk_id') if len(chunks) > 0  else None
                new_chunk = Document(short_chunks + current_chunk.strip(), metadata={'chunk_id': len(chunks), 'title': title, 'tables': tables, 'page': page, 'previous_chunk_id': previous_chunk})
                if len(chunks) > 0:
                    chunks[-1].metadata['next_chunk_id'] = new_chunk.metadata.get('chunk_id')
                chunks.append(new_chunk)
                current_chunk = f"SECTION: {title} (cont.)\n"
                word_count = len(current_chunk.split())
                short_chunks = ''
            current_chunk += "CLAUSE: " + c + "\n"
            word_count += len(c.split())

        if not (len(current_chunk.strip().split()) < 15):
            previous_chunk: Document | None = chunks[-1].metadata.get('chunk_id') if len(chunks) > 0 else None
            new_chunk = Document(short_chunks + current_chunk.strip(), metadata={'chunk_id': len(chunks), 'title': title, 'tables': tables, 'page': page, 'previous_chunk_id': previous_chunk})
            if len(chunks) > 0:
                chunks[-1].metadata['next_chunk_id'] = new_chunk.metadata.get('chunk_id')
            chunks.append(new_chunk)
            short_chunks = ''
        else:
            short_chunks += (current_chunk.strip() + '\n')

    return chunks

def chunk_contract(path):
    elements = unstructured_load_documents(path)
    structure = build_structure(elements)
    chunks = create_chunks(structure)
    for c in chunks:
        print('-----------------------')
        print(c)
        print('-----------------------')
    return chunks

def create_vector_store(chunks):
    vectorbase = FAISS.from_documents(documents=chunks, embedding=embedding_model)
    return vectorbase
