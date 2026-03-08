from openai import OpenAI
import base64
import mimetypes
import os
import csv
import glob
import json
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black
from dotenv import load_dotenv
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path

# Configuration
load_dotenv() 
DATA_DIR = os.getenv("DATA_DIR")
RESOURCES_DIR = os.getenv("RESOURCES_DIR")
OUTPUTS_DIR  = os.getenv("OUTPUTS_DIR")
RESPONSES_DIR = os.getenv("RESPONSES_DIR")
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")


def encode_image_to_base64(file_path):
    """Encode a file to base64 for API transmission."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_mime_type(file_path):
    """Get the MIME type of a file."""
    return mimetypes.guess_type(file_path)[0]


def get_student_id(filename):
    """Extract student ID from filename (part before first underscore)."""
    return filename.split('_')[0]


def group_files_by_student(data_dir):
    """Group assignment files by student ID."""
    files = glob.glob(os.path.join(data_dir, "*"))
    # Also search subdirectories
    files.extend(glob.glob(os.path.join(data_dir, "*", "*")))
    students = {}
    for file in files:
        filename = os.path.basename(file)
        if os.path.isfile(file):
            student_id = get_student_id(filename)
            if student_id not in students:
                students[student_id] = []
            students[student_id].append(file)
    return students


def load_resources(resources_dir):
    """Load all assignment questions and answer files."""
    files = glob.glob(os.path.join(resources_dir, "*"))
    questions = []
    answers = []
    for file in files:
        if os.path.isfile(file):
            # Separate by filename patterns or let model handle both
            if 'answer' in file.lower() or '答案' in file:
                answers.append(file)
            else:
                questions.append(file)
    return questions, answers


def build_grading_prompt(questions_files, answers_files, student_files):
    """Build the prompt for grading a student's assignment."""
    prompt_parts = [
        "你是一位运筹学作业批改专家。请根据以下题目和答案，批改学生的作业。",
        "\n【作业题目】"
    ]
    # Add questions as images
    for i, q_file in enumerate(questions_files):
        prompt_parts.append(f"\n题目 {i+1}:")

    prompt_parts.append("\n【参考答案】")
    for i, a_file in enumerate(answers_files):
        prompt_parts.append(f"\n答案 {i+1}:")

    prompt_parts.extend([
        "\n【学生作业】",
        "请批改学生的作业，要求：",
        "1. 以百分制打分（0-100分）",
        "2. 写上评语，说明错误在哪里，尽量控制在30字之内",
        "\n请按以下JSON格式输出（只输出JSON，不要有其他内容）：",
        '{"score": 85, "comment": "计算正确，步骤清晰"}'
    ])
    return "\n".join(prompt_parts)


def parse_fallback(text):
    """Fallback parsing if JSON parsing fails."""
    # Try to extract score
    score_match = re.search(r'(score|得分)[:：]\s*(\d+)', text, re.IGNORECASE)
    score = int(score_match.group(2)) if score_match else 0

    # Try to extract comment
    comment_match = re.search(r"(comment|评语)[:：]\s*[\"']?([^\"'}\n]+)", text, re.IGNORECASE)
    comment = comment_match.group(2).strip()[:30] if comment_match else text[-30:] if len(text) > 30 else text

    return score, comment


def grade_assignment(client, model, questions, answers, student_files):
    """Grade a student's assignment using Gemini model."""
    # Combine all files for API call
    all_files = questions + answers + student_files

    content = [{"type": "text", "text": build_grading_prompt(questions, answers, student_files)}]

    for file_path in all_files:
        base64_data = encode_image_to_base64(file_path)
        mime_type = get_mime_type(file_path) or "image/jpeg"
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}
        })

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"}
        )

        # Parse JSON response
        try:
            content = response.choices[0].message.content
            result = json.loads(content)
            score = result.get('score', 0)
            comment = result.get('comment', '')
            return score, comment, content
        except json.JSONDecodeError:
            # Fallback parsing
            text = response.choices[0].message.content
            return parse_fallback(text)
    except Exception as e:
        print(f"Error grading: {e}")
        return 0, f"评分失败: {str(e)}"


def create_graded_pdf(student_id, student_files, score, comment, output_path):
    """Create a PDF with student's assignment, score, and comment."""
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    # Add Chinese font support (Windows)
    try:
        pdfmetrics.registerFont(TTFont('Microsoft YaHei', './resources/msyh.ttc', subfontIndex=0))
        chinese_font = 'Microsoft YaHei'
    except:
        chinese_font = 'Helvetica'

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=1,
        textColor=black,
        fontName=chinese_font
    )
    story.append(Paragraph(f"运筹学作业批改 - 学号: {student_id}", title_style))
    story.append(Spacer(1, 20))

    # Score and Comment
    score_style = ParagraphStyle(
        'Score',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=10,
        fontName=chinese_font
    )
    story.append(Paragraph(f"得分: {score}分 / 100", score_style))
    story.append(Paragraph(f"评语: {comment}", score_style))
    story.append(Spacer(1, 30))

    # Student's assignment images
    story.append(Paragraph("学生作业:", score_style))
    story.append(Spacer(1, 10))

    has_pdf = False
    pdf_path = []
    for file_path in student_files:
        try:
            path = Path(file_path)
            ext = path.suffix.lower()

            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                img = RLImage(file_path)
                # Calculate aspect ratio and resize
                width = 6 * inch
                img.drawWidth = width
                img.drawHeight = width * (img.imageHeight / img.imageWidth)
                story.append(img)
                story.append(Spacer(1, 10))
            elif ext == '.pdf':
                pdf_path.append(str(file_path))
                has_pdf = True
        except Exception as e:
            story.append(Paragraph(f"无法显示文件: {os.path.basename(file_path)}", score_style))

    doc.build(story)
    if has_pdf:
        merge_pdf_to_writer(output_path, pdf_path)


def merge_pdf_to_writer(output_path, pdf_paths):
    """把学生的 PDF 加到现有的 PdfWriter 里"""
    pdf_writer = PdfWriter()
    reader = PdfReader(output_path)
    for page in reader.pages:
        pdf_writer.add_page(page)
    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            pdf_writer.add_page(page)
    with open(output_path, "wb") as output_file:
        pdf_writer.write(output_file)


def export_csv(results, output_path):
    """Export grading results to CSV file."""
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['学号', '得分', '评语'])
        for student_id, score, comment in results:
            writer.writerow([student_id, score, comment])


def save_to_txt(content, path):
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)


def main():
    """Main function to run the grading process."""
    print("=" * 50)
    print("Operation Research Assignment Grading System")
    print("=" * 50)

    # Ensure outputs directory exists
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    # Initialize client
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # Load resources
    print("\nLoading assignment questions and answers...")
    questions, answers = load_resources(RESOURCES_DIR)
    print(f"Found {len(questions)} question files and {len(answers)} answer files")

    # Group student files
    print("\nProcessing student assignments...")
    students = group_files_by_student(DATA_DIR)
    print(f"Found {len(students)} students")

    if not students:
        print("No student assignments found in data directory!")
        return

    # Grade each student
    results = []
    for student_id, files in students.items():
        print(f"\nGrading student {student_id}...")
        print(f"  Files: {[os.path.basename(f) for f in files]}")
        # score, comment, content = grade_assignment(client, MODEL, questions, answers, files)
        score = 85
        comment = "计算正确，步骤清晰"
        content = str(score) + " " + comment
        save_to_txt(content, os.path.join(RESPONSES_DIR, f"{student_id}_grading.txt"))
        results.append((student_id, score, comment))

        # Generate PDF
        pdf_path = os.path.join(OUTPUTS_DIR, f"{student_id}.pdf")
        create_graded_pdf(student_id, files, score, comment, pdf_path)
        print(f"  Score: {score}, Comment: {comment}")
        print(f"  PDF saved to: {pdf_path}")

    # Export CSV
    csv_path = os.path.join(OUTPUTS_DIR, "grading_results.csv")
    export_csv(results, csv_path)
    print(f"\n{'=' * 50}")
    print(f"CSV summary saved to: {csv_path}")
    print("Grading completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
