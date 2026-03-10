import os
import csv
import logging
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black
from PyPDF2 import PdfReader, PdfWriter
import utils

logger = logging.getLogger(__name__)

def create_graded_pdf(student_id, student_files, score, comment, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_path = os.path.join(project_root, 'resources', 'msyh.ttc')
    
    try:
        pdfmetrics.registerFont(TTFont('Microsoft YaHei', font_path, subfontIndex=0))
        chinese_font = 'Microsoft YaHei'
    except Exception as e:
        chinese_font = 'Helvetica'
        logger.warning(f"未找到中文字体，PDF中文可能显示异常: {e}")

    # 为标题和内容都应用中文字体
    heading_style = ParagraphStyle(
        'HeadingZH',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    score_style = ParagraphStyle(
        'Score',
        parent=styles['Normal'],
        fontSize=14,
        fontName=chinese_font,
        spaceAfter=8,
        leading=20
    )
    story.append(Paragraph(f"运筹学作业批改 - 学号: {student_id}", heading_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"得分: {score}分 / 100", score_style))
    story.append(Paragraph(f"评语: {comment}", score_style))
    story.append(Spacer(1, 20))

    pdf_paths = []
    for file_path in student_files:
        ext = Path(file_path).suffix.lower()
        if ext in ['.jpg', '.jpeg', '.png']:
            img = RLImage(file_path)
            width = 6 * inch
            img.drawWidth = width
            img.drawHeight = width * (img.imageHeight / img.imageWidth)
            story.append(img)
            story.append(Spacer(1, 10))
        elif ext == '.pdf':
            pdf_paths.append(file_path)

    doc.build(story)
    
    if pdf_paths:
        merge_pdfs(output_path, pdf_paths)

def merge_pdfs(base_pdf, extra_pdfs):
    writer = PdfWriter()
    for p in [base_pdf] + extra_pdfs:
        reader = PdfReader(p)
        for page in reader.pages:
            writer.add_page(page)
    with open(base_pdf, "wb") as f:
        writer.write(f)


def load_grading_records(csv_path):
    """加载成绩记录
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        记录列表
    """
    return utils.read_grading_csv(csv_path)


def check_student_has_score(csv_path, student_id, hw_n):
    """检查学生的指定作业成绩是否已登记（非空）
    
    Args:
        csv_path: CSV文件路径
        student_id: 学号
        hw_n: 作业号
        
    Returns:
        True表示已登记（成绩非空），False表示未登记或未找到
    """
    record = utils.get_student_record(csv_path, student_id)
    if record is None:
        return False
    
    score_field = f'score_hw_{hw_n}'
    score = record.get(score_field, '').strip()
    return bool(score)


def export_csv(results, csv_path, hw_n=1):
    """导出成绩到CSV文件
    
    Args:
        results: 成绩结果列表，每项为字典，包含：
                 {'timestamp': '...', 'student_id': '...', 'score': 85, 'comment': '...', 'hw_n': 1}
        csv_path: 输出CSV文件路径
        hw_n: 作业号
    """
    # 如果CSV不存在或为空，初始化
    if not os.path.exists(csv_path):
        utils.initialize_csv(csv_path)
    
    # 读取现有记录
    records = utils.read_grading_csv(csv_path)
    fieldnames = utils.get_csv_fieldnames(csv_path)
    
    if fieldnames is None or len(fieldnames) == 0:
        # CSV 文件为空或无效，重新初始化
        utils.initialize_csv(csv_path)
        fieldnames = utils.get_csv_fieldnames(csv_path)
        records = []
    
    score_field = f'score_hw_{hw_n}'
    comment_field = f'comment_hw_{hw_n}'
    
    # 检查是否需要添加新的作业列
    needs_new_columns = score_field not in fieldnames
    
    if needs_new_columns:
        # 使用add_hw_columns来添加新列并保持正确的顺序
        utils.add_hw_columns(csv_path, hw_n)
        # 重新读取fieldnames
        fieldnames = utils.get_csv_fieldnames(csv_path)
        records = utils.read_grading_csv(csv_path)
    
    # 更新或添加学生记录
    for result in results:
        student_id = result['student_id']
        score = result['score']
        comment = result['comment']
        timestamp = result.get('timestamp', utils.generate_timestamp())
        
        # 查找现有记录
        found = False
        for record in records:
            if record.get('student_id') == student_id:
                # 更新现有记录
                if record.get('timestamp', '').strip() == '':
                    record['timestamp'] = timestamp
                record[score_field] = str(score)
                record[comment_field] = comment
                found = True
                break
        
        if not found:
            # 创建新记录
            new_record = {'timestamp': timestamp, 'student_id': student_id}
            # 初始化所有字段为空
            for field in fieldnames:
                if field not in ['timestamp', 'student_id']:
                    new_record[field] = ''
            # 设置当前作业的成绩和评语
            new_record[score_field] = str(score)
            new_record[comment_field] = comment
            records.append(new_record)
    
    # 写入CSV文件
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
    except Exception as e:
        logger.error(f"导出CSV失败: {e}")