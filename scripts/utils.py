import os
import csv
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def read_file_content(file_path):
    """读取文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容字符串，读取失败返回None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件 {file_path} 失败: {e}")
        return None


def write_file_content(file_path, content):
    """写入文件内容
    
    Args:
        file_path: 文件路径
        content: 文件内容
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"写入文件 {file_path} 失败: {e}")
        return False


def generate_timestamp():
    """生成ISO 8601格式的时间戳
    
    Returns:
        时间戳字符串，格式: 2026-03-09T10:30:45
    """
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


def read_grading_csv(csv_path):
    """读取成绩CSV文件
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        列表形式的记录，每条记录为字典，文件不存在或读取失败返回空列表
    """
    if not os.path.exists(csv_path):
        return []
    
    try:
        records = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return []
            for row in reader:
                records.append(row)
        return records
    except Exception as e:
        logger.error(f"读取CSV文件 {csv_path} 失败: {e}")
        return []


def get_csv_fieldnames(csv_path):
    """获取CSV文件的列名
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        列名列表，文件不存在或读取失败返回None
    """
    if not os.path.exists(csv_path):
        return None
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            return headers
    except Exception as e:
        logger.error(f"读取CSV列名失败: {e}")
        return None


def get_student_record(csv_path, student_id):
    """获取特定学生的记录
    
    Args:
        csv_path: CSV文件路径
        student_id: 学号
        
    Returns:
        学生的记录字典，不存在返回None
    """
    records = read_grading_csv(csv_path)
    for record in records:
        if record.get('student_id') == student_id:
            return record
    return None


def update_csv_field(csv_path, student_id, attempt_n, field, value):
    """更新CSV中特定学生特定字段的值
    
    Args:
        csv_path: CSV文件路径
        student_id: 学号
        attempt_n: 尝试次数
        field: 字段名（如'score_attempt_1', 'comment_attempt_1', 'is_registered_attempt_1'）
        value: 新值
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        records = read_grading_csv(csv_path)
        fieldnames = get_csv_fieldnames(csv_path)
        
        if fieldnames is None or not records:
            logger.error(f"CSV文件 {csv_path} 无效")
            return False
        
        # 查找并更新记录
        found = False
        for record in records:
            if record.get('student_id') == student_id:
                record[field] = value
                found = True
                break
        
        if not found:
            logger.warning(f"未找到学号 {student_id} 的记录")
            return False
        
        # 写回CSV文件
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        
        return True
    except Exception as e:
        logger.error(f"更新CSV字段失败: {e}")
        return False


def add_attempt_columns(csv_path, new_attempt_n):
    """添加新的尝试列到CSV文件
    
    Args:
        csv_path: CSV文件路径
        new_attempt_n: 新的尝试次数（如2表示添加第2次的列）
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        records = read_grading_csv(csv_path)
        fieldnames = get_csv_fieldnames(csv_path)
        
        if fieldnames is None:
            logger.error(f"CSV文件 {csv_path} 无效")
            return False
        
        # 新增的列名
        new_columns = [
            f'score_attempt_{new_attempt_n}',
            f'comment_attempt_{new_attempt_n}',
            f'is_registered_attempt_{new_attempt_n}'
        ]
        
        # 检查列是否已存在
        if new_columns[0] in fieldnames:
            logger.warning(f"第{new_attempt_n}次的列已存在")
            return False
        
        # 添加新列到表头
        new_fieldnames = fieldnames + new_columns
        
        # 为现有记录初始化新列（得分、评语为空，未登记状态为False）
        for record in records:
            for col in new_columns[:-1]:
                record[col] = ''
            record[new_columns[-1]] = 'False'
        
        # 写回CSV文件
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=new_fieldnames)
            writer.writeheader()
            writer.writerows(records)
        
        logger.info(f"成功添加第{new_attempt_n}次评分的列")
        return True
    except Exception as e:
        logger.error(f"添加CSV列失败: {e}")
        return False


def initialize_csv(csv_path):
    """初始化CSV文件（如果不存在）
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        初始化的表头列表
    """
    fieldnames = [
        'timestamp',
        'student_id',
        'score_attempt_1',
        'comment_attempt_1',
        'is_registered_attempt_1'
    ]
    
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
    
    return fieldnames
