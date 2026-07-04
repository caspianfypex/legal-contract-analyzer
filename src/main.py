import asyncio
import os
from fastapi import FastAPI, UploadFile, File
import tempfile
import ingestion_pipeline
import retrieval_pipeline

app = FastAPI()

def run_pipeline(docspath):
    try:
        chunks = ingestion_pipeline.chunk_contract(docspath)
        db = ingestion_pipeline.create_vector_store(chunks)
        response = retrieval_pipeline.process_query(db, chunks)
        os.remove(docspath)
        return db,response
    except Exception as e:
        print(f'Error occured: {e}')
        return None,None

@app.post('/upload_pdf')
async def upload_pdf(file: UploadFile = File()):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
         content = await file.read()
         tmp.write(content)
         tmp_path = tmp.name

    response = await asyncio.to_thread(run_pipeline, tmp_path)
    print(response[1])
    return {'content': response[1]}
