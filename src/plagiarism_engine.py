import re
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List

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

    def _get_corpus_documents(self, corpus_assignment_no: int | None):
        """Get full documents from corpus for new algorithm."""
        with self.lock:
            cur = self.conn.cursor()
            if corpus_assignment_no is None:
                cur.execute(
                    """
                    SELECT d.id, d.document_name, d.student_id, d.assignment_no
                    FROM documents d
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT d.id, d.document_name, d.student_id, d.assignment_no
                    FROM documents d
                    WHERE d.assignment_no = ?
                    """,
                    (corpus_assignment_no,),
                )
            docs = cur.fetchall()
        
        corpus_docs = []
        for doc_id, doc_name, student_id, assignment_no in docs:
            with self.lock:
                cur = self.conn.cursor()
                cur.execute(
                    """
                    SELECT GROUP_CONCAT(chunk_text, ' ')
                    FROM document_chunks
                    WHERE document_id = ?
                    """,
                    (doc_id,),
                )
                result = cur.fetchone()
                full_text = result[0] if result[0] else ""
            
            corpus_docs.append({
                "doc_id": doc_id,
                "document_name": doc_name,
                "student_id": student_id,
                "assignment_no": assignment_no,
                "text": full_text,
            })
        
        return corpus_docs

    @staticmethod
    def _jaccard_similarity(text1: str, text2: str) -> float:
        """Compute Jaccard similarity on tokens."""
        tokens1 = set(re.findall(r"\b\w+\b", text1.lower()))
        tokens2 = set(re.findall(r"\b\w+\b", text2.lower()))
        
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _lcs_length(seq1: List, seq2: List) -> int:
        """Compute length of longest common subsequence using DP."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        
        return dp[m][n]

    @staticmethod
    def _longest_common_ratio(text1: str, text2: str) -> float:
        """Compute ratio of longest common subsequence length to average text length."""
        words1 = re.findall(r"\b\w+\b", text1.lower())
        words2 = re.findall(r"\b\w+\b", text2.lower())
        
        if not words1 or not words2:
            return 1.0 if words1 == words2 else 0.0
        
        lcs_length = PlagiarismEngine._lcs_length(words1, words2)
        avg_length = (len(words1) + len(words2)) / 2
        
        return lcs_length / avg_length if avg_length > 0 else 0.0

    @staticmethod
    def _combined_similarity(text1: str, text2: str) -> float:
        """Combine Jaccard and LCS similarity with weights."""
        jaccard = PlagiarismEngine._jaccard_similarity(text1, text2)
        lcs = PlagiarismEngine._longest_common_ratio(text1, text2)
        return 0.6 * jaccard + 0.4 * lcs

    def check_plagiarism(
        self,
        text: str,
        threshold: float = 0.3,
        top_k: int = 15,
        corpus_assignment_no: int | None = None,
    ):
        """
        Check plagiarism using Jaccard + LCS combined similarity.
        
        Args:
            text: Query text to check
            threshold: Similarity threshold (0.0-1.0). Default 0.3 for new algorithm.
            top_k: Number of top matches to return
            corpus_assignment_no: Assignment to compare against
        
        Returns:
            Dict with plagiarism_percent, total_chunks, matched_chunks, top_matches, document_breakdown
        """
        if not text.strip():
            return {
                "plagiarism_percent": 0.0,
                "total_chunks": 0,
                "matched_chunks": 0,
                "top_matches": [],
                "document_breakdown": [],
            }

        # Get corpus documents
        corpus_docs = self._get_corpus_documents(corpus_assignment_no=corpus_assignment_no)
        if not corpus_docs:
            return {
                "plagiarism_percent": 0.0,
                "total_chunks": 1,
                "matched_chunks": 0,
                "top_matches": [],
                "document_breakdown": [],
            }

        # Split query text into chunks for display purposes
        query_chunks = split_into_chunks(text)
        
        # Compare query document against each corpus document
        matches = []
        matched_docs = 0
        by_document = {}  # key -> similarity score

        for corpus_doc in corpus_docs:
            corpus_text = corpus_doc["text"]
            if not corpus_text.strip():
                continue

            # Calculate similarity between full documents
            doc_similarity = self._combined_similarity(text, corpus_text)

            if doc_similarity >= threshold:
                matched_docs += 1

            # Get best matching chunk pair for display
            corpus_chunks = split_into_chunks(corpus_text)
            best_query_chunk = query_chunks[0] if query_chunks else ""
            best_corpus_chunk = corpus_chunks[0] if corpus_chunks else ""
            best_chunk_similarity = 0.0

            # Find the best matching chunk pair
            if query_chunks and corpus_chunks:
                for q_chunk in query_chunks:
                    for c_chunk in corpus_chunks:
                        chunk_sim = self._combined_similarity(q_chunk, c_chunk)
                        if chunk_sim > best_chunk_similarity:
                            best_chunk_similarity = chunk_sim
                            best_query_chunk = q_chunk
                            best_corpus_chunk = c_chunk

            key = (
                corpus_doc["document_name"],
                corpus_doc["student_id"],
                corpus_doc["assignment_no"],
            )
            by_document[key] = doc_similarity

            matches.append(
                {
                    "query_chunk": best_query_chunk,
                    "matched_chunk": best_corpus_chunk,
                    "source_document": (
                        f"{corpus_doc['document_name']}"
                        f"{'' if not corpus_doc['student_id'] else f' (student: {corpus_doc['student_id']})'}"
                    ),
                    "source_student_id": corpus_doc["student_id"],
                    "source_assignment_no": corpus_doc["assignment_no"],
                    "similarity": doc_similarity,
                    "is_flagged": doc_similarity >= threshold,
                }
            )

        matches.sort(key=lambda x: x["similarity"], reverse=True)

        # Calculate overall plagiarism percentage
        if matches:
            avg_similarity = sum(m["similarity"] for m in matches) / len(matches)
            plagiarism_percent = (matched_docs / len(corpus_docs)) * 100.0 if corpus_docs else 0.0
            plagiarism_percent = max(plagiarism_percent, avg_similarity * 100.0)
        else:
            plagiarism_percent = 0.0

        # Build document-level breakdown
        breakdown = [
            {
                "source_document": doc_name,
                "source_student_id": student_id,
                "source_assignment_no": assign_no,
                "matched_chunks": 1,  # For new algorithm, each document is compared once
                "coverage_percent": sim * 100.0,
            }
            for (doc_name, student_id, assign_no), sim in sorted(
                by_document.items(), key=lambda item: item[1], reverse=True
            )
            if sim >= threshold
        ]

        return {
            "plagiarism_percent": min(plagiarism_percent, 100.0),
            "total_chunks": len(query_chunks) if query_chunks else 1,
            "matched_chunks": matched_docs,
            "top_matches": matches[:top_k],
            "document_breakdown": breakdown,
        }
