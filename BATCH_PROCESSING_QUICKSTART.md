# Quick Start: Batch Processing

## Step-by-Step Guide

### 1. Prepare Your Files
Organize your assignment submissions in a folder on your computer. Name each file using this format:

```
(student_roll_number)_A(assignment_number).txt
```

**Examples:**
- `001_A1.txt`
- `002_A1.txt`
- `003_A1.txt`
- `015_A1.txt`

**Notes:**
- Roll numbers should be unique per student (e.g., 001, 002, 003, etc.)
- The 'A' can be uppercase or lowercase (A or a)
- Assignment number must be a number (1, 2, 3, etc.)
- File extension: `.txt` or `.pdf`

### 2. Create a ZIP File
Use your operating system's file compression tool:

**Windows:**
1. Select all files
2. Right-click → Send to → Compressed (zipped) folder
3. Name it something like `assignment1_submissions.zip`

**macOS:**
1. Select all files
2. Right-click → Compress Selection
3. ZIP file is created automatically

**Linux:**
```bash
zip -j assignment1_submissions.zip *.txt
# -j: flattens directory structure
```

### 3. Upload to the Application
1. Open the Streamlit app: `streamlit run app.py`
2. Click on the **"Batch Processing"** tab
3. Set the **Assignment Number** (must match the number in your filenames)
4. Upload your ZIP file
5. Click **"Process ZIP File"**

### 4. Review Results
The system will show:
- ✅ Number of files successfully ingested
- ⚠️ Any files that failed to process (with reasons)
- 🔴 HIGH RISK plagiarism matches
- 🟡 MEDIUM RISK potential plagiarism

---

## Example: Processing 5 Submissions

### Files in your folder:
```
001_A1.txt
002_A1.txt
003_A1.txt
004_A1.txt
005_A1.txt
```

### After compression:
```
submissions_batch1.zip
```

### Upload & Process:
1. Assignment Number: `1` (from the filenames)
2. Similarity Threshold: `0.3` (default, catches 30%+ matches)
3. Click "Process ZIP File"

### Output:
- 5 files ingested successfully
- System performs 10 pairwise comparisons:
  - 001 vs 002, 001 vs 003, 001 vs 004, 001 vs 005
  - 002 vs 003, 002 vs 004, 002 vs 005
  - 003 vs 004, 003 vs 005
  - 004 vs 005
- Reports show which pairs have suspicious similarities

---

## Troubleshooting

### Files not being processed?
- ❌ **Wrong filename format**: Check format is exactly `(number)_A(number).ext`
- ❌ **Uppercase A**: Both `A` and `a` are accepted
- ❌ **Wrong extension**: Only `.txt` or `.pdf` supported
- ❌ **No readable text**: PDFs must have selectable text (OCR disabled)

### No plagiarism detected?
- Submissions are truly unique (good!)
- Threshold is too high (lower the slider to see more matches)
- Text sections are too different (algorithm is working correctly)

### Ingestion shows 0 files?
- ZIP file might be empty or corrupted
- Files don't match the naming convention
- Try extracting the ZIP manually to verify content

---

## Advanced Tips

### Comparing Across Multiple Assignments
Run the batch processor once per assignment number:
1. Assignment 1: Upload `*_A1.txt` files (set assignment to 1)
2. Assignment 2: Upload `*_A2.txt` files (set assignment to 2)
3. Check results separately for each

(If you want cross-assignment comparison, use the original "Plagiarism Check" tab)

### Adjusting Sensitivity
- **Low threshold (0.1-0.3)**: More matches reported, includes minor similarities
- **High threshold (0.6-0.95)**: Only obvious plagiarism, fewer false positives

### Large Batches
- 50+ submissions work fine
- System processes them efficiently
- Typical time: 10-20 seconds for 50 submissions

---

## Understanding Your Results

### Similarity Score
Shows how much of one submission appears in another:
- **0.9-1.0** (90-100%): Almost identical - highly suspicious
- **0.7-0.9** (70-90%): Very similar - likely plagiarism
- **0.5-0.7** (50-70%): Significant overlap - possible plagiarism
- **0.3-0.5** (30-50%): Some overlap - review manually
- **0.0-0.3** (0-30%): Minor overlap - probably independent work

### Algorithm
The system intelligently combines:
- **Token overlap** (60%): How many unique words are shared
- **Sequence matching** (40%): How much of the text appears in same order

This catches both direct copying and paraphrasing attempts.

---

## Next Steps
After identifying suspicious pairs:
1. Review the original assignment files
2. Compare them side-by-side manually if needed
3. Have a conversation with the students involved
4. Keep documentation of plagiarism cases

---

**Need help?** Check [BATCH_PROCESSING_GUIDE.md](BATCH_PROCESSING_GUIDE.md) for technical details.
