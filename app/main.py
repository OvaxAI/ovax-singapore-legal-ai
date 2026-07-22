from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "singapore_company_law_demo.json"

app = FastAPI(
    title="OVAX Singapore Company Law AI",
    version="0.1.0",
    description=(
        "Runnable MVP for retrieval-based answers about Singapore company law. "
        "Demo data contains curated summaries and official source links."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this before production.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=8)


class SourceItem(BaseModel):
    title: str
    topic: str
    source_url: str
    official_source: str
    updated_at: str | None = None
    score: float


class AskResponse(BaseModel):
    answer: str
    mode: str
    sources: list[SourceItem]
    disclaimer: str


def load_documents() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        raise RuntimeError(f"Missing data file: {DATA_FILE}")
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


DOCUMENTS = load_documents()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def search_documents(question: str, top_k: int) -> list[dict[str, Any]]:
    query_tokens = set(tokenize(question))
    scored: list[tuple[float, dict[str, Any]]] = []

    for doc in DOCUMENTS:
        searchable = " ".join(
            [
                doc.get("title", ""),
                doc.get("topic", ""),
                doc.get("summary", ""),
                " ".join(doc.get("keywords", [])),
            ]
        )
        doc_tokens = set(tokenize(searchable))

        overlap = len(query_tokens & doc_tokens)
        phrase_bonus = 0.0
        question_lower = question.lower()
        for keyword in doc.get("keywords", []):
            if keyword.lower() in question_lower:
                phrase_bonus += 2.0

        score = float(overlap) + phrase_bonus
        if score > 0:
            item = dict(doc)
            item["_score"] = score
            scored.append((score, item))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:top_k]]


def build_context(results: list[dict[str, Any]]) -> str:
    blocks = []
    for index, doc in enumerate(results, start=1):
        blocks.append(
            f"""SOURCE {index}
Title: {doc['title']}
Topic: {doc['topic']}
Summary: {doc['summary']}
Official source: {doc['official_source']}
URL: {doc['source_url']}
Updated at: {doc.get('updated_at') or 'Not recorded'}
"""
        )
    return "\n".join(blocks)


def local_answer(question: str, results: list[dict[str, Any]]) -> str:
    if not results:
        return (
            "I could not find a relevant basis in the current demo dataset. "
            "The dataset is intentionally small and should not be used as a complete statement of Singapore law."
        )

    summaries = "\n\n".join(
        f"- {doc['summary']} [Source {index}]"
        for index, doc in enumerate(results, start=1)
    )
    return (
        "Based only on the current demo dataset:\n\n"
        f"{summaries}\n\n"
        "Please open the cited official sources and verify the current legislation, "
        "effective dates, exceptions, and facts of the specific case."
    )


def ai_answer(question: str, results: list[dict[str, Any]]) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None or not results:
        return None

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    instructions = """You are OVAX Singapore Company Law AI, a retrieval-only legal information assistant.

Rules:
1. Answer only from the supplied context.
2. Do not invent sections, duties, deadlines, penalties, or legal conclusions.
3. Cite claims using [Source 1], [Source 2], etc.
4. Clearly state when the supplied context is insufficient.
5. Distinguish legislation from regulator guidance.
6. Do not present the answer as legal advice.
7. Keep the answer concise and practical.
"""

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=f"QUESTION:\n{question}\n\nCONTEXT:\n{build_context(results)}",
    )
    return response.output_text.strip()


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "documents_loaded": len(DOCUMENTS),
        "openai_enabled": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/api/documents")
def documents() -> dict[str, Any]:
    safe_docs = [
        {
            "id": doc["id"],
            "title": doc["title"],
            "topic": doc["topic"],
            "official_source": doc["official_source"],
            "source_url": doc["source_url"],
            "updated_at": doc.get("updated_at"),
        }
        for doc in DOCUMENTS
    ]
    return {"count": len(safe_docs), "documents": safe_docs}


@app.post("/api/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    results = search_documents(payload.question, payload.top_k)

    try:
        generated = ai_answer(payload.question, results)
    except Exception as exc:
        # The API remains usable when the external model is unavailable.
        generated = None

    answer = generated or local_answer(payload.question, results)
    mode = "openai-rag" if generated else "local-retrieval"

    sources = [
        SourceItem(
            title=doc["title"],
            topic=doc["topic"],
            source_url=doc["source_url"],
            official_source=doc["official_source"],
            updated_at=doc.get("updated_at"),
            score=doc["_score"],
        )
        for doc in results
    ]

    return AskResponse(
        answer=answer,
        mode=mode,
        sources=sources,
        disclaimer=(
            "Demo legal information only. It is not legal advice. "
            "Verify the current text on Singapore Statutes Online or ACRA."
        ),
    )


from fastapi.staticfiles import StaticFiles

# Keep this mount last so API routes remain reachable.
app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")
