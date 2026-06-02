"""Chunking, embedding, and retrieval for source-grounded study content."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import re
from typing import Any, Protocol
from uuid import uuid4


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True, slots=True)
class SourceChunk:
    id: str
    text: str
    source_name: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchResult:
    chunk: SourceChunk
    score: float


class Embedder(Protocol):
    model_name: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


def chunk_text(
    text: str,
    source_name: str,
    *,
    chunk_size: int = 180,
    overlap: int = 35,
) -> list[SourceChunk]:
    """Split text into overlapping word chunks for semantic search."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if overlap < 0:
        raise ValueError("overlap cannot be negative.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    words = re.findall(r"\S+", text)
    if not words:
        return []

    chunks: list[SourceChunk] = []
    step = chunk_size - overlap
    for chunk_index, start in enumerate(range(0, len(words), step)):
        chunk_words = words[start : start + chunk_size]
        if not chunk_words:
            break

        chunk = SourceChunk(
            id=f"{_stable_id(source_name)}-{chunk_index}",
            text=" ".join(chunk_words),
            source_name=source_name,
            chunk_index=chunk_index,
            metadata={"start_word": start, "word_count": len(chunk_words)},
        )
        chunks.append(chunk)

        if start + chunk_size >= len(words):
            break

    return chunks


class MiniLMEmbedder:
    """Local sentence-transformers embedder used by the intended pipeline."""

    model_name = DEFAULT_EMBEDDING_MODEL

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed. Install requirements.txt "
                    "or use HashingEmbedder for local fallback."
                ) from exc
            self._model = SentenceTransformer(self.model_name)

        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return [embedding.tolist() for embedding in embeddings]


class HashingEmbedder:
    """Dependency-free fallback embedder for tests and offline demos."""

    def __init__(self, dimensions: int = 384) -> None:
        self.model_name = f"hashing-fallback-{dimensions}"
        self.dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = _tokens(text)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector


class InMemoryVectorStore:
    """Small cosine-similarity store used when ChromaDB is unavailable."""

    backend_name = "in-memory"

    def __init__(self, embedder: Embedder | None = None) -> None:
        self.embedder = embedder or HashingEmbedder()
        self._chunks: list[SourceChunk] = []
        self._embeddings: list[list[float]] = []

    def add_chunks(self, chunks: list[SourceChunk]) -> None:
        if not chunks:
            return
        self._chunks.extend(chunks)
        self._embeddings.extend(self.embedder.embed_texts([chunk.text for chunk in chunks]))

    def query(self, query_text: str, *, limit: int = 5) -> list[SearchResult]:
        if not self._chunks:
            return []

        query_embedding = self.embedder.embed_texts([query_text])[0]
        scored = [
            SearchResult(chunk=chunk, score=_cosine_similarity(query_embedding, embedding))
            for chunk, embedding in zip(self._chunks, self._embeddings, strict=True)
        ]
        return sorted(scored, key=lambda result: result.score, reverse=True)[:limit]


class ChromaVectorStore:
    """ChromaDB-backed vector store for the intended app pipeline."""

    backend_name = "chromadb"

    def __init__(
        self,
        *,
        collection_name: str | None = None,
        persist_path: str = ".chroma",
        embedder: Embedder | None = None,
    ) -> None:
        self.embedder = embedder or MiniLMEmbedder()
        self.collection_name = collection_name or f"study-assistant-{uuid4().hex[:10]}"
        self.persist_path = persist_path

        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "chromadb is not installed. Install requirements.txt or use InMemoryVectorStore."
            ) from exc

        self._client = chromadb.PersistentClient(path=persist_path)
        self._collection = self._client.get_or_create_collection(name=self.collection_name)

    def add_chunks(self, chunks: list[SourceChunk]) -> None:
        if not chunks:
            return

        embeddings = self.embedder.embed_texts([chunk.text for chunk in chunks])
        self._collection.add(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[_to_chroma_metadata(chunk) for chunk in chunks],
        )

    def query(self, query_text: str, *, limit: int = 5) -> list[SearchResult]:
        query_embedding = self.embedder.embed_texts([query_text])[0]
        response = self._collection.query(query_embeddings=[query_embedding], n_results=limit)

        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]

        results: list[SearchResult] = []
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            source_name = str(metadata.get("source_name", "source"))
            chunk_index = int(metadata.get("chunk_index", 0))
            chunk = SourceChunk(
                id=chunk_id,
                text=document,
                source_name=source_name,
                chunk_index=chunk_index,
                metadata={key: value for key, value in metadata.items() if key not in {"source_name", "chunk_index"}},
            )
            score = 1.0 / (1.0 + float(distance))
            results.append(SearchResult(chunk=chunk, score=score))

        return results


def build_index(
    text: str,
    source_name: str,
    *,
    query_hint: str = "",
    chunk_size: int = 180,
    overlap: int = 35,
    prefer_chroma: bool = True,
    persist_path: str = ".chroma",
) -> tuple[InMemoryVectorStore | ChromaVectorStore, list[SourceChunk], list[str]]:
    chunks = chunk_text(text, source_name, chunk_size=chunk_size, overlap=overlap)
    warnings: list[str] = []

    store: InMemoryVectorStore | ChromaVectorStore
    if prefer_chroma:
        try:
            store = ChromaVectorStore(persist_path=persist_path)
        except RuntimeError as exc:
            warnings.append(str(exc))
            store = InMemoryVectorStore()
    else:
        store = InMemoryVectorStore()

    try:
        store.add_chunks(chunks)
        if query_hint and chunks:
            store.query(query_hint, limit=1)
    except Exception as exc:
        if not isinstance(store, ChromaVectorStore):
            raise
        warnings.append(f"Chroma pipeline failed, using in-memory fallback: {exc}")
        store = InMemoryVectorStore()
        store.add_chunks(chunks)

    return store, chunks, warnings


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _to_chroma_metadata(chunk: SourceChunk) -> dict[str, str | int | float | bool]:
    metadata: dict[str, str | int | float | bool] = {
        "source_name": chunk.source_name,
        "chunk_index": chunk.chunk_index,
    }
    for key, value in chunk.metadata.items():
        if isinstance(value, str | int | float | bool):
            metadata[key] = value
    return metadata
