import os
import csv
import glob
import logging
from datetime import datetime
from openai import OpenAI

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


def update_csv_field(csv_path, student_id, hw_n, field, value):
    """更新CSV中特定学生特定字段的值
    
    Args:
        csv_path: CSV文件路径
        student_id: 学号
        hw_n: 作业次数
        field: 字段名（如'score_hw_1', 'comment_hw_1'）
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


def add_hw_columns(csv_path, new_hw_n):
    """添加新的作业列到CSV文件
    
    Args:
        csv_path: CSV文件路径
        new_hw_n: 新的作业次数（如2表示添加第2次的列）
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        records = read_grading_csv(csv_path)
        fieldnames = get_csv_fieldnames(csv_path)
        
        if fieldnames is None:
            logger.error(f"CSV文件 {csv_path} 无效")
            return False
        
        score_field = f'score_hw_{new_hw_n}'
        comment_field = f'comment_hw_{new_hw_n}'
        
        # 检查列是否已存在
        if score_field in fieldnames:
            logger.warning(f"第{new_hw_n}次作业的列已存在")
            return False
        
        # 找到所有现有的作业编号
        existing_hw_nums = set()
        for field in fieldnames:
            if field.startswith('score_hw_'):
                hw_num = int(field.split('_')[2])
                existing_hw_nums.add(hw_num)
        
        # 按顺序重建字段名（先timestamp和student_id，然后按顺序放所有score，最后所有comment）
        base_fields = ['timestamp', 'student_id']
        score_fields = []
        comment_fields = []
        
        all_hw_nums = sorted(list(existing_hw_nums) + [new_hw_n])
        for hw_num in all_hw_nums:
            score_fields.append(f'score_hw_{hw_num}')
            comment_fields.append(f'comment_hw_{hw_num}')
        
        new_fieldnames = base_fields + score_fields + comment_fields
        
        # 为现有记录初始化新列（为空）
        for record in records:
            record[score_field] = ''
            record[comment_field] = ''
        
        # 写回CSV文件
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=new_fieldnames)
            writer.writeheader()
            writer.writerows(records)
        
        logger.info(f"成功添加第{new_hw_n}次作业的列")
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
        'score_hw_1',
        'comment_hw_1'
    ]
    
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
    
    return fieldnames


def create_client():
    """创建OpenAI客户端"""
    return OpenAI(
        base_url=os.getenv("API_BASE_URL"),
        api_key=os.getenv("API_KEY")
    )


def load_resources(resources_dir):
    """加载题目和答案资源
    
    Args:
        resources_dir: 资源目录路径
        
    Returns:
        (questions_list, answers_list) - 题目和答案文件路径列表
    """
    files = glob.glob(os.path.join(resources_dir, "*"))
    q = [f for f in files if os.path.isfile(f) and 'answer' not in f.lower() and '答案' not in f]
    a = [f for f in files if os.path.isfile(f) and ('answer' in f.lower() or '答案' in f)]
    return q, a


def group_files_by_student(data_dir):
    """按学号分组学生作业文件
    
    Args:
        data_dir: 数据目录路径
        
    Returns:
        字典，键为学号，值为该学生的作业文件列表
    """
    files = glob.glob(os.path.join(data_dir, "*"))
    files.extend(glob.glob(os.path.join(data_dir, "*", "*")))
    students = {}
    for file in files:
        if os.path.isfile(file):
            student_id = os.path.basename(file).split('_')[0]
            students.setdefault(student_id, []).append(file)
    return students
