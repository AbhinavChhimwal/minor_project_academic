# Understanding Plagiarism Similarity Score - Detailed Guide

## What is Similarity Score?

The **similarity score** is a number between **0.0 and 1.0** (or **0% to 100%**) that measures how much one document resembles another document.

- **1.0 (100%)** = Documents are identical
- **0.5 (50%)** = Documents share about half of their content
- **0.0 (0%)** = Documents are completely different

### Visual Understanding

```
0.0 ════════════════════════════════════════ 1.0
|                                            |
No match              Some overlap          Identical
(different)         (possible plagiarism)    (certain plagiarism)
```

---

## How Similarity is Calculated

The system uses **two different algorithms combined** to detect plagiarism:

### Algorithm 1: Jaccard Similarity (60% importance)

**What it measures**: How many **unique words are shared** between two documents.

**Formula**:
```
Jaccard = (Shared Words) / (Total Unique Words)
```

### Example 1: Very Similar Documents

**Document A (Student 001):**
```
"Python is a programming language. Python is easy to learn. 
Python is widely used for web development."
```

**Document B (Student 002):**
```
"Python is a programming language. Python is extremely easy to learn. 
Python is widely used for web development and data science."
```

**Step 1: Extract unique words**
```
Doc A words: {python, is, a, programming, language, easy, learn, widely, used, for, web, development}
Doc B words: {python, is, a, programming, language, extremely, easy, learn, widely, used, for, web, development, and, data, science}
```

**Step 2: Find shared words**
```
Shared: {python, is, a, programming, language, easy, learn, widely, used, for, web, development}
Count: 12 words
```

**Step 3: Count total unique words (union)**
```
Total unique: {python, is, a, programming, language, easy, learn, widely, used, for, web, development, extremely, and, data, science}
Count: 16 words
```

**Step 4: Calculate Jaccard**
```
Jaccard = 12 / 16 = 0.75 (75% overlap)
```

---

### Algorithm 2: Longest Common Sequence (LCS Ratio) - (40% importance)

**What it measures**: How much of the **word order is preserved** between documents.

**Important**: LCS looks at words in the same order, not just the same words.

### Example 2: Same Concept, Different Order

**Document A:**
```
"The algorithm uses dynamic programming"
```

**Document B:**
```
"Dynamic programming uses the algorithm"
```

**Word-by-word comparison:**
```
Doc A: [The, algorithm, uses, dynamic, programming]
Doc B: [Dynamic, programming, uses, the, algorithm]
```

**LCS matching (words in same order):**
```
Common sequence: [uses] = 1 word in same position
Average length: (5 + 5) / 2 = 5 words
LCS_Ratio = 1 / 5 = 0.20 (20%)
```

**Why so low?** Because the words appear in different order, only "uses" appears in a similar relative position.

### Example 3: Same Word Order

**Document A:**
```
"The cat sat on the mat"
```

**Document B:**
```
"The cat sat on a mat"
```

**LCS matching:**
```
Doc A: [The, cat, sat, on, the, mat]
Doc B: [The, cat, sat, on, a, mat]

Common sequence: [The, cat, sat, on, mat] = 5 words
Average length: (6 + 6) / 2 = 6 words
LCS_Ratio = 5 / 6 = 0.833 (83%)
```

---

## Combined Similarity Score

The final score **combines both algorithms**:

```
Final Score = (0.6 × Jaccard) + (0.4 × LCS_Ratio)
```

### Why combine them?

- **Jaccard (60%)**: Catches copy-pasting and reuse of same words
- **LCS (40%)**: Catches if words are reordered to disguise plagiarism

### Example 4: Two Different Cases

**Case 1: Direct Copy**
```
Doc A: "Python is a programming language used for web development"
Doc B: "Python is a programming language used for web development"

Jaccard: 1.0 (100% same words)
LCS: 1.0 (100% same order)
Combined: (0.6 × 1.0) + (0.4 × 1.0) = 1.0 (100% PLAGIARISM)
```

**Case 2: Paraphrased**
```
Doc A: "Python is a programming language used for web development"
Doc B: "Python is used for web development and is a programming language"
        (Reordered, slightly different)

Jaccard: 0.85 (85% same words)
LCS: 0.60 (60% word order match)
Combined: (0.6 × 0.85) + (0.4 × 0.60) = 0.51 + 0.24 = 0.75 (75% PLAGIARISM)
```

---

## Real-World Examples

### Example 5: Student Assignment Comparison

**Original Assignment (Reference):**
```
"Artificial Intelligence is a branch of computer science that aims to 
create intelligent machines that can perform tasks like humans. AI has 
applications in healthcare, finance, and transportation industries."
```

**Student A Submission:**
```
"Artificial Intelligence is a branch of computer science that aims to 
create intelligent machines that can perform tasks like humans. AI has 
applications in healthcare, finance, and transportation industries."
```

**Analysis**: ✅ **EXACT MATCH - 100% Similarity**
- Identical text
- Result: **🔴 FLAGGED - Highly suspicious**

---

### Example 6: Slight Paraphrasing

**Original Assignment (Reference):**
```
"The binary search algorithm divides a sorted array in half repeatedly. 
It is more efficient than linear search with O(log n) time complexity."
```

**Student B Submission:**
```
"The binary search method works by continuously splitting a sorted array 
into two halves. This approach is faster than checking each element 
sequentially, with an efficiency rating of O(log n)."
```

**Analysis**:
```
Shared words: {the, binary, search, a, sorted, array, in, half, is, more/faster, efficient, than, linear/sequential, o, log, n}
= ~14 shared words

Word order: Some words appear in similar order but not all
LCS ratio: ~0.65

Jaccard: ~0.70 (70%)
LCS: ~0.65 (65%)
Combined: (0.6 × 0.70) + (0.4 × 0.65) = 0.42 + 0.26 = 0.68 (68%)
```

**Result**: 🟡 **MEDIUM RISK - Possible paraphrasing**

---

### Example 7: Completely Different

**Original Assignment (Reference):**
```
"The water cycle describes how water moves between ocean, atmosphere, 
and land through evaporation, condensation, and precipitation."
```

**Student C Submission:**
```
"Photosynthesis is the process where plants convert light energy into 
chemical energy. This occurs in the chloroplasts of plant cells through 
light-dependent and light-independent reactions."
```

**Analysis**:
```
Shared words: {the, is, of, in, process, through}
= ~6 very common words

Word order: Completely different topics
LCS ratio: ~0.15

Jaccard: ~0.20 (20%)
LCS: ~0.15 (15%)
Combined: (0.6 × 0.20) + (0.4 × 0.15) = 0.12 + 0.06 = 0.18 (18%)
```

**Result**: ✅ **NO FLAG - Original work**

---

## Interpreting Similarity Scores

### Default Threshold: 0.3 (30%)

The system flags documents as potentially plagiarized if similarity ≥ 0.3:

| Score | Percentage | Risk Level | Meaning | Action |
|-------|-----------|-----------|---------|--------|
| 0.0-0.2 | 0-20% | ✅ Low | Minimal overlap, likely original | No action |
| 0.2-0.4 | 20-40% | 🟡 Medium | Modest overlap, worth reviewing | Review manually |
| 0.4-0.6 | 40-60% | 🟡 Medium | Significant overlap, likely plagiarized | Investigate |
| 0.6-0.8 | 60-80% | 🔴 High | Very similar, very suspicious | Probable plagiarism |
| 0.8-1.0 | 80-100% | 🔴 Very High | Nearly identical or exact match | Definite plagiarism |

---

## How to Adjust Sensitivity

### Threshold Slider (0.1 to 0.95)

**Lower Threshold (More Lenient)**
```
Threshold: 0.1 (10%)
Shows: Even slightly similar documents
Risk: More false positives (flagging original work)
Use when: You want to catch all possible plagiarism
```

**Higher Threshold (More Strict)**
```
Threshold: 0.7 (70%)
Shows: Only very similar documents
Risk: May miss subtle plagiarism
Use when: You want to be very certain (fewer false positives)
```

**Default Threshold (Balanced)**
```
Threshold: 0.3 (30%)
Shows: Obvious plagiarism + some paraphrasing
Risk: Good balance
Use when: In doubt (recommended)
```

---

## Common Misconceptions

### ❌ Myth 1: "50% similarity = 50% copied"

**Reality**: Similarity is not about percentage of copied content.

Example:
```
Student A: "Python is easy"  (3 words)
Student B: "Python is hard"  (3 words)

Similarity: ~0.66 (66%)

But they said OPPOSITE things! The similarity measures word overlap, 
not meaning overlap.
```

### ❌ Myth 2: "Different words = Different content"

**Reality**: Reordered or replaced words still show high similarity.

Example:
```
Original: "Quick brown fox jumps"
Plagiarism: "A quick, incredibly brown fox leaps upward"

Similarity: ~0.60 (60%) - Still caught!
```

### ✅ Fact 1: "Very similar text = Very similar score"

If text is nearly identical, score will be high (0.8+).

### ✅ Fact 2: "Completely different = Low score"

If documents are about different topics, score will be low (0.0-0.3).

---

## Practical Decision Making

### When Student Gets 100% Similarity

```
Action: Check if it's the same file being compared
Reason: System should prevent this, but verify
Solution: Set "Skip duplicates" option
```

### When Student Gets 75% Similarity

```
Action: Investigate by reading both documents
Look for:
  • Exact phrase matches? → Plagiarism
  • Same structure, different words? → Paraphrasing
  • Same references? → Might be coincidence
Decision: Manual review needed to confirm
```

### When Student Gets 25% Similarity

```
Action: Probably fine
Check: Are the shared words just common words?
  • "the", "is", "and", "a", "for" = Common words, low concern
  • "plagiarism detection algorithm" = Specific phrases, review
Decision: Low risk unless specific terms match
```

### When Student Gets 5% Similarity

```
Action: No action needed
Status: Likely original work
Confidence: High
```

---

## Special Cases

### Same Topic, Different Approach

```
Both students write about: "Machine Learning Applications"

Doc A: "ML is used in healthcare for diagnosis prediction"
Doc B: "Healthcare applications include diagnosis, treatment planning, and prognosis"

Similarity: 0.45 (45%)
Reason: Similar topic, overlapping words, but different focus
Action: Review, but likely legitimate (same topic assignment)
```

### Code Comments (Text Analysis)

```
Doc A: "This function validates user input"
Doc B: "This function checks if user input is valid"

Similarity: 0.78 (78%)
Reason: Nearly same explanation
Action: Check if it's the same explanation or genuine paraphrase
```

### Quoted References

```
Doc A: "As Einstein said: 'Imagination is more important than knowledge'"
Doc B: "Einstein stated: 'Imagination is more important than knowledge'"

Similarity: 0.95 (95%)
Reason: Same quote (expected)
Action: Fine if properly cited. Check bibliography.
```

---

## Step-by-Step Example: Full Comparison

Let's trace through a complete example:

### The Documents

**Reference Document:**
```
"Climate change refers to long-term shifts in global temperatures 
and weather patterns. It is primarily caused by human activities 
like burning fossil fuels and deforestation."
```

**Student Submission:**
```
"Global climate change involves persistent changes in Earth's temperature 
and atmospheric patterns. This phenomenon is mainly driven by human 
activities including the burning of fossil fuels and removal of forests."
```

### Step 1: Extract Words

**Reference Words**: 
climate, change, refers, long, term, shifts, global, temperatures, weather, patterns, it, is, primarily, caused, by, human, activities, like, burning, fossil, fuels, and, deforestation

**Student Words**: 
global, climate, change, involves, persistent, changes, earth, temperature, atmospheric, patterns, this, phenomenon, is, mainly, driven, by, human, activities, including, the, burning, of, fossil, fuels, and, removal, of, forests

### Step 2: Find Overlaps

**Shared words**: 
climate, change, global, temperature(s), patterns, is, caused/driven, by, human, activities, burning, fossil, fuels, and

**Count**: ~14 shared words

### Step 3: Calculate Jaccard

```
Unique words (Reference): ~23
Unique words (Student): ~28
Total unique words (Union): ~35

Jaccard = 14 / 35 = 0.40 (40%)
```

### Step 4: Calculate LCS Ratio

```
Reference sequence: [climate, change, global, temperature, patterns, is, human, activities, burning, fossil, fuels]
Student sequence: [global, climate, change, temperature, patterns, is, human, activities, burning, fossil, fuels]

Common in sequence: 11 words
Average length: (23 + 28) / 2 = 25.5

LCS_Ratio = 11 / 25.5 = 0.43 (43%)
```

### Step 5: Combine Scores

```
Final Score = (0.6 × 0.40) + (0.4 × 0.43)
            = 0.24 + 0.17
            = 0.41 (41%)
```

### Step 6: Interpret Result

```
Similarity: 41%
Threshold: 30% (default)
Status: 🟡 FLAGGED (above threshold)
Risk Level: MEDIUM
Recommendation: Review document - possible paraphrasing detected
```

---

## Summary: What to Remember

1. **Similarity = Word Overlap + Word Order**
   - Not about meaning, just about text similarity

2. **Higher Score = More Suspicious**
   - 0-30%: Probably okay
   - 30-60%: Worth checking
   - 60%+: Very suspicious

3. **Two Algorithms Work Together**
   - Jaccard catches copy-pasting
   - LCS catches reordering/paraphrasing

4. **Context Matters**
   - Same topic? Some overlap is expected
   - Different topic? Even small overlap is suspicious
   - Direct quotes? High similarity is okay if cited

5. **Use the Threshold Slider**
   - Default 0.3 is good for most cases
   - Adjust if needed: lower for lenient, higher for strict

---

## Quick Reference Card

```
┌──────────────────────────────────────────────────────┐
│ SIMILARITY SCORE QUICK GUIDE                          │
├──────────────────────────────────────────────────────┤
│                                                       │
│ 0.0 - 0.2:  ✅ Original work (no action)            │
│ 0.2 - 0.4:  🟡 Minor overlap (review optional)      │
│ 0.4 - 0.6:  🟡 Significant overlap (investigate)    │
│ 0.6 - 0.8:  🔴 Very similar (very likely plagiarism)│
│ 0.8 - 1.0:  🔴 Nearly identical (definite plagiarism)│
│                                                       │
│ Threshold = 0.3 (default, adjust as needed)         │
│ Score = 60% Jaccard + 40% LCS                       │
│ (60% word overlap + 40% word order)                 │
│                                                       │
└──────────────────────────────────────────────────────┘
```

---

**Note**: This system is for detection and review. Final determination of plagiarism should always be made by a human reviewer after examining the actual documents.
