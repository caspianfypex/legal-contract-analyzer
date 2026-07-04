import re
from typing import List

from langchain_core.messages import HumanMessage
from unstructured.documents.elements import Element
from models import get_vision_model
from prompts import vision_prompt

ARTICLE_PATTERN = re.compile(
    r"^(ARTICLE|Article)\s+([IVXLC]+|\d+)\b"
)

TOP_LEVEL_SECTION_PATTERN = re.compile(
    r"^\d+\.\s+[A-Z]"
)

CLAUSE_PATTERN = re.compile(
    r"^\d+\.\d+(\.\d+)*\b"
)

SUBCLAUSE_PATTERN = re.compile(
    r"^(\([a-zA-Z]\)|\(\d+\)|\([ivxIVX]+\))\s*"
)

def is_article(text:str):
    return bool(ARTICLE_PATTERN.match(text.strip()))

def is_top_section(text:str):
    return bool(TOP_LEVEL_SECTION_PATTERN.match(text.strip()))

def is_clause(text:str):
    return bool(CLAUSE_PATTERN.match(text.strip()))

def is_subclause(text:str):
    return bool(SUBCLAUSE_PATTERN.match(text.strip()))

def clean(text:str):
    return " ".join(text.split()).strip()

def is_footer(text:str):
    text = text.strip()
    return bool(re.match(r"(?i)^page\s+\d+(\s+of\s+\d+)?$", text))

def build_structure(elements: List[Element]):
    structure = []
    current_section = None
    current_clause = None
    llm = get_vision_model()

    for el in elements:
        text = clean(el.text)
        category = getattr(el, "category", "")

        if is_footer(text) or not text:
            continue
        elif is_article(text) or is_top_section(text) or category == 'Title':
            current_section = {
                "title": text,
                "body": [],
                "clauses": [],
                "page": getattr(el.metadata, 'page_number', -1),
                "tables": []
            }
            structure.append(current_section)
            current_clause = None
            continue

        elif is_clause(text):

            if current_section:
                current_clause = text
                current_section["clauses"].append(current_clause)
            continue

        elif is_subclause(text):
            if current_clause:
                current_clause += " " + text
                current_section["clauses"][-1] = current_clause
                continue

        if current_clause:
            current_clause += " " + text
            current_section["clauses"][-1] = current_clause
        elif current_section:
            # if category == 'Table':
            #     message = HumanMessage(
            #         content=[
            #             {"type": "text", "text": vision_prompt},
            #             {
            #                 "type": "image_url",
            #                 "image_url": f"data:image/jpeg;base64,{el.metadata.image_base64}",
            #             },
            #         ]
            #     )
            #     response = llm.invoke([message])
            #     print(response.embedding_text)
            #     current_section["body"].append(response.embedding_text)
            #     current_section['tables'].append(response.structured_json)
            # else:
             current_section['body'].append(text)
        else:
            if category != 'Table':
                structure.append({
                    "title": "UNKNOWN",
                    "body": [text],
                    "clauses": [],
                    "page": getattr(getattr(el, 'metadata'), 'page_number', -1)
                })
            # else:
            #     message = HumanMessage(
            #         content=[
            #             {"type": "text", "text": vision_prompt},
            #             {
            #                 "type": "image_url",
            #                 "image_url": f"data:image/jpeg;base64,{el.metadata.image_base64}",
            #             },
            #         ]
            #     )
            #     response = llm.invoke([message])
            #     structure.append({
            #         "title": "UNKNOWN",
            #         "body": [response.embedding_text],
            #         "clauses": [],
            #         "page": getattr(getattr(el, 'metadata'), 'page_number', -1),
            #         "tables": [response.structured_json]
            #     })

    return structure