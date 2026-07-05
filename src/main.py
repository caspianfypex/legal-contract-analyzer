import asyncio
import os
from typing import Literal

from fastapi import FastAPI, UploadFile, File
import tempfile

import ingestion_pipeline
import retrieval_pipeline

app = FastAPI()
modes_dict = {'Low': 5, 'Standard': 15, 'High': 25, 'Ultra': 40}

def run_pipeline(docspath, context_query='', mode=Literal['Low', 'Standard', 'High', 'Ultra']):
    try:
        chunks = ingestion_pipeline.chunk_contract(docspath)
        db = ingestion_pipeline.create_vector_store(chunks)
        response = retrieval_pipeline.process_query(db=db, docs=chunks, n_chunks=modes_dict.get(mode, 15), user_query=context_query)
        os.remove(docspath)
        return db,response
    except Exception as e:
        print(f'Error occured: {e}')
        return None,None

@app.post('/upload_pdf')
async def upload_pdf(context_query = '', file: UploadFile = File(), mode=Literal['Low', 'Standard', 'High', 'Ultra']):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
         content = await file.read()
         tmp.write(content)
         tmp_path = tmp.name

    response = await asyncio.to_thread(run_pipeline, tmp_path, context_query, mode)
    print(response[1])
    return {'content': response[1]}
