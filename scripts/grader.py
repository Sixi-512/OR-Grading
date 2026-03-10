import os
import base64
import mimetypes
import logging
import utils

logger = logging.getLogger(__name__)

def encode_image_to_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_mime_type(file_path):
    return mimetypes.guess_type(file_path)[0]

def build_grading_prompt(questions_files, answers_files):
    prompt_parts = [
        "你是一位运筹学作业批改专家。请根据以下题目和答案，批改学生的作业。",
        "\n【作业题目】"
    ]
    for i in range(len(questions_files)):
        prompt_parts.append(f"\n题目 {i+1}:")
    
    prompt_parts.append("\n【参考答案】")
    for i in range(len(answers_files)):
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

def grade_assignment(client, model, questions, answers, student_files):
    """调用LLM获取评分"""
    all_files = questions + answers + student_files
    content = [{"type": "text", "text": build_grading_prompt(questions, answers)}]

    for file_path in all_files:
        base64_data = encode_image_to_base64(file_path)
        mime_type = get_mime_type(file_path) or "image/jpeg"
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}
        })

    try:
        return '{"score": 85, "comment": "计算正确，步骤清晰"}'
        # response = client.chat.completions.create(
        #     model=model,
        #     messages=[{"role": "user", "content": content}],
        #     response_format={"type": "json_object"}
        # )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"调用LLM失败: {e}")
        return None

def save_raw_response(content, student_id, responses_dir):
    """保存LLM的原始响应（覆盖方式，只保留最新回复）
    
    Args:
        content: LLM返回的原始内容
        student_id: 学号
        responses_dir: 响应保存目录
    """
    os.makedirs(responses_dir, exist_ok=True)
    path = os.path.join(responses_dir, f"{student_id}.txt")
    if not utils.write_file_content(path, content):
        logger.info(f"学号 {student_id} 的LLM响应信息保存出错")


def generate_comment_from_score(client, model, score):
    """根据成绩调用LLM生成评语
    
    Args:
        client: OpenAI客户端
        model: 使用的模型名称
        score: 分数
        
    Returns:
        生成的评语字符串，失败返回None
    """
    prompt = f"""你是一位运筹学作业批改专家。根据以下分数，生成简洁的评语（30字以内）：
    分数: {score}/100
    请只输出评语，不要包含其他内容。"""
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        comment = response.choices[0].message.content.strip()
        return comment
    except Exception as e:
        logger.error(f"生成评语失败: {e}")
        return None