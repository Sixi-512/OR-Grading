import json
import re
import logging
import utils

logger = logging.getLogger(__name__)


def parse_fallback(text):
    """如果JSON解析失败，使用正则匹配"""
    score_match = re.search(r'(score|得分)[:：]\s*(\d+)', text, re.IGNORECASE)
    score = int(score_match.group(2)) if score_match else 0

    comment_match = re.search(r"(comment|评语)[:：]\s*[\"']?([^\"'}\n]+)", text, re.IGNORECASE)
    comment = comment_match.group(2).strip()[:30] if comment_match else "评分解析异常"
    
    return score, comment


def load_grade_file(file_path):
    """读取文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容，读取失败返回None
    """
    return utils.read_file_content(file_path)


def parse_grade_content(content):
    """解析成绩内容（JSON格式）
    
    Args:
        content: 包含成绩和评语的内容字符串（JSON格式）
        
    Returns:
        (score, comment) 元组，解析失败时score为0，comment为错误信息
    """
    if not content:
        logger.error("内容为空")
        return 0, "内容为空"
    
    try:
        data = json.loads(content)
        score = data.get('score', 0)
        comment = data.get('comment', '无评语')
        return score, comment
    except json.JSONDecodeError:
        logger.warning("JSON解析失败，尝试备选方案...")
        return parse_fallback(content)
    except Exception as e:
        logger.error(f"解析成绩内容出错: {e}")
        return 0, "解析失败"


def get_grade_from_file(file_path):
    """读取并解析txt文件中的成绩
    
    Args:
        file_path: 文件路径
        
    Returns:
        (score, comment) 元组
    """
    content = load_grade_file(file_path)
    if content is None:
        return 0, "读取失败"
    return parse_grade_content(content)