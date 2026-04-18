import re
import sqlite3
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple

from .config import DB_PATH
from .text_utils import clean_text, extract_text_from_upload


class BatchProcessor:
    """Handles batch processing of zip files containing submissions."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)

    def parse_filename(self, filename: str) -> Tuple[str, int] | None:
        """
        Parse filename in format: roll_no_AssignmentNo.ext
        e.g., 001_A1.txt -> ('001', 1)
        e.g., 001_A15.txt -> ('001', 15)
        Returns (roll_no, assignment_no) or None if invalid format.
        """
        # Remove extension
        name_without_ext = filename.rsplit(".", 1)[0] if "." in filename else filename
        
        # Match pattern: digits_A_digits
        pattern = r"^(\d+)_[Aa](\d+)$"
        match = re.match(pattern, name_without_ext)
        
        if match:
            roll_no = match.group(1)
            assignment_no = int(match.group(2))
            return roll_no, assignment_no
        return None

    def extract_files_from_zip(self, zip_bytes: bytes) -> Dict[str, Tuple[str, str, int]]:
        """
        Extract files from zip and parse metadata.
        Returns dict: {filename: (text_content, roll_no, assignment_no)}
        """
        files = {}
        
        try:
            with zipfile.ZipFile(BytesIO(zip_bytes)) as z:
                for file_info in z.filelist:
                    # Skip directories and hidden files
                    if file_info.is_dir() or file_info.filename.startswith("."):
                        continue
                    
                    filename = Path(file_info.filename).name
                    parsed = self.parse_filename(filename)
                    
                    if not parsed:
                        continue  # Skip files that don't match the format
                    
                    roll_no, assignment_no = parsed
                    file_bytes = z.read(file_info.filename)
                    
                    try:
                        text = extract_text_from_upload(filename, file_bytes)
                        if text.strip():
                            files[filename] = (text, roll_no, assignment_no)
                    except Exception:
                        # Skip files that can't be processed
                        pass
        except zipfile.BadZipFile:
            raise ValueError("Invalid zip file")
        
        return files

    def ingest_files_to_db(self, files: Dict[str, Tuple[str, str, int]], skip_duplicates: bool = True) -> Dict:
        """
        Ingest extracted files into the database.
        
        Args:
            files: Dict of {filename: (text_content, roll_no, assignment_no)}
            skip_duplicates: If True, skip existing documents. If False, replace them.
        
        Returns:
            Dict with ingestion summary including duplicates found.
        """
        from .plagiarism_engine import PlagiarismEngine
        
        engine = PlagiarismEngine(self.db_path)
        
        ingested = []
        failed = []
        duplicates = []
        
        # Get existing documents for quick lookup
        existing_docs = self._get_existing_documents_by_assignment(files)
        
        for filename, (text, roll_no, assignment_no) in files.items():
            # Check if document already exists
            if filename in existing_docs:
                duplicates.append({
                    "filename": filename,
                    "roll_no": roll_no,
                    "assignment_no": assignment_no,
                    "reason": "File with same name already exists in database"
                })
                if skip_duplicates:
                    continue
                else:
                    # Delete existing document before re-ingesting
                    engine.delete_document(existing_docs[filename])
            
            try:
                result = engine.ingest_document(
                    document_name=filename,
                    text=text,
                    student_id=roll_no,
                    assignment_no=assignment_no,
                )
                ingested.append({
                    "filename": filename,
                    "roll_no": roll_no,
                    "assignment_no": assignment_no,
                    "chunks": result.get("chunks_added", 0),
                })
            except Exception as e:
                failed.append({
                    "filename": filename,
                    "error": str(e),
                })
        
        return {
            "ingested": ingested,
            "failed": failed,
            "duplicates": duplicates,
            "total_ingested": len(ingested),
            "total_failed": len(failed),
            "total_duplicates": len(duplicates),
        }

    def _get_existing_documents_by_assignment(self, files: Dict[str, Tuple[str, str, int]]) -> Dict[str, int]:
        """
        Check which files from the input already exist in database.
        Returns mapping of {filename: db_id} for existing documents.
        """
        if not files:
            return {}
        
        # Get all assignment numbers from input files
        assignment_nos = set(data[2] for data in files.values())
        
        existing = {}
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        for assignment_no in assignment_nos:
            cur.execute(
                """
                SELECT document_name, id
                FROM documents
                WHERE assignment_no = ?
                """,
                (assignment_no,),
            )
            rows = cur.fetchall()
            for doc_name, db_id in rows:
                # Match by filename
                for input_filename in files.keys():
                    if input_filename == doc_name:
                        existing[input_filename] = db_id
        
        conn.close()
        return existing

    def get_all_documents_by_assignment(self, assignment_no: int) -> List[Dict]:
        """Retrieve all documents for a given assignment from database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.id, d.document_name, d.student_id, d.assignment_no
            FROM documents d
            WHERE d.assignment_no = ?
            ORDER BY d.student_id
            """,
            (assignment_no,),
        )
        rows = cur.fetchall()
        conn.close()
        
        return [
            {
                "db_id": r[0],
                "filename": r[1],
                "roll_no": r[2],
                "assignment_no": r[3],
            }
            for r in rows
        ]

    def get_document_text(self, doc_id: int) -> str:
        """Retrieve full text of a document by reconstructing from chunks."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT GROUP_CONCAT(chunk_text, ' ')
            FROM document_chunks
            WHERE document_id = ?
            """,
            (doc_id,),
        )
        result = cur.fetchone()
        conn.close()
        
        return result[0] if result[0] else ""


class PairwiseSimilarity:
    """Compute pairwise plagiarism similarity between documents."""

    @staticmethod
    def jaccard_similarity(text1: str, text2: str) -> float:
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
    def longest_common_ratio(text1: str, text2: str) -> float:
        """
        Compute ratio of longest common subsequence length to average text length.
        Uses word-level LCS for efficiency.
        """
        words1 = re.findall(r"\b\w+\b", text1.lower())
        words2 = re.findall(r"\b\w+\b", text2.lower())
        
        if not words1 or not words2:
            return 1.0 if words1 == words2 else 0.0
        
        lcs_length = PairwiseSimilarity._lcs_length(words1, words2)
        avg_length = (len(words1) + len(words2)) / 2
        
        return lcs_length / avg_length if avg_length > 0 else 0.0

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
    def combined_similarity(text1: str, text2: str, weights: Dict[str, float] = None) -> float:
        """
        Combine multiple similarity metrics with optional weights.
        Default: 60% Jaccard, 40% LCS ratio
        """
        if weights is None:
            weights = {"jaccard": 0.6, "lcs": 0.4}
        
        jaccard = PairwiseSimilarity.jaccard_similarity(text1, text2)
        lcs = PairwiseSimilarity.longest_common_ratio(text1, text2)
        
        return weights.get("jaccard", 0.6) * jaccard + weights.get("lcs", 0.4) * lcs


class BatchComparison:
    """Compare all documents in an assignment against each other."""

    def __init__(self, db_path=DB_PATH):
        self.batch_processor = BatchProcessor(db_path)
        self.db_path = db_path

    def compare_all_pairs(self, assignment_no: int, threshold: float = 0.3) -> List[Dict]:
        """
        Compare all documents in an assignment against each other.
        Returns list of comparison results above threshold.
        """
        documents = self.batch_processor.get_all_documents_by_assignment(assignment_no)
        
        if len(documents) < 2:
            return []
        
        comparisons = []
        
        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):
                doc1 = documents[i]
                doc2 = documents[j]
                
                text1 = self.batch_processor.get_document_text(doc1["db_id"])
                text2 = self.batch_processor.get_document_text(doc2["db_id"])
                
                if not text1.strip() or not text2.strip():
                    continue
                
                similarity = PairwiseSimilarity.combined_similarity(text1, text2)
                
                if similarity >= threshold:
                    comparisons.append({
                        "document_1": f"{doc1['roll_no']} (A{doc1['assignment_no']})",
                        "document_2": f"{doc2['roll_no']} (A{doc2['assignment_no']})",
                        "similarity": similarity,
                        "flagged": similarity >= 0.7,  # High risk if >= 0.7
                    })
        
        comparisons.sort(key=lambda x: x["similarity"], reverse=True)
        return comparisons
