import os
import csv
import logging
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
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
    except:
        chinese_font = 'Helvetica'
        logger.warning("未找到中文字体，PDF可能显示异常")

    score_style = ParagraphStyle('Score', parent=styles['Normal'], fontSize=14, fontName=chinese_font)
    story.append(Paragraph(f"运筹学作业批改 - 学号: {student_id}", styles['Heading1']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"得分: {score}分 / 100", score_style))
    story.append(Paragraph(f"评语: {comment}", score_style))
    story.append(Spacer(1, 30))

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
    logger.info(f"学号 {student_id} 的PDF报告已生成")

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


def check_student_registered(csv_path, student_id, attempt_n):
    """检查学生的指定次数评分是否已登记
    
    Args:
        csv_path: CSV文件路径
        student_id: 学号
        attempt_n: 评分次数
        
    Returns:
        True表示已登记，False表示未登记或未找到
    """
    record = utils.get_student_record(csv_path, student_id)
    if record is None:
        return False
    
    is_registered_field = f'is_registered_attempt_{attempt_n}'
    is_registered = record.get(is_registered_field, 'False').strip() == 'True'
    return is_registered


def set_student_registered(csv_path, student_id, attempt_n, value):
    """设置学生的指定次数评分登记状态
    
    Args:
        csv_path: CSV文件路径
        student_id: 学号
        attempt_n: 评分次数
        value: True/False 或 'True'/'False' 字符串
        
    Returns:
        成功返回True，失败返回False
    """
    is_registered_field = f'is_registered_attempt_{attempt_n}'
    value_str = 'True' if value is True or value == 'True' else 'False'
    return utils.update_csv_field(csv_path, student_id, attempt_n, is_registered_field, value_str)


def export_csv(results, csv_path, attempt_n=1):
    """导出成绩到CSV文件
    
    Args:
        results: 成绩结果列表，每项为字典，包含：
                 {'timestamp': '...', 'student_id': '...', 'score': 85, 'comment': '...', 'attempt_n': 1}
        csv_path: 输出CSV文件路径
        attempt_n: 评分次数
    """
    # 如果CSV不存在，初始化
    if not os.path.exists(csv_path):
        utils.initialize_csv(csv_path)
    
    # 读取现有记录
    records = utils.read_grading_csv(csv_path)
    fieldnames = utils.get_csv_fieldnames(csv_path)
    
    if fieldnames is None:
        logger.error(f"CSV文件 {csv_path} 无效")
        return
    
    # 检查是否需要添加新的尝试列
    score_field = f'score_attempt_{attempt_n}'
    comment_field = f'comment_attempt_{attempt_n}'
    is_registered_field = f'is_registered_attempt_{attempt_n}'
    
    needs_new_columns = score_field not in fieldnames
    
    if needs_new_columns:
        # 添加新列
        new_fieldnames = fieldnames + [score_field, comment_field, is_registered_field]
        for record in records:
            record[score_field] = ''
            record[comment_field] = ''
            record[is_registered_field] = 'False'
        fieldnames = new_fieldnames
    
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
                record['timestamp'] = timestamp
                record[score_field] = str(score)
                record[comment_field] = comment
                record[is_registered_field] = 'True'
                found = True
                break
        
        if not found:
            # 创建新记录
            new_record = {
                'timestamp': timestamp,
                'student_id': student_id,
                'score_attempt_1': '',
                'comment_attempt_1': '',
                'is_registered_attempt_1': 'False'
            }
            # 填充所有可能的尝试列
            if attempt_n > 1:
                for i in range(2, attempt_n + 1):
                    new_record[f'score_attempt_{i}'] = ''
                    new_record[f'comment_attempt_{i}'] = ''
                    new_record[f'is_registered_attempt_{i}'] = 'False'
            
            new_record[score_field] = str(score)
            new_record[comment_field] = comment
            new_record[is_registered_field] = 'True'
            records.append(new_record)
    
    # 写入CSV文件
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        logger.info(f"CSV汇总表已导出至 {csv_path}")
    except Exception as e:
        logger.error(f"导出CSV失败: {e}")