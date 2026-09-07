from config import get_settings
import chromadb
from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
settings = get_settings()
CHROMA_PATH = (settings.resolved_data_dir / "chroma")
CHROMA_PATH.mkdir(parents=True, exist_ok=True)

_chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_PATH)
)

_collection = _chroma_client.get_or_create_collection(
    name="document_chunks",
    metadata={"hnsw:space": "cosine"},
)

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )

    return _embedding_model


def add_chunks(
    ids: list[str],
    texts: list[str],
    metadatas: list[dict],
):
    if not texts:
        return

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
    ).tolist()

    _collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search_chunks(
    query: str,
    top_k: int,
    where: dict | None = None,
) -> list[dict]:
    collection_size = _collection.count()

    if collection_size == 0:
        return []

    model = get_embedding_model()

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
    ).tolist()[0]

    query_arguments = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, collection_size),
        "include": [
            "documents",
            "metadatas",
            "distances",
        ],
    }

    if where:
        query_arguments["where"] = where

    results = _collection.query(**query_arguments)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    matches = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        matches.append(
            {
                "text": document,
                "metadata": metadata,
                "distance": float(distance),
                "retrieval_similarity": (
                    1.0 - float(distance)
                ),
            }
        )

    return matches

def get_chunks(
    where: dict,
) -> list[dict]:
    results = _collection.get(
        where=where,
        include=[
            "documents",
            "metadatas",
        ],
    )

    ids = results.get("ids") or []
    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []

    return [
        {
            "id": record_id,
            "text": document,
            "metadata": metadata,
        }
        for record_id, document, metadata in zip(
            ids,
            documents,
            metadatas,
        )
    ]