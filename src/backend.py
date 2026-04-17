import sqlite3
from pathlib import Path

import faiss
import numpy as np

from .config import DB_PATH, FAISS_PATH, HIDDEN_DIM


class PlagiarismStore:
    def __init__(self, db_path=DB_PATH, faiss_path=FAISS_PATH, dim=HIDDEN_DIM):
        self.db_path = Path(db_path)
        self.faiss_path = Path(faiss_path)
        self.dim = dim
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self._init_db()
        self.index = self._load_or_create_index()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                text TEXT NOT NULL,
                vector_id INTEGER NOT NULL
            )
            """
        )
        self.conn.commit()

    def _load_or_create_index(self):
        if self.faiss_path.exists():
            return faiss.read_index(str(self.faiss_path))
        return faiss.IndexFlatL2(self.dim)

    def add_entries(self, student_id: str, sentences, vectors):
        if not vectors:
            return
        mat = np.stack(vectors).astype('float32')
        start_id = self.index.ntotal
        self.index.add(mat)

        cur = self.conn.cursor()
        for i, sentence in enumerate(sentences):
            cur.execute(
                'INSERT INTO submissions (student_id, text, vector_id) VALUES (?, ?, ?)',
                (student_id, sentence, start_id + i),
            )
        self.conn.commit()
        self.save_index()

    def search(self, query_vector, k=5):
        if self.index.ntotal == 0:
            return []
        q = np.array([query_vector], dtype='float32')
        distances, ids = self.index.search(q, k)
        cur = self.conn.cursor()

        results = []
        for dist, vid in zip(distances[0], ids[0]):
            if vid < 0:
                continue
            cur.execute(
                'SELECT student_id, text FROM submissions WHERE vector_id = ?',
                (int(vid),),
            )
            row = cur.fetchone()
            if row:
                results.append(
                    {
                        'student_id': row[0],
                        'text': row[1],
                        'vector_id': int(vid),
                        'distance': float(dist),
                        'similarity': float(1 / (1 + dist)),
                    }
                )
        return results

    def save_index(self):
        faiss.write_index(self.index, str(self.faiss_path))
