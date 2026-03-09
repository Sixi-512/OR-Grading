# Operation Research Assignment Automatic Correction and Grading (OR-AACG)

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

## Directory Structure
```
proj-OR-Grading
├── data/                                       # Student assignment files (PDF, JPG, PNG)
│   └── [folder]/[student_id]_[...]
├── outputs/
│   ├── [student_id]_attempt_N.pdf              # Individual graded assignments
│   ├── grades/
│   │   └── grading_results.csv                 # Summary CSV with multi-attempt records
│   └── responses/
│       └── [student_id]_grading_attempt_N.txt  # Raw LLM responses
├── resources/                                  # Assignment questions and answers (PDF, JPG, PNG)
├── scripts/                                    # Python modules
│   ├── main.py                                 # CLI entry point
│   ├── workflow.py                             # Business logic workflows
│   ├── grader.py                               # LLM interaction & grading
│   ├── parser.py                               # Grade content parsing
│   ├── reporter.py                             # PDF & CSV generation
│   └── utils.py                                # Utility functions
├── .env                                        # Environment configuration
└── README.md
```

## Configuration

### .env File
Create a `.env` file in the project root:
```
API_BASE_URL=https://your-api-endpoint.com/v1
API_KEY=your-api-key
MODEL=your-model-name
DATA_DIR=./data
RESOURCES_DIR=./resources
OUTPUTS_DIR=./outputs
RESPONSES_DIR=./outputs/responses
CSV_PATH=./outputs/grades/grading_results.csv
```

## Quick Start

### 1. Prepare your data:
- Place student assignments in `data/` directory with filenames like `student_id_xxx.ext`
- Place assignment questions and answers in `resources/` directory
- Question files should not contain "答案" or "answer" in the filename
- Answer files should contain "答案" or "answer" in the filename

### 2. Configure .env file (see Configuration section above)

### 3. Run grading:
```bash
# First grading attempt (run from project root)
python scripts/main.py grade

# Second grading attempt (will add new columns to CSV)
python scripts/main.py grade --attempt 2
```

### 4. Check results in `outputs/` directory:
- Individual graded PDFs named by student ID and attempt
- `grades/grading_results.csv` with all scores, comments, and registration status

## Command Reference

### `grade` Command
Grade student assignments for a specified attempt number.

```bash
python scripts/main.py grade [--attempt N]
```

**Arguments:**
- `--attempt N`: Specify attempt number (default: 1)

**Examples:**
```bash
# Grade with default attempt 1
python scripts/main.py grade

# Grade for attempt 2
python scripts/main.py grade --attempt 2
```

**Behavior:**
1. Checks CSV for already-registered students
2. Skips students whose scores are already recorded
3. Calls LLM for ungraded students
4. Creates/extends CSV with new attempt columns if needed
5. Marks records as registered after score + comment are saved
6. Generates PDF reports for each student

### `regenerate-comments` Command
Regenerate feedback comments for existing scores without calling LLM for grading.

```bash
python scripts/main.py regenerate-comments --attempt N [--students ID1,ID2,...]
```

**Arguments:**
- `--attempt N`: Attempt number to regenerate comments for (required)
- `--students IDs`: Comma-separated student IDs (optional, defaults to all students)

**Examples:**
```bash
# Regenerate comments for all students in attempt 1
python scripts/main.py regenerate-comments --attempt 1

# Regenerate comments for specific students in attempt 2
python scripts/main.py regenerate-comments --attempt 2 --students 2451760,2452701

# Regenerate for multiple specific students
python scripts/main.py regenerate-comments --attempt 1 --students 2451760,2452701,2453118
```

**Behavior:**
1. Loads existing scores from `score_attempt_N` column
2. Calls LLM to generate feedback from score alone
3. Updates `comment_attempt_N` column for each student
4. Keeps `is_registered_attempt_N` status unchanged

## CSV File Format

The `grading_results.csv` file maintains a record of all grading attempts with multi-attempt support:

**Example:**
```csv
timestamp,student_id,score_attempt_1,comment_attempt_1,is_registered_attempt_1,score_attempt_2,comment_attempt_2,is_registered_attempt_2
2026-03-09T10:30:45,2451760,85,步骤清晰,True,87,有改进,True
2026-03-09T10:31:15,2452701,78,计算有误,True,,未评,False
2026-03-09T10:32:00,2453118,,未评,False,92,逻辑清晰,True
```

**Column Structure:**
- `timestamp`: ISO 8601 format timestamp of first grading
- `student_id`: Student ID (primary identifier)
- `score_attempt_N`: Score for attempt N (0-100)
- `comment_attempt_N`: Feedback comment for attempt N
- `is_registered_attempt_N`: Registration status (True=recorded, False=not recorded)

**Key Features:**
- **Multi-attempt support**: Each grading attempt adds 3 new columns
- **Independent scoring**: Each attempt has separate score, comment, and registration status
- **Smart skipping**: Students with `is_registered_attempt_N=True` are skipped in subsequent gradings
- **Auto-registration**: Set to `True` only when both score AND comment are recorded
- **Column extension**: New attempt columns created automatically on first use
- **Timestamp tracking**: Records when grading was first performed

## File Organization

### Student Assignment Files
Format: `student_id_other_details.ext`
- Stored in `data/` directory and subdirectories
- Examples: `2451760_作业2.pdf`, `2452701_submission.jpg`, `2453118_assignment.png`
- Supported formats: PDF, JPG, PNG

### Question and Answer Files
Stored in `resources/` directory:
- **Questions**: Files NOT containing "答案" or "answer" in filename
- **Answers**: Files containing "答案" or "answer" in filename
- Supported formats: PDF, JPG, PNG, etc.

### Output Files
Generated in `outputs/` directory:
- `[student_id]_attempt_[N].pdf`: Individual graded assignments with score and comments
- `grades/grading_results.csv`: Summary record of all grading attempts
- `responses/[student_id]_grading_attempt_[N].txt`: Raw LLM JSON responses (for logging)
## Module Architecture

### Core Modules

#### `main.py` - CLI Entry Point
Command-line interface with argument parsing. Supports:
- `grade [--attempt N]`: Grade student assignments
- `regenerate-comments --attempt N [--students ID1,ID2,...]`: Regenerate feedback

#### `workflow.py` - Business Logic
High-level workflows coordinating multiple components:
- `grade_students()`: Main grading pipeline (file loading → LLM → PDF/CSV generation)
- `regenerate_comments_batch()`: Batch feedback regeneration from existing scores

#### `grader.py` - LLM Integration
Handles all LLM interactions:
- `grade_assignment()`: Grade assignment using LLM with multi-modal input
- `generate_comment_from_score()`: Generate feedback from score alone
- `save_raw_response()`: Store raw LLM responses

#### `parser.py` - Content Parsing
Separates file I/O from parsing logic:
- `load_grade_file()`: Read file content
- `parse_grade_content()`: Parse JSON/text to extract score and comment
- `get_grade_from_file()`: Convenience wrapper combining both

#### `reporter.py` - Output Generation
Generates reports and manages CSV:
- `create_graded_pdf()`: Generate individual graded PDF
- `export_csv()`: Handle CSV creation/updates with dynamic columns
- `check_student_registered()`: Verify if grading is recorded
- `set_student_registered()`: Mark grading as registered

#### `utils.py` - Utility Functions
Reusable utilities for file I/O and CSV operations:
- `read_file_content()`: Read files safely
- `write_file_content()`: Write files with error handling
- `generate_timestamp()`: ISO 8601 timestamps
- `read_grading_csv()`: Load CSV records
- `update_csv_field()`: Update specific CSV cells
- `add_attempt_columns()`: Extend CSV with new attempt columns
- `initialize_csv()`: Create new CSV with headers

## Workflow Examples

### Example 1: First Grading
```bash
python scripts/main.py grade --attempt 1
```
1. Load student files and resources
2. Check CSV for existing records
3. Skip already-graded students
4. Call LLM for each ungraded student
5. Parse LLM response and save raw response
6. Generate PDF reports
7. Update CSV (creates first attempt columns if new)
8. Mark records as registered

### Example 2: Multiple Grading Attempts
```bash
# First attempt
python scripts/main.py grade --attempt 1

# Second attempt (with possibly different rubrics)
python scripts/main.py grade --attempt 2
```
1. CSV automatically adds 3 new columns: score_attempt_2, comment_attempt_2, is_registered_attempt_2
2. New attempt columns initialized to False registration status
3. Previous attempt records remain unchanged
4. Only students without recorded scores for attempt 2 are processed

### Example 3: Regenerate Feedback
```bash
python scripts/main.py regenerate-comments --attempt 1
```
1. Load all scores from `score_attempt_1` column
2. For each student with a score:
   - Call LLM to generate comment from score alone
   - Update `comment_attempt_1` column
3. Registration status remains True

### Example 4: Regenerate for Specific Students
```bash
python scripts/main.py regenerate-comments --attempt 2 --students 2451760,2452701
```
1. Only process students 2451760 and 2452701
2. Use their scores from `score_attempt_2`
3. Generate new comments and update CSV

## Error Handling

- **Missing .env file**: Script exits with clear error message
- **Invalid CSV**: Detailed logging for CSV read/write failures
- **LLM API errors**: Logged and processing continues for next student
- **File I/O errors**: Caught with fallback responses
- **Malformed JSON**: Fallback regex parsing attempts

## Troubleshooting

### Students skipped even though not graded
- Check `is_registered_attempt_N` column - may need to reset to False manually

### CSV columns mismatch
- Ensure all student records have the same columns
- Use `add_attempt_columns()` utility function to extend existing CSV

### LLM API timeout
- Check API_BASE_URL and API_KEY in .env
- Ensure network connectivity
- Verify model name exists

## License
[Add your license here]
