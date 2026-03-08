# Operation Research Assignment Automatic Correction and Grading (OR-AACG)

## Description
This system automatically grades Operation Research assignments using AI (Gemini model). It reads student submissions, compares them with provided questions and answers, and generates scores with feedback comments.

## Requirements

### Environment
- Python 3.8 or higher

### Dependencies
Install the required Python packages:
```bash
pip install openai reportlab Pillow
```

## Directory Structure
```
proj-OR-Grading
├── data/                   # Student assignment files (PDF, JPG, PNG)
│   └── [student_id]_[...]
├── outputs/                # Graded results
│   ├── [student_id].pdf          # Individual graded assignments
│   └── grading_results.csv       # Summary CSV
├── resourses/              # Assignment questions and answers (PDF, JPG, PNG)
├── scripts/                # Python scripts
│   └── grader.py           # Main grading script
└── README.md
```

## Usage

### 1. Prepare your data:
- Place student assignments in `data/` directory with filenames like `student_id_xxx.ext`
- Place assignment questions and answers in `resourses/` directory

### 2. Run the grading script:
```bash
python scripts/grader.py
```

### 3. Check results in `outputs/` directory:
- Individual graded PDFs named by student ID
- `grading_results.csv` with all scores and comments

## File Naming Convention

### Student Files
Format: `student_id_other_details.ext`
- Example: `2451760_作业2.pdf`, `2452701_submission.jpg`
- All files with the same student ID (text before first underscore) are grouped together

### Resources
- Question files: Any file in `resourses/` not containing "answer" or "答案" in the filename
- Answer files: Files in `resourses/` containing "answer" or "答案" in the filename

## Output Format

### Graded PDF
Each student gets a PDF file containing:
- Title with student ID
- Score (0-100)
- Comment (feedback, under 30 words in Chinese)
- Original assignment images

### CSV Summary
`grading_results.csv` contains:
- Student ID (学号)
- Score (得分)
- Comment (评语)

## API Configuration

Edit the API configuration in `scripts/grader.py` if needed:
```python
API_BASE_URL = "https://jeniya.chat/v1"
API_KEY = "your_api_key"
MODEL = "gemini-2.5-flash-preview-05-20"
```

## Features

1. **Multi-format Support**: Processes PDF, JPG, and PNG files
2. **Automatic Grouping**: Groups files by student ID from filenames
3. **AI-Powered Grading**: Uses Gemini model for intelligent grading
4. **Detailed Feedback**: Provides specific comments on errors
5. **Comprehensive Output**: Generates both individual PDFs and a summary CSV

## License
[Add your license here]
