# AI Assignment Plagiarism Checker

A practical plagiarism-checking web app where you:
- upload all reference assignments you want to compare against,
- upload a new submission,
- get plagiarism percentage + top matched passages + source document breakdown.

## Supported File Types

- `.txt`
- `.pdf`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Note: PDFs must have selectable text. (OCR is disabled.)

## Run

```bash
streamlit run app.py
```

## How to Use

1. Open **Database Management** tab.
2. Set `Assignment number for these files` (and optional `Student ID`) and upload the reference files. Click **Ingest uploaded assignments**.
3. Open **Plagiarism Check** tab. Set your submission assignment number `N` and the `Compare against assignment number` (default is `N-1`).
4. Upload the submission and click **Run plagiarism check**.
5. Review:
   - overall plagiarism risk percentage,
   - flagged chunk count,
   - top matched passages,
   - document-level source breakdown.

## Storage

- Metadata and text chunks are stored in SQLite at `data/plagiarism.sqlite3`.
- You can inspect and clear stored corpus from the **Database Status** tab.
