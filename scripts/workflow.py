import os
import glob
import logging
from openai import OpenAI

import grader
import parser
import reporter
import utils

logger = logging.getLogger(__name__)


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


def grade_students(client, model, data_dir, resources_dir, outputs_dir, responses_dir, 
                   csv_path, attempt_n=1):
    """对学生作业进行评分的主流程
    
    Args:
        client: OpenAI客户端
        model: 使用的模型名称
        data_dir: 学生作业数据目录
        resources_dir: 题目和答案资源目录
        outputs_dir: 输出目录
        responses_dir: 原始响应保存目录
        csv_path: CSV成绩记录文件路径
        attempt_n: 评分次数（默认为1）
        
    Returns:
        成功处理的学生数量
    """
    os.makedirs(outputs_dir, exist_ok=True)
    os.makedirs(responses_dir, exist_ok=True)
    
    # 初始化CSV文件（如果不存在）
    if not os.path.exists(csv_path):
        utils.initialize_csv(csv_path)
        logger.info(f"成功初始化CSV文件: {csv_path}")
    
    # 加载资源
    questions, answers = load_resources(resources_dir)
    students = group_files_by_student(data_dir)
    
    if not students:
        logger.error("未找到学生作业文件！")
        return 0
    
    processed_count = 0
    final_results = []
    
    for student_id, files in students.items():
        logger.info(f"正在处理学生: {student_id}")
        
        # 检查该学生的该次评分是否已登记
        if reporter.check_student_registered(csv_path, student_id, attempt_n):
            logger.info(f"学生 {student_id} 第{attempt_n}次评分已登记，跳过")
            continue
        
        # 1. 获取LLM评分内容
        raw_content = grader.grade_assignment(client, model, questions, answers, files)
        
        if raw_content:
            # 2. 保存原始响应
            grader.save_raw_response(raw_content, student_id, responses_dir, attempt_n)
            
            # 3. 直接解析raw_content
            score, comment = parser.parse_grade_content(raw_content)
            
            # 4. 生成报告PDF
            pdf_path = os.path.join(outputs_dir, f"{student_id}_attempt_{attempt_n}.pdf")
            reporter.create_graded_pdf(student_id, files, score, comment, pdf_path)
            
            # 5. 记录结果（包含时间戳）
            timestamp = utils.generate_timestamp()
            final_results.append({
                'timestamp': timestamp,
                'student_id': student_id,
                'score': score,
                'comment': comment,
                'attempt_n': attempt_n
            })
            
            processed_count += 1
            logger.info(f"学生 {student_id} 评分完成: 得分 {score}, 评语 '{comment}'")
        else:
            logger.error(f"学生 {student_id} 评分过程中止")
    
    # 导出汇总表
    if final_results:
        reporter.export_csv(final_results, csv_path, attempt_n)
        logger.info(f"所有批改任务已完成！共处理 {processed_count} 名学生")
    
    return processed_count


def regenerate_comments_batch(client, model, csv_path, attempt_n, student_ids=None):
    """根据现有成绩批量重新生成评语
    
    Args:
        client: OpenAI客户端
        model: 使用的模型名称
        csv_path: CSV成绩记录文件路径
        attempt_n: 评分次数
        student_ids: 指定的学号列表，如果为None则处理所有该次数的已登记学生
        
    Returns:
        成功更新的学生数量
    """
    records = utils.read_grading_csv(csv_path)
    
    if not records:
        logger.error(f"CSV文件 {csv_path} 不存在或为空")
        return 0
    
    # 确定要处理的学生
    target_students = []
    score_field = f'score_attempt_{attempt_n}'
    comment_field = f'comment_attempt_{attempt_n}'
    is_registered_field = f'is_registered_attempt_{attempt_n}'
    
    for record in records:
        # 检查该次数的列是否存在
        if score_field not in record:
            logger.warning(f"CSV中不存在第{attempt_n}次评分的列，请先添加")
            return 0
        
        student_id = record.get('student_id')
        score_str = record.get(score_field, '').strip()
        is_registered = record.get(is_registered_field, 'False').strip() == 'True'
        
        # 如果指定了学号列表，则只处理在列表中的学生
        if student_ids and student_id not in student_ids:
            continue
        
        # 只处理有成绩且已登记的学生
        if score_str and is_registered:
            try:
                score = int(score_str)
                target_students.append((student_id, score))
            except ValueError:
                logger.warning(f"学生 {student_id} 的成绩格式无效: {score_str}")
    
    if not target_students:
        logger.info("没有找到需要处理的学生")
        return 0
    
    updated_count = 0
    
    for student_id, score in target_students:
        logger.info(f"正在为学生 {student_id} 生成第{attempt_n}次评语 (成绩: {score})")
        
        # 调用LLM生成评语
        new_comment = grader.generate_comment_from_score(client, model, score)
        
        if new_comment:
            # 更新CSV中的评语
            if utils.update_csv_field(csv_path, student_id, attempt_n, comment_field, new_comment):
                logger.info(f"学生 {student_id} 的评语已更新: '{new_comment}'")
                updated_count += 1
            else:
                logger.error(f"更新学生 {student_id} 的评语失败")
        else:
            logger.error(f"为学生 {student_id} 生成评语失败")
    
    logger.info(f"批量生成评语完成！共更新 {updated_count} 名学生")
    return updated_count
