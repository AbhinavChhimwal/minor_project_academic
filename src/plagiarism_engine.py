import sqlite3
import threading
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import DB_PATH
from .text_utils import split_into_chunks


class PlagiarismEngine:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self.vectorizer = HashingVectorizer(
            n_features=4096,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 3),
            lowercase=True,
        )
        self._init_db()

    def _init_db(self):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_name TEXT NOT NULL,
                    student_id TEXT,
                    assignment_no INTEGER,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
                """
            )

            # Backward-compatible migration for older DBs.
            docs_cols = {row[1] for row in cur.execute("PRAGMA table_info(documents)").fetchall()}
            if "student_id" not in docs_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN student_id TEXT")
            if "assignment_no" not in docs_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN assignment_no INTEGER")

            self.conn.commit()

    def list_documents(self):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT d.id, d.document_name, d.student_id, d.assignment_no, d.uploaded_at, COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN document_chunks c ON c.document_id = d.id
                GROUP BY d.id
                ORDER BY d.id DESC
                """
            )
            rows = cur.fetchall()
        # UI-friendly index that starts at 0.
        docs = []
        for idx, row in enumerate(rows):
            db_id = row[0]
            docs.append(
                {
                    "id": idx,  # display id starting at 0
                    "db_id": db_id,  # internal sqlite id (for deletion)
                    "document_name": row[1],
                    "student_id": row[2],
                    "assignment_no": row[3],
                    "uploaded_at": row[4],
                    "chunk_count": row[5],
                }
            )
        return docs

    def clear_database(self):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM document_chunks")
            cur.execute("DELETE FROM documents")
            self.conn.commit()

    def delete_document(self, db_id: int):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM documents WHERE id = ?", (int(db_id),))
            self.conn.commit()

    def delete_documents_by_assignment_no(self, assignment_no: int):
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM documents WHERE assignment_no = ?", (int(assignment_no),))
            self.conn.commit()

    def ingest_document(self, document_name: str, text: str, student_id: str | None, assignment_no: int | None):
        chunks = split_into_chunks(text)
        if not chunks:
            return {"chunks_added": 0}

        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO documents (document_name, student_id, assignment_no) VALUES (?, ?, ?)",
                (document_name, student_id, assignment_no),
            )
            document_id = cur.lastrowid
            cur.executemany(
                "INSERT INTO document_chunks (document_id, chunk_text) VALUES (?, ?)",
                [(document_id, chunk) for chunk in chunks],
            )
            self.conn.commit()
        return {"chunks_added": len(chunks), "document_id": document_id}

    def _get_corpus_chunks(self, corpus_assignment_no: int | None):
        with self.lock:
            cur = self.conn.cursor()
            if corpus_assignment_no is None:
                cur.execute(
                    """
                    SELECT c.id, c.chunk_text, d.document_name, d.student_id, d.assignment_no
                    FROM document_chunks c
                    JOIN documents d ON d.id = c.document_id
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT c.id, c.chunk_text, d.document_name, d.student_id, d.assignment_no
                    FROM document_chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE d.assignment_no = ?
                    """,
                    (corpus_assignment_no,),
                )
            rows = cur.fetchall()
        return [
            {
                "chunk_id": r[0],
                "chunk_text": r[1],
                "document_name": r[2],
                "student_id": r[3],
                "assignment_no": r[4],
            }
            for r in rows
        ]

    def check_plagiarism(
        self,
        text: str,
        threshold: float = 0.75,
        top_k: int = 15,
        corpus_assignment_no: int | None = None,
    ):
        query_chunks = split_into_chunks(text)
        if not query_chunks:
            return {
                "plagiarism_percent": 0.0,
                "total_chunks": 0,
                "matched_chunks": 0,
                "top_matches": [],
                "document_breakdown": [],
            }

        corpus = self._get_corpus_chunks(corpus_assignment_no=corpus_assignment_no)
        if not corpus:
            return {
                "plagiarism_percent": 0.0,
                "total_chunks": len(query_chunks),
                "matched_chunks": 0,
                "top_matches": [],
                "document_breakdown": [],
            }

        corpus_texts = [c["chunk_text"] for c in corpus]
        query_matrix = self.vectorizer.transform(query_chunks)
        corpus_matrix = self.vectorizer.transform(corpus_texts)
        similarity_matrix = cosine_similarity(query_matrix, corpus_matrix)

        matches = []
        matched_chunks = 0
        similarity_sum = 0.0
        by_document = {}  # key -> count

        for query_idx, query_chunk in enumerate(query_chunks):
            sims = similarity_matrix[query_idx]
            best_idx = int(np.argmax(sims))
            best_score = float(sims[best_idx])
            best_hit = corpus[best_idx]
            similarity_sum += best_score

            if best_score >= threshold:
                matched_chunks += 1
                key = (
                    best_hit["document_name"],
                    best_hit["student_id"],
                    best_hit["assignment_no"],
                )
                by_document.setdefault(key, 0)
                by_document[key] += 1

            matches.append(
                {
                    "query_chunk": query_chunk,
                    "matched_chunk": best_hit["chunk_text"],
                    "source_document": (
                        f"{best_hit['document_name']}"
                        f"{'' if not best_hit['student_id'] else f' (student: {best_hit['student_id']})'}"
                    ),
                    "source_student_id": best_hit["student_id"],
                    "source_assignment_no": best_hit["assignment_no"],
                    "similarity": best_score,
                    "is_flagged": best_score >= threshold,
                }
            )

        matches.sort(key=lambda x: x["similarity"], reverse=True)
        avg_similarity = similarity_sum / max(1, len(query_chunks))
        plagiarism_percent = max((matched_chunks / len(query_chunks)) * 100.0, avg_similarity * 100.0)

        breakdown = [
            {
                "source_document": doc_name,
                "source_student_id": student_id,
                "source_assignment_no": assign_no,
                "matched_chunks": count,
                "coverage_percent": (count / len(query_chunks)) * 100.0,
            }
            for (doc_name, student_id, assign_no), count in sorted(
                by_document.items(), key=lambda item: item[1], reverse=True
            )
        ]

        return {
            "plagiarism_percent": min(plagiarism_percent, 100.0),
            "total_chunks": len(query_chunks),
            "matched_chunks": matched_chunks,
            "top_matches": matches[:top_k],
            "document_breakdown": breakdown,
        }
