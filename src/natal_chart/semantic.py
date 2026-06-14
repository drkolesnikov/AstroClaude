from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np

VECTOR_DIMENSIONS = 128
SEMANTIC_MODEL_NAME = "local-semantic-lsa-v1"
MAX_LSA_FEATURES = 768
LSA_DIMENSIONS = 96
CONCEPT_WEIGHT = 4.0
LSA_WEIGHT = 1.0

CONCEPT_PROFILES: dict[str, dict[str, float]] = {
    "shadow": {
        "shadow": 2.0,
        "disowned": 2.1,
        "rejected": 1.8,
        "inferior": 1.6,
        "complex": 1.2,
        "hidden": 1.7,
        "repressed": 1.9,
        "banished": 2.2,
        "basement": 1.7,
        "cellar": 1.7,
        "twin": 1.5,
        "double": 1.8,
        "forbidden": 1.8,
        "unlived": 2.0,
        "refused": 2.0,
        "anger": 1.2,
        "sealed": 0.9,
        "door": 0.7,
        "stranger": 1.1,
        "unwanted": 1.8,
    },
    "saturn_boundary": {
        "saturn": 2.2,
        "boundary": 2.0,
        "authority": 1.8,
        "discipline": 1.8,
        "necessity": 1.8,
        "fear": 1.4,
        "law": 1.3,
        "time": 1.3,
        "limit": 1.5,
        "gate": 1.3,
    },
    "eros": {
        "eros": 2.2,
        "desire": 2.0,
        "beloved": 1.9,
        "appetite": 1.5,
        "union": 1.7,
        "intimacy": 1.8,
        "longing": 1.9,
        "venus": 1.5,
        "mars": 1.2,
        "beauty": 1.3,
        "relational": 1.4,
    },
    "vocation": {
        "vocation": 2.2,
        "calling": 2.0,
        "daimon": 2.0,
        "telos": 1.8,
        "destiny": 1.8,
        "craft": 1.4,
        "work": 1.2,
        "task": 1.4,
        "public": 1.1,
        "becoming": 1.3,
    },
    "wound": {
        "wound": 2.2,
        "chiron": 2.0,
        "medicine": 1.7,
        "healing": 1.7,
        "scar": 1.6,
        "pain": 1.3,
        "symptom": 1.2,
        "teacher": 1.2,
    },
    "persona": {
        "persona": 2.2,
        "mask": 1.9,
        "role": 1.5,
        "adaptation": 1.7,
        "social": 1.2,
        "appearance": 1.2,
        "performance": 1.2,
    },
    "ego": {
        "ego": 2.0,
        "identity": 1.6,
        "center": 1.2,
        "will": 1.3,
        "agency": 1.5,
        "consciousness": 1.4,
        "adaptation": 1.1,
    },
    "parental": {
        "parental": 2.0,
        "mother": 1.8,
        "father": 1.8,
        "imago": 1.9,
        "ancestral": 1.5,
        "family": 1.4,
        "authority": 1.2,
        "care": 1.1,
    },
    "anima_animus": {
        "anima": 2.1,
        "animus": 2.1,
        "soul": 1.6,
        "inner": 1.2,
        "feminine": 1.6,
        "masculine": 1.6,
        "image": 1.1,
        "other": 1.1,
    },
    "numinous": {
        "numinous": 2.2,
        "god": 1.7,
        "gods": 1.7,
        "sacred": 1.8,
        "awe": 1.7,
        "transcendent": 1.7,
        "mystery": 1.5,
        "divine": 1.7,
    },
    "amplification": {
        "amplification": 2.0,
        "myth": 1.8,
        "fairy": 1.7,
        "tale": 1.4,
        "alchemy": 1.9,
        "alchemical": 1.9,
        "nigredo": 2.0,
        "underworld": 1.8,
        "descent": 1.6,
        "parallel": 1.2,
        "symbolic": 1.3,
    },
    "literal_noise": {
        "technical": 1.6,
        "dictionary": 1.8,
        "definition": 1.8,
        "literal": 1.7,
        "object": 1.2,
        "cast": 1.2,
        "ballots": 1.6,
        "discarded": 1.4,
        "goods": 1.5,
        "category": 1.3,
        "keyword": 1.3,
    },
}


@dataclass(frozen=True)
class SemanticEmbeddingModel:
    name: str
    dimensions: int
    concept_order: tuple[str, ...]
    concept_profiles: dict[str, dict[str, float]]
    vocabulary: tuple[str, ...]
    idf: tuple[float, ...]
    components: tuple[tuple[float, ...], ...]


def build_semantic_index(texts: list[str]) -> tuple[SemanticEmbeddingModel, list[list[float]], dict[str, float]]:
    tokenized = [_tokens(text) for text in texts]
    idf_weights = _idf_weights(tokenized)
    vocabulary = _select_vocabulary(idf_weights, tokenized)
    idf = tuple(idf_weights[term] for term in vocabulary)
    components = _fit_lsa_components(tokenized, vocabulary, idf)
    model = SemanticEmbeddingModel(
        name=SEMANTIC_MODEL_NAME,
        dimensions=VECTOR_DIMENSIONS,
        concept_order=tuple(CONCEPT_PROFILES),
        concept_profiles=CONCEPT_PROFILES,
        vocabulary=tuple(vocabulary),
        idf=idf,
        components=components,
    )
    return model, [embed_tokens(tokens, model) for tokens in tokenized], idf_weights


def embed_text(text: str, model: SemanticEmbeddingModel) -> list[float]:
    return embed_tokens(_tokens(text), model)


def embed_tokens(tokens: list[str], model: SemanticEmbeddingModel) -> list[float]:
    vector = np.zeros(model.dimensions, dtype=np.float64)
    concept_values = _concept_vector(tokens, model)
    concept_size = min(len(concept_values), model.dimensions)
    vector[:concept_size] = concept_values[:concept_size] * CONCEPT_WEIGHT

    lsa_values = _lsa_vector(tokens, model)
    lsa_start = concept_size
    lsa_size = min(len(lsa_values), model.dimensions - lsa_start)
    if lsa_size > 0:
        vector[lsa_start : lsa_start + lsa_size] = lsa_values[:lsa_size] * LSA_WEIGHT

    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return [0.0] * model.dimensions
    return [round(float(value / norm), 8) for value in vector]


def model_to_payload(model: SemanticEmbeddingModel) -> dict[str, Any]:
    return {
        "name": model.name,
        "dimensions": model.dimensions,
        "concept_order": list(model.concept_order),
        "concept_profiles": model.concept_profiles,
        "vocabulary": list(model.vocabulary),
        "idf": list(model.idf),
        "components": [list(row) for row in model.components],
    }


def model_from_payload(payload: dict[str, Any]) -> SemanticEmbeddingModel:
    return SemanticEmbeddingModel(
        name=payload["name"],
        dimensions=payload["dimensions"],
        concept_order=tuple(payload["concept_order"]),
        concept_profiles={
            concept: {term: float(weight) for term, weight in profile.items()}
            for concept, profile in payload["concept_profiles"].items()
        },
        vocabulary=tuple(payload["vocabulary"]),
        idf=tuple(float(value) for value in payload["idf"]),
        components=tuple(tuple(float(value) for value in row) for row in payload["components"]),
    )


def _concept_vector(tokens: list[str], model: SemanticEmbeddingModel) -> np.ndarray:
    counts = Counter(tokens)
    values = []
    for concept in model.concept_order:
        profile = model.concept_profiles[concept]
        score = 0.0
        for token, count in counts.items():
            if token in profile:
                score += (1 + math.log(count)) * profile[token]
        values.append(score)
    return np.array(values, dtype=np.float64)


def _lsa_vector(tokens: list[str], model: SemanticEmbeddingModel) -> np.ndarray:
    if not model.vocabulary or not model.components:
        return np.array([], dtype=np.float64)
    vector = _tfidf_vector(tokens, model.vocabulary, model.idf)
    components = np.array(model.components, dtype=np.float64)
    return vector @ components.T


def _fit_lsa_components(
    tokenized: list[list[str]],
    vocabulary: list[str],
    idf: tuple[float, ...],
) -> tuple[tuple[float, ...], ...]:
    if not tokenized or not vocabulary:
        return ()
    matrix = np.vstack([_tfidf_vector(tokens, vocabulary, idf) for tokens in tokenized])
    rank = min(matrix.shape)
    target_dimensions = min(LSA_DIMENSIONS, VECTOR_DIMENSIONS - len(CONCEPT_PROFILES), rank)
    if target_dimensions <= 0:
        return ()

    if rank <= target_dimensions + 8:
        _, _, vt = np.linalg.svd(matrix, full_matrices=False)
    else:
        rng = np.random.default_rng(17)
        sketch_dimensions = min(rank, target_dimensions + 16)
        omega = rng.normal(size=(matrix.shape[1], sketch_dimensions))
        sketch = matrix @ omega
        q, _ = np.linalg.qr(sketch, mode="reduced")
        compressed = q.T @ matrix
        _, _, vt = np.linalg.svd(compressed, full_matrices=False)

    return tuple(
        tuple(round(float(value), 8) for value in row)
        for row in vt[:target_dimensions]
    )


def _tfidf_vector(tokens: list[str], vocabulary: tuple[str, ...] | list[str], idf: tuple[float, ...]) -> np.ndarray:
    index_by_term = {term: index for index, term in enumerate(vocabulary)}
    counts = Counter(tokens)
    vector = np.zeros(len(vocabulary), dtype=np.float64)
    for token, count in counts.items():
        index = index_by_term.get(token)
        if index is not None:
            vector[index] = (1 + math.log(count)) * idf[index]
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return vector
    return vector / norm


def _select_vocabulary(idf_weights: dict[str, float], tokenized: list[list[str]]) -> list[str]:
    if not idf_weights:
        return []
    document_frequencies = Counter()
    for tokens in tokenized:
        document_frequencies.update(set(tokens))

    concept_terms = {
        term
        for profile in CONCEPT_PROFILES.values()
        for term in profile
        if term in idf_weights
    }
    ranked_terms = sorted(
        idf_weights,
        key=lambda term: (-(document_frequencies[term] * idf_weights[term]), term),
    )
    selected = list(concept_terms)
    for term in ranked_terms:
        if term in concept_terms:
            continue
        selected.append(term)
        if len(selected) >= MAX_LSA_FEATURES:
            break
    return sorted(selected[:MAX_LSA_FEATURES])


def _idf_weights(tokenized: list[list[str]]) -> dict[str, float]:
    if not tokenized:
        return {}
    document_count = len(tokenized)
    document_frequencies = Counter()
    for tokens in tokenized:
        document_frequencies.update(set(tokens))
    return {
        token: round(math.log((document_count + 1) / (frequency + 1)) + 1, 8)
        for token, frequency in document_frequencies.items()
    }


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())
