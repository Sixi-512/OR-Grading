import os
import sys
import argparse
import logging
from dotenv import load_dotenv

import grader
import parser
import reporter
import utils

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()


def grade_students(client, model, data_dir, resources_dir, outputs_dir, responses_dir, csv_path, hw_n=1):
    """对学生作业进行评分的主流程"""
    os.makedirs(outputs_dir, exist_ok=True)
    os.makedirs(responses_dir, exist_ok=True)
    
    if not os.path.exists(csv_path):
        utils.initialize_csv(csv_path)
    
    questions, answers = utils.load_resources(resources_dir)
    students = utils.group_files_by_student(data_dir)
    
    if not students:
        logger.error("未找到学生作业文件！")
        return 0
    
    processed_count = 0
    final_results = []
    
    for student_id, files in students.items():
        if reporter.check_student_has_score(csv_path, student_id, hw_n):
            continue
        
        raw_content = grader.grade_assignment(client, model, questions, answers, files)
        
        if raw_content:
            grader.save_raw_response(raw_content, student_id, responses_dir)
            score, comment = parser.parse_grade_content(raw_content)
            hw_folder = os.path.join(outputs_dir, f'hw_{hw_n}')
            os.makedirs(hw_folder, exist_ok=True)
            pdf_path = os.path.join(hw_folder, f"{student_id}_hw_{hw_n}.pdf")
            reporter.create_graded_pdf(student_id, files, score, comment, pdf_path)
            
            final_results.append({
                'timestamp': utils.generate_timestamp(),
                'student_id': student_id,
                'score': score,
                'comment': comment,
                'hw_n': hw_n
            })
            
            processed_count += 1
            logger.info(f"student_id: {student_id}, score_hw_{hw_n}: {score}, comment_hw_{hw_n}: {comment}")
        else:
            logger.error(f"学生 {student_id} 评分过程中止")
    
    if final_results:
        reporter.export_csv(final_results, csv_path, hw_n)
    
    return processed_count


def regenerate_comments_batch(client, model, csv_path, hw_n, student_ids=None):
    """根据现有成绩批量重新生成评语"""
    records = utils.read_grading_csv(csv_path)
    
    if not records:
        logger.error(f"CSV文件 {csv_path} 不存在或为空")
        return 0
    
    target_students = []
    score_field = f'score_hw_{hw_n}'
    comment_field = f'comment_hw_{hw_n}'
    
    for record in records:
        if score_field not in record:
            logger.warning(f"CSV中不存在第{hw_n}次作业的列，请先添加")
            return 0
        
        student_id = record.get('student_id')
        score_str = record.get(score_field, '').strip()
        
        if student_ids and student_id not in student_ids:
            continue
        
        if score_str:
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
        new_comment = grader.generate_comment_from_score(client, model, score)
        
        if new_comment:
            if utils.update_csv_field(csv_path, student_id, hw_n, comment_field, new_comment):
                logger.info(f"student_id: {student_id}, score_hw_{hw_n}: {score}, comment_hw_{hw_n}: {new_comment}")
                updated_count += 1
            else:
                logger.error(f"更新学生 {student_id} 的评语失败")
        else:
            logger.error(f"为学生 {student_id} 生成评语失败")
    
    return updated_count


def parse_opt():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运筹学作业批改系统')
    parser.add_argument('command', choices=['grade', 'regenerate'], help='执行命令（grade: 评分，regenerate: 重新生成评语）')
    parser.add_argument('--data-dir', type=str, required=True, help='学生作业文件目录')
    parser.add_argument('--resources-dir', type=str, required=True, help='问题和答案资源目录')
    parser.add_argument('--hw', type=int, default=1, help='作业号（默认为1）')
    parser.add_argument('--students', type=str, help='学号列表（逗号分隔，如"2451760,2452701"），仅用于regenerate命令')
    return parser.parse_args()


def main():
    """主函数：执行命令行操作"""
    opt = parse_opt()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 从命令行参数获取数据和资源目录
    DATA_DIR = opt.data_dir
    RESOURCES_DIR = opt.resources_dir
    
    # 验证目录存在性
    if not os.path.isdir(DATA_DIR):
        logger.error(f"数据目录不存在: {DATA_DIR}")
        return 1
    
    if not os.path.isdir(RESOURCES_DIR):
        logger.error(f"资源目录不存在: {RESOURCES_DIR}")
        return 1
    
    # 固定输出目录
    OUTPUTS_DIR = os.path.join(project_root, "outputs")
    RESPONSES_DIR = os.path.join(OUTPUTS_DIR, "responses")
    CSV_PATH = os.path.join(OUTPUTS_DIR, "grading_results.csv")
    MODEL = os.getenv("MODEL")
    
    if not MODEL:
        logger.error("缺少MODEL环境变量配置")
        return 1
    
    client = utils.create_client()
    
    if opt.command == 'grade':
        logger.info(f"开始第{opt.hw}次作业评分")
        
        processed_count = grade_students(
            client=client, model=MODEL, data_dir=DATA_DIR, resources_dir=RESOURCES_DIR,
            outputs_dir=OUTPUTS_DIR, responses_dir=RESPONSES_DIR, csv_path=CSV_PATH, hw_n=opt.hw
        )
        
        if processed_count > 0:
            logger.info(f"评分完成，共处理 {processed_count} 名学生")
            return 0
        else:
            logger.warning("未处理任何学生")
            return 1
    
    elif opt.command == 'regenerate':
        if not os.path.exists(CSV_PATH):
            logger.error(f"CSV文件不存在: {CSV_PATH}")
            return 1
        
        student_ids = None
        if opt.students:
            student_ids = [s.strip() for s in opt.students.split(',')]
        
        logger.info(f"开始重新生成第{opt.hw}次作业的评语")
        
        updated_count = regenerate_comments_batch(
            client=client, model=MODEL, csv_path=CSV_PATH, hw_n=opt.hw, student_ids=student_ids
        )
        
        if updated_count > 0:
            logger.info(f"评语生成完成，共更新 {updated_count} 名学生")
            return 0
        else:
            logger.warning("未更新任何学生的评语")
            return 1


if __name__ == "__main__":
    sys.exit(main())