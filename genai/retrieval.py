import os
import re
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeChunk:
    """Represents a chunk of text extracted from the knowledge base."""

    def __init__(self, chunk_id: str, title: str, category: str, fault_tag: str,
                 source_file: str, text: str):
        self.chunk_id = chunk_id
        self.title = title
        self.category = category
        self.fault_tag = fault_tag
        self.source_file = source_file
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "title": self.title,
            "category": self.category,
            "fault_tag": self.fault_tag,
            "source_file": self.source_file,
            "text": self.text,
        }


class KnowledgeBaseLoader:
    """Loads and chunks knowledge base markdown files."""

    def __init__(self, kb_dir: str = "knowledge_base"):
        self.kb_dir = kb_dir

    def load_all_chunks(self) -> List[KnowledgeChunk]:
        chunks: List[KnowledgeChunk] = []
        if not os.path.exists(self.kb_dir):
            return chunks

        for root, _, files in os.walk(self.kb_dir):
            category = os.path.basename(root)
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.kb_dir)
                    fault_tag = file.replace(".md", "")
                    doc_chunks = self._chunk_file(file_path, category, fault_tag, rel_path)
                    chunks.extend(doc_chunks)

        return chunks

    def _chunk_file(self, file_path: str, category: str, fault_tag: str, rel_path: str) -> List[KnowledgeChunk]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        doc_title = fault_tag.replace("_", " ").title()
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            doc_title = title_match.group(1).strip()

        sections = re.split(r"\n(?=##\s+)", content)
        chunks = []

        for idx, sec in enumerate(sections):
            sec_text = sec.strip()
            if not sec_text:
                continue

            sec_title = doc_title
            sec_title_match = re.search(r"^##?\s+(.+)$", sec_text, re.MULTILINE)
            if sec_title_match:
                sec_title = f"{doc_title} — {sec_title_match.group(1).strip()}"

            chunk_id = f"{fault_tag}_sec_{idx+1}"
            chunks.append(KnowledgeChunk(
                chunk_id=chunk_id,
                title=sec_title,
                category=category,
                fault_tag=fault_tag,
                source_file=rel_path,
                text=sec_text
            ))

        return chunks


class VectorStore:
    """Local vector store index using TF-IDF and Cosine Similarity."""

    def __init__(self, index_file: str = os.path.join("vector_store", "kb_index.pkl")):
        self.index_file = index_file
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[np.ndarray] = None
        self.chunks: List[KnowledgeChunk] = []

    def build_index(self, chunks: List[KnowledgeChunk]):
        self.chunks = chunks
        if not chunks:
            return

        texts = [f"{c.title}\n{c.category}\n{c.fault_tag}\n{c.text}" for c in chunks]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english"
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)

        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
        with open(self.index_file, "wb") as f:
            pickle.dump({"vectorizer": self.vectorizer, "tfidf_matrix": self.tfidf_matrix, "chunks": self.chunks}, f)

    def load_index(self) -> bool:
        if not os.path.exists(self.index_file):
            return False
        try:
            with open(self.index_file, "rb") as f:
                data = pickle.load(f)
                self.vectorizer = data["vectorizer"]
                self.tfidf_matrix = data["tfidf_matrix"]
                self.chunks = data["chunks"]
            return True
        except Exception:
            return False

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.vectorizer or self.tfidf_matrix is None or not self.chunks:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            chunk = self.chunks[idx]
            res_dict = chunk.to_dict()
            res_dict["relevance_score"] = round(score, 4)
            results.append(res_dict)

        return results


class MaintenanceRetriever:
    """Main retriever service for RAG integration."""

    def __init__(self, kb_dir: str = "knowledge_base", index_file: str = os.path.join("vector_store", "kb_index.pkl")):
        self.kb_loader = KnowledgeBaseLoader(kb_dir=kb_dir)
        self.vector_store = VectorStore(index_file=index_file)
        self._initialize_store()

    def _initialize_store(self):
        if not self.vector_store.load_index():
            chunks = self.kb_loader.load_all_chunks()
            self.vector_store.build_index(chunks)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return self.vector_store.search(query, top_k=top_k)

    def retrieve_for_prediction(self, normalized_pred: Dict[str, Any], top_k: int = 3) -> List[Dict[str, Any]]:
        from genai.adapter import PredictionAdapter
        query = PredictionAdapter.build_search_query(normalized_pred)
        return self.retrieve(query, top_k=top_k)
