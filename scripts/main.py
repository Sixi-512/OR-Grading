import os
import sys
import argparse
import logging
from dotenv import load_dotenv
from openai import OpenAI

import workflow

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()


def create_client():
    """创建OpenAI客户端"""
    return OpenAI(
        base_url=os.getenv("API_BASE_URL"),
        api_key=os.getenv("API_KEY")
    )


def cmd_grade(args):
    """grade 子命令：对学生作业进行评分"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 获取环境变量（绝对路径）
    DATA_DIR = os.path.join(project_root, os.getenv("DATA_DIR", "data"))
    RESOURCES_DIR = os.path.join(project_root, os.getenv("RESOURCES_DIR", "resources"))
    OUTPUTS_DIR = os.path.join(project_root, os.getenv("OUTPUTS_DIR", "outputs"))
    RESPONSES_DIR = os.path.join(project_root, os.getenv("RESPONSES_DIR", "outputs\\responses"))
    CSV_PATH = os.path.join(OUTPUTS_DIR, "grading_results.csv")  # CSV与OUTPUTS_DIR一致
    MODEL = os.getenv("MODEL")
    
    if not all([DATA_DIR, RESOURCES_DIR, OUTPUTS_DIR, RESPONSES_DIR, CSV_PATH, MODEL]):
        logger.error("缺少必要的环境变量配置")
        return 1
    
    client = create_client()
    logger.info(f"开始第{args.attempt}次评分流程")
    logger.info(f"数据目录: {DATA_DIR}\n资源目录: {RESOURCES_DIR}\n输出目录: {OUTPUTS_DIR}")
    
    processed_count = workflow.grade_students(
        client=client, model=MODEL, data_dir=DATA_DIR, resources_dir=RESOURCES_DIR,
        outputs_dir=OUTPUTS_DIR, responses_dir=RESPONSES_DIR, csv_path=CSV_PATH, attempt_n=args.attempt
    )
    
    if processed_count > 0:
        logger.info(f"成功完成 {processed_count} 名学生的评分")
        return 0
    else:
        logger.warning("未处理任何学生")
        return 1


def cmd_regenerate_comments(args):
    """regenerate-comments 子命令：批量重新生成评语"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUTS_DIR = os.path.join(project_root, os.getenv("OUTPUTS_DIR", "outputs"))
    CSV_PATH = os.path.join(OUTPUTS_DIR, "grading_results.csv")  # CSV与OUTPUTS_DIR一致
    MODEL = os.getenv("MODEL")
    
    if not all([CSV_PATH, MODEL]):
        logger.error("缺少必要的环境变量配置")
        return 1
    if not os.path.exists(CSV_PATH):
        logger.error(f"CSV文件不存在: {CSV_PATH}")
        return 1
    
    client = create_client()
    student_ids = None
    if args.students:
        student_ids = [s.strip() for s in args.students.split(',')]
        logger.info(f"将处理指定的学生: {', '.join(student_ids)}")
    
    logger.info(f"开始重新生成第{args.attempt}次评分的评语")
    updated_count = workflow.regenerate_comments_batch(
        client=client, model=MODEL, csv_path=CSV_PATH, attempt_n=args.attempt, student_ids=student_ids
    )
    
    if updated_count > 0:
        logger.info(f"成功更新 {updated_count} 名学生的评语")
        return 0
    else:
        logger.warning("未更新任何学生的评语")
        return 1


def parse_opt():
    """解析命令行参数并返回opt对象"""
    parser = argparse.ArgumentParser(
        description='运筹学作业批改系统',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用的子命令')
    
    # grade 子命令
    grade_parser = subparsers.add_parser('grade', help='对学生作业进行评分')
    grade_parser.add_argument('--attempt', type=int, default=1, help='评分次数（默认为1）')
    grade_parser.set_defaults(func=cmd_grade)
    
    # regenerate-comments 子命令
    regen_parser = subparsers.add_parser('regenerate-comments', help='批量重新生成评语')
    regen_parser.add_argument('--attempt', type=int, required=True, help='指定评分次数')
    regen_parser.add_argument('--students', type=str, help='学号列表（逗号分隔，如"2451760,2452701"），不指定则处理所有学生')
    regen_parser.set_defaults(func=cmd_regenerate_comments)
    
    return parser.parse_args()


def main():
    """主函数：执行命令行操作"""
    opt = parse_opt()
    if not hasattr(opt, 'func'):
        return 1
    return opt.func(opt)


if __name__ == "__main__":
    sys.exit(main())