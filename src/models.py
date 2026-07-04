import torch.cuda
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

class VisionResponse(BaseModel):
    embedding_text: str
    structured_json: str

embedding_model = None
llm = None
hf_cross_encoder = None
vision_model = None
structured_vision_model = None

def get_embedding_model():
    global embedding_model

    if not embedding_model:
        embedding_model = HuggingFaceEmbeddings(model_name='Qwen/Qwen3-Embedding-4B', model_kwargs={'device': 'cuda'}, encode_kwargs={'normalize_embeddings': True}) if torch.cuda.is_available() else HuggingFaceEmbeddings(model_name='Qwen/Qwen3-Embedding-4B', encode_kwargs={'normalize_embeddings': True})
    return embedding_model

def get_llm_model():
    global llm

    if not llm:
        llm = ChatGroq(model='openai/gpt-oss-120b', temperature=0)
    return llm

def get_reranker_model():
    global hf_cross_encoder

    if not hf_cross_encoder:
        hf_cross_encoder = HuggingFaceCrossEncoder(model_name='BAAI/bge-reranker-v2-m3', model_kwargs={"device": "cuda"}) if torch.cuda.is_available() else HuggingFaceCrossEncoder(model_name='BAAI/bge-reranker-v2-m3')

    return hf_cross_encoder

def get_vision_model():
    global vision_model
    global structured_vision_model

    if not vision_model:
        vision_model = ChatGoogleGenerativeAI(model='gemini-2.5-flash', temperature=0)
        structured_vision_model = vision_model.with_structured_output(VisionResponse)
    return structured_vision_model
