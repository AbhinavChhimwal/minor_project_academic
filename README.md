# AI Assignment Plagiarism Checker

A practical plagiarism-checking web app with two workflows:

## Workflow 1: Manual Check (Original)
- Upload reference assignments you want to compare against
- Upload a new submission
- Get plagiarism percentage + top matched passages + source document breakdown

## Workflow 2: Batch Processing (New)
- Prepare a ZIP file with all submissions named: `(roll_no)_A(assignment_no).ext`
  - Examples: `001_A1.txt`, `002_A1.txt`, `015_A1.pdf`
- Upload the ZIP file
- System automatically:
  - Extracts all files
  - Validates filename format and metadata
  - Adds them to database
  - Compares every submission against all others
  - Generates plagiarism report with detected matches

## Supported File Types

- `.txt`
- `.pdf` (must have selectable text; OCR is disabled)

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

### Option 1: Manual Check (Original Workflow)

1. Open **Database Management** tab.
2. Set `Assignment number for these files` (and optional `Student ID`) and upload the reference files. Click **Ingest uploaded assignments**.
3. Open **Plagiarism Check** tab. Set your submission assignment number `N` and the `Compare against assignment number` (default is `N-1`).
4. Upload the submission and click **Run plagiarism check**.
5. Review:
   - overall plagiarism risk percentage,
   - flagged chunk count,
   - top matched passages,
   - document-level source breakdown.

### Option 2: Batch Processing (New Workflow)

1. Prepare a ZIP file with submissions using naming convention: `(roll_no)_A(assignment_no).ext`
   - Example structure:
     ```
     submissions.zip
     ├── 001_A1.txt
     ├── 002_A1.txt
     ├── 003_A1.pdf
     └── 004_A1.txt
     ```
2. Open **Batch Processing** tab.
3. Set the assignment number (must match the assignment number in filenames).
4. Upload the ZIP file.
5. System automatically:
   - Extracts files from ZIP
   - Parses metadata from filenames
   - Ingests files into database
   - Compares every file against every other file
6. Review the plagiarism report showing all pairs with detected similarities.

## Storage

- Metadata and text chunks are stored in SQLite at `data/plagiarism.sqlite3`.
- You can inspect and clear stored corpus from the **Database Status** tab.
