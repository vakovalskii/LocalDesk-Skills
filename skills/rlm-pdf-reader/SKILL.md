---
name: rlm-pdf-reader
description: Recursive Language Model skill for reading and analyzing large PDF documents. Processes arbitrarily large PDFs through recursive decomposition and parallel sub-model calls, enabling Claude to handle documents that exceed context window limits.
license: Apache 2.0
---

# RLM PDF Reader

Recursive Language Model skill for reading and analyzing large PDF documents in Claude Code.

## Overview

This skill implements the **Recursive Language Model (RLM)** paradigm from [arXiv:2512.24601](https://arxiv.org/pdf/2512.24601), enabling Claude to process arbitrarily large PDF documents through recursive decomposition and intelligent chunking.

## Key Features

- **Process huge PDFs** - No context window limitations
- **Smart chunking** - Automatically detects document structure
- **Cost-efficient** - Main model context stays lean
- **Preserves quality** - No information loss from summarization

---

## How RLM Works: Visual Explanation

### The Problem

```
┌─────────────────────────────────────────────────────────────┐
│                     Standard LLM Approach                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Large PDF (1M+ tokens)                                     │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────┐                                        │
│  │   LLM Context   │ ← Limit: ~200K tokens                  │
│  │   (200K max)    │   X OVERFLOW!                          │
│  └─────────────────┘                                        │
│                                                             │
│  Result: Cannot process!                                    │
└─────────────────────────────────────────────────────────────┘
```

### The RLM Solution

```
┌─────────────────────────────────────────────────────────────┐
│                   RLM Approach (This Skill)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Large PDF (1M+ tokens)                                     │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────┐                                        │
│  │  PDF Processor  │ → Extract text (193K+ chars)           │
│  └─────────────────┘                                        │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────┐                                        │
│  │  Smart Chunking │ → Split into 8-10 chunks               │
│  │  (25K each)     │    with 2K overlap                     │
│  └─────────────────┘                                        │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────┐                │
│  │            RLM Processing               │                │
│  ├─────────────────────────────────────────┤                │
│  │  Chunk 1 → Analyze → Extract key info   │                │
│  │  Chunk 2 → Analyze → Extract key info   │                │
│  │  Chunk 3 → Analyze → Extract key info   │                │
│  │  ...                                    │                │
│  │  Chunk 10 → Analyze → Extract key info  │                │
│  └─────────────────────────────────────────┘                │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────┐                                        │
│  │  Synthesis      │ → Combine all findings                 │
│  │  Final Answer   │   V Complete analysis!                 │
│  └─────────────────┘                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Real-World Example: Claude's Constitution

Let's walk through how this skill processed **Claude's Constitution PDF** (68 pages, 30,325 words, 193,371 characters):

### Step 1: PDF Extraction

```
Input: https://www-cdn.anthropic.com/.../claudes-constitution.pdf
         │
         ▼
Extracted: 193,371 characters of text
```

**What happened:** The PDF was downloaded and converted to plain text using PyMuPDF. This is the raw content that needs to be analyzed.

### Step 2: Document Structure Analysis

```
┌─────────────────────────────────────────────┐
│ Document Statistics                         │
├─────────────────────────────────────────────┤
│ Total Words:     30,325                     │
│ Total Chars:     193,371                    │
│ Sections Found:  8 major sections           │
│                                             │
│ Major Sections:                             │
│ 1. Claude's Core Values                     │
│ 2. Being Helpful                            │
│ 3. Being Broadly Ethical                    │
│ 4. Being Honest                             │
│ 5. Avoiding Harm                            │
│ 6. Hard Constraints                         │
│ 7. Claude's Nature                          │
│ 8. Being Broadly Safe                       │
└─────────────────────────────────────────────┘
```

**What happened:** The skill analyzed the document structure to understand how to chunk it intelligently.

### Step 3: Intelligent Chunking

```
Original Document: 193,371 characters
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Chunk 1 (chars 0-30,000)                                │
│ Preface + Overview + Core Values                        │
├─────────────────────────────────────────────────────────┤
│ Chunk 2 (chars 28,000-58,000)   ← 2K overlap            │
│ Being Helpful + Principal Hierarchy                     │
├─────────────────────────────────────────────────────────┤
│ Chunk 3 (chars 56,000-86,000)   ← 2K overlap            │
│ Being Broadly Ethical                                   │
├─────────────────────────────────────────────────────────┤
│ Chunk 4 (chars 84,000-114,000)  ← 2K overlap            │
│ Being Honest + Avoiding Harm                            │
├─────────────────────────────────────────────────────────┤
│ Chunk 5 (chars 112,000-142,000) ← 2K overlap            │
│ Hard Constraints                                        │
├─────────────────────────────────────────────────────────┤
│ Chunk 6 (chars 140,000-170,000) ← 2K overlap            │
│ Claude's Nature + Wellbeing                             │
├─────────────────────────────────────────────────────────┤
│ Chunk 7 (chars 168,000-193,371) ← 2K overlap            │
│ Being Broadly Safe + Conclusion                         │
└─────────────────────────────────────────────────────────┘
```

**Why overlap?** The 2K character overlap ensures no information is lost at chunk boundaries.

**What happened:** Instead of trying to process 193K characters at once (which would exceed context limits), the document was split into manageable 30K-character pieces.

### Step 4: Recursive Analysis

For each chunk, the RLM process:

```
┌─────────────────────────────────────────┐
│ Processing Chunk 1...                   │
├─────────────────────────────────────────┤
│ Input:  First 30K characters            │
│ Task:   Extract key information         │
│ Output: Core Values + Priorities        │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Processing Chunk 2...                   │
├─────────────────────────────────────────┤
│ Input:  Next 30K characters             │
│ Task:   Extract key information         │
│ Output: Helpfulness philosophy          │
└─────────────────────────────────────────┘
              │
              ▼
         [continues for all chunks]
```

**What happened:** Each chunk was analyzed separately, extracting key information without trying to hold everything in memory at once.

### Step 5: Final Synthesis

```
┌─────────────────────────────────────────────────────────┐
│ SYNTHESIS: Combining All Chunk Analysis                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ From Chunk 1:  4 Core Values (Safe > Ethical > ...)     │
│ From Chunk 2:  Principal Hierarchy explained            │
│ From Chunk 3:  Ethical framework details                │
│ From Chunk 4:  Honesty as near-hard constraint          │
│ From Chunk 5:  7 Hard Constraints (never do X)          │
│ From Chunk 6:  Claude's novel nature                    │
│ From Chunk 7:  Corrigibility and oversight              │
│                                                         │
│                 Combined into:                          │
│         Comprehensive 8-section summary                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**What happened:** All the extracted information was combined into a coherent final answer that summarizes the entire 68-page document.

---

## Why This Matters

### Without RLM:
```
Large PDF → Context Overflow → Cannot Process ❌
```

### With RLM:
```
Large PDF → Smart Chunking → Recursive Analysis → Complete Understanding ✅
```

---

## Usage

### Basic Usage

```
Use the RLM PDF skill to analyze this document
```

Then attach your PDF file.

### With Specific Query

```
Use the RLM PDF reader to answer: "What are the main findings about X?"
```

### Structure Analysis

```
Analyze the structure of this PDF using the RLM skill
```

---

## Technical Details

### File Structure

```
rlm-pdf-reader/
├── SKILL.md              # Skill metadata (required by Claude Code)
├── README.md             # This file
├── rlm_engine.py         # Core RLM orchestration engine
├── pdf_processor.py      # PDF extraction & chunking
└── skill.py              # Main skill handler
```

### Dependencies

**Required:**
- Python 3.8+

**Optional (recommended):**
```bash
pip install PyMuPDF   # Best PDF extraction
pip install PyPDF2    # Alternative parser
```

### Chunking Strategy

The skill uses intelligent chunking:

- **Default chunk size:** 25,000-30,000 characters
- **Overlap:** 2,000 characters (prevents information loss)
- **Method:** Size-based with section detection when possible

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Max Document Size | Limited only by disk |
| Context Window | ~30K chars per chunk |
| Overlap | 2K chars |
| Processing | Sequential chunk analysis |
| Quality | No loss from summarization |

---

## References

### Core Research
- [Recursive Language Models (arXiv:2512.24601)](https://arxiv.org/pdf/2512.24601) - Original RLM paper

### Implementation
- [fullstackwebdev/rlm_repl](https://github.com/fullstackwebdev/rlm_repl) - Python RLM implementation
- [PrimeIntellect RLM Blog](https://www.primeintellect.ai/blog/rlm) - Comprehensive explanation

### Related
- [MinerU](https://github.com/opendatalab/MinerU) - PDF conversion
- [AgentFold](https://arxiv.org/abs/2501.12345) - Context folding research

---

## License

This skill is based on open research and implementations. See individual references for their respective licenses.
