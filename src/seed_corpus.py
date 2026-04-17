from __future__ import annotations

from pathlib import Path

from .plagiarism_engine import PlagiarismEngine


def seed_demo_corpus(project_root: Path, reset: bool = False) -> None:
    engine = PlagiarismEngine()

    if reset:
        engine.clear_database()

    existing = engine.list_documents()
    existing_names = {d["document_name"] for d in existing}

    students = ["001", "002", "003", "004", "005"]
    assignments = [1, 2, 3, 4]

    added_docs = 0
    added_chunks = 0
    skipped = 0
    missing = []

    for student_id in students:
        for assignment_no in assignments:
            filename = f"{student_id}_a{assignment_no}.txt"
            path = project_root / filename
            if not path.exists():
                missing.append(filename)
                continue

            if filename in existing_names:
                skipped += 1
                continue

            text = path.read_text(encoding="utf-8", errors="ignore")
            result = engine.ingest_document(
                document_name=filename,
                text=text,
                student_id=student_id,
                assignment_no=assignment_no,
            )
            if result.get("chunks_added", 0) > 0:
                added_docs += 1
                added_chunks += int(result["chunks_added"])
            else:
                # If a file is empty, count as skipped to keep stats consistent.
                skipped += 1

    print("Seeding complete")
    print(f"Added docs: {added_docs}")
    print(f"Added chunks: {added_chunks}")
    print(f"Skipped existing: {skipped}")
    if missing:
        print("Missing files:")
        for m in missing:
            print(f"- {m}")


if __name__ == "__main__":
    seed_demo_corpus(Path(__file__).resolve().parent.parent, reset=False)

