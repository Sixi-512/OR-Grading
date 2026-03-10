# Operation Research Assignment Automatic Correction and Grading (OR-AACG)

## Overview

- [Description](#description)
- [Requirements](#requirements)
- [Usage](#usage)
- [Output CSV Format](#output-csv-format)
- [Project Structure](#project-structure)

## Description
This system automatically grades Operation Research assignments using AI (LLM). It reads student submissions, compares them with provided questions and answers, and generates scores with feedback comments. The system supports multiple grading attempts and allows batch regeneration of feedback.

## Requirements

### Environment
- Python 3.8 or higher

### Dependencies
Install the required Python packages:
```bash
pip install openai reportlab PyPDF2 python-dotenv
```

## Usage

### 1. Configuration
Create a `.env` file in the project root with only API credentials:
```
API_BASE_URL=https://your-api-endpoint.com/v1
API_KEY=your-api-key
MODEL=your-model-name
```

### 2. Prepare Your Data
- Place student assignments in `data/` directory with filenames like `student_id_xxx.ext`
- Place assignment questions and answers in `resources/` directory
- Question files should NOT contain "答案" or "answer" in the filename
- Answer files MUST contain "答案" or "answer" in the filename

### 3. Run Commands

All commands require `--data-dir` and `--resources-dir` to specify the directories containing student assignments and question/answer files:

```bash
# Grade first homework
python scripts/main.py grade --data-dir ./data --resources-dir ./resources

# Grade specific homework
python scripts/main.py grade --data-dir ./data --resources-dir ./resources --hw 2

# Regenerate comments for all students in homework 1
python scripts/main.py regenerate --data-dir ./data --resources-dir ./resources --hw 1

# Regenerate comments for specific students in homework 2
python scripts/main.py regenerate --data-dir ./data --resources-dir ./resources --hw 2 --students 2451760,2452701
```

**Parameters:**
- `command`: `grade` (new grading) or `regenerate` (update comments only)
- `--data-dir`: Path to directory containing student assignment files (required)
- `--resources-dir`: Path to directory containing question and answer files (required)
- `--hw`: Homework number (default: 1)
- `--students`: Comma-separated student IDs for selective processing (optional, only for regenerate)

### 4. Check Results
Results are stored in `outputs/` directory:
- `grades/hw_[N]/[student_id]_hw_[N].pdf` - Individual graded assignments (organized by homework number)
- `grading_results.csv` - Summary record with all homework scores and comments

## Output CSV Format

| timestamp | student_id | score_hw_1 | score_hw_2 | comment_hw_1 | comment_hw_2 |
|-----------|------------|-----------|-----------|--------------|--------------|
| 2026-03-09T10:30:45 | 2451760 | 85 | 87 | 步骤清晰 | 有改进 |
| 2026-03-09T10:31:15 | 2452701 | 78 | | 计算有误 | |
| 2026-03-09T10:32:00 | 2453118 | | 92 | | 逻辑清晰 |

**Features:**
- Column order: `timestamp`, `student_id`, then all score columns (`score_hw_1`, `score_hw_2`, ...), then all comment columns (`comment_hw_1`, `comment_hw_2`, ...)
- Timestamp recorded at first grading (ISO 8601 format)
- Registration status determined by checking if score is non-empty (blank = not graded, non-blank = graded)
- New columns added automatically when grading new homework
- Each student can have different grading status for each homework independently

## Project Structure

```
proj-OR-Grading/
├── scripts/                         # Python modules and CLI entry point
│   ├── main.py                      # Command-line interface and workflows
│   ├── grader.py                    # LLM integration and grading logic
│   ├── parser.py                    # File loading and content parsing
│   ├── reporter.py                  # PDF generation and CSV management
│   └── utils.py                     # File I/O and utility functions
├── data/                            # Student assignment files
├── resources/                       # Question and answer files
├── outputs/                         # Generated output files
│   ├── grading_results.csv          # Grading records (all homeworks)
│   ├── grades/                      # PDF reports organized by homework
│   │   ├── hw_1/                    # First homework folder
│   │   │   ├── 2451760_hw_1.pdf
│   │   │   └── 2452701_hw_1.pdf
│   │   └── hw_2/                    # Second homework folder
│   │       ├── 2451760_hw_2.pdf
│   │       └── 2453118_hw_2.pdf
│   └── responses/                   # Raw LLM response logs
│       ├── 2451760.txt              # Latest response for student 2451760
│       ├── 2452701.txt              # Latest response for student 2452701
│       └── 2453118.txt              # Latest response for student 2453118
├── .env                             # Configuration (API keys, paths)
└── README.md
```

### Module Reference

| Module | Purpose |
|--------|---------|
| `main.py` | CLI entry point; handles command parsing and coordinates workflows (grade, regenerate) |
| `grader.py` | LLM integration; generates grades and comments via OpenAI API |
| `parser.py` | File loading and JSON/text parsing to extract scores and comments |
| `reporter.py` | PDF generation and CSV creation/updates with dynamic homework columns |
| `utils.py` | Reusable file I/O, CSV operations, and timestamp utilities |