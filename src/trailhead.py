"""
trailhead.py — small, shared helpers for the Trailhead Copilot workshop.

The notebooks teach each concept step by step. This module holds the little bits of
reusable plumbing (finding data files, loading CSVs, a thin Claude wrapper, and the
embed/index/search helpers) so later notebooks don't have to re-type code students
have already seen. Everything here is intentionally short and commented, and every
function notes what students might customize for their own project.

Heavy dependencies (sentence-transformers, faiss, anthropic) are imported *inside*
the functions that need them, so importing this module just to load CSV data does not
require the ML libraries.
"""

from __future__ import annotations

import os
from pathlib import Path


# --- Locating the repo's data and documents ----------------------------------
def repo_root() -> Path:
    """Return the trailhead-copilot repo root, wherever the notebook runs from.

    Works whether the file lives at src/trailhead.py in a clone or was copied into
    a Colab session. Customize DATA/DOCS locations here if you restructure the repo.
    """
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "data").is_dir() and (parent / "documents").is_dir():
            return parent
    # Fallback: assume src/ is one level below the root.
    return here.parent.parent


DATA_DIR = repo_root() / "data"
MD_DIR = repo_root() / "documents" / "markdown"


# --- Configuration -----------------------------------------------------------
# The default model is Haiku 4.5: the cheapest Claude model, and more than capable
# for the Q&A, routing, and extraction tasks in this workshop. Switch to
# "claude-sonnet-5" or "claude-opus-4-8" for stronger reasoning at higher cost.
DEFAULT_MODEL = "claude-haiku-4-5"

# The local embedding model. Small, fast, free, and runs in Colab/Databricks with no
# extra API key. A larger model would improve retrieval quality at some speed cost.
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


# --- Loading the business data -----------------------------------------------
def load_data() -> dict:
    """Load every CSV in data/ into a dict of pandas DataFrames.

    Returns keys: customers, products, orders, order_items, inventory, shipments.
    """
    import pandas as pd

    names = ["customers", "products", "orders", "order_items", "inventory", "shipments"]
    return {name: pd.read_csv(DATA_DIR / f"{name}.csv") for name in names}


# --- Loading and chunking the knowledge documents ----------------------------
def load_documents() -> list[dict]:
    """Read every markdown file in documents/markdown/.

    Returns a list of {"source": <filename>, "text": <full text>} dicts.
    """
    docs = []
    for path in sorted(MD_DIR.glob("*.md")):
        docs.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
    return docs


def chunk_text(text: str, source: str, max_chars: int = 700) -> list[dict]:
    """Split a document into small, overlap-free chunks on paragraph boundaries.

    We keep chunks roughly paragraph-sized so each retrieved piece is focused. Tune
    `max_chars` up for fewer/larger chunks or down for more granular retrieval.
    Returns a list of {"source", "text"} dicts.
    """
    chunks, current = [], ""
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        # If adding this paragraph would overflow, flush the current chunk first.
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append({"source": source, "text": current.strip()})
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current.strip():
        chunks.append({"source": source, "text": current.strip()})
    return chunks


def build_chunks(max_chars: int = 700) -> list[dict]:
    """Convenience: load all documents and return one flat list of chunks."""
    chunks = []
    for doc in load_documents():
        chunks.extend(chunk_text(doc["text"], doc["source"], max_chars=max_chars))
    return chunks


# --- Embeddings + FAISS index ------------------------------------------------
def load_embedder():
    """Load the sentence-transformers embedding model (downloaded once, then cached)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL_NAME)


def build_index(chunks: list[dict], embedder=None):
    """Embed chunk texts and build a FAISS index for similarity search.

    Returns (index, embedder). We L2-normalize the vectors and use an inner-product
    index, which makes inner product equal to cosine similarity.
    """
    import faiss
    import numpy as np

    if embedder is None:
        embedder = load_embedder()
    vectors = embedder.encode([c["text"] for c in chunks], show_progress_bar=False)
    vectors = np.asarray(vectors, dtype="float32")
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index, embedder


def search(query: str, index, chunks: list[dict], embedder, top_k: int = 4) -> list[dict]:
    """Return the top_k most similar chunks to `query`, each with a similarity score."""
    import faiss
    import numpy as np

    q = embedder.encode([query])
    q = np.asarray(q, dtype="float32")
    faiss.normalize_L2(q)
    scores, indices = index.search(q, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        hit = dict(chunks[idx])
        hit["score"] = float(score)
        results.append(hit)
    return results


# --- Talking to Claude -------------------------------------------------------
def get_client():
    """Create an Anthropic client. Reads the key from the ANTHROPIC_API_KEY env var.

    Never hardcode your API key. In Colab we set the env var with getpass so the key
    isn't saved in the notebook.
    """
    import anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set it before calling Claude, e.g.:\n"
            "    import os, getpass\n"
            "    os.environ['ANTHROPIC_API_KEY'] = getpass.getpass('Anthropic API key: ')"
        )
    return anthropic.Anthropic()


def ask_claude(
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 512,
    client=None,
) -> str:
    """Send a single prompt to Claude and return the text of the reply.

    Keeps things simple for the workshop: one user message in, text out. `system`
    sets the assistant's role/instructions; `max_tokens` caps the reply length (and
    therefore cost). Raise `max_tokens` for longer answers.
    """
    client = client or get_client()
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    # Concatenate any text blocks in the response.
    return "".join(block.text for block in response.content if block.type == "text")
