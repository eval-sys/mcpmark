#!/usr/bin/env python3
"""
验证脚本用于检查 Playwright 网页数据提取任务。

该脚本验证模型是否成功从网页提取了CSV格式的数据，
通过检查 messages.json 中最后一条助手消息来验证。
"""

import sys
import json
import os
import re
import csv
from io import StringIO

# 预期的CSV表头（必须完全匹配，包括空格）
EXPECTED_HEADER_LINE = "Title, Rating, Likes, Views, Replies"
EXPECTED_HEADERS = ["Title", "Rating", "Likes", "Views", "Replies"]
# 确切的数据行数（与data.csv完全一致）
EXPECTED_DATA_ROWS = 97


def get_model_response():
    """
    Get the model's response from the MCP_MESSAGES environment variable.
    Returns the last assistant message text.
    """
    messages_path = os.getenv("MCP_MESSAGES")
    print(f"| MCP_MESSAGES: {messages_path}")
    if not messages_path:
        print("| Warning: MCP_MESSAGES environment variable not set", file=sys.stderr)
        return None

    try:
        with open(messages_path, 'r') as f:
            messages = json.load(f)

        # Find the last assistant message with status completed
        for message in reversed(messages):
            if (message.get('role') == 'assistant' and
                message.get('status') == 'completed' and
                message.get('type') == 'message'):
                content = message.get('content', [])
                # Extract text from content
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') in ['text', 'output_text']:
                            return item.get('text', '')
                elif isinstance(content, str):
                    return content

        print("| Warning: No completed assistant message found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"| Error reading messages file: {str(e)}", file=sys.stderr)
        return None


def extract_csv_from_response(response):
    """
    从模型响应中提取CSV数据。
    """
    # 查找CSV代码块
    csv_pattern = r'```(?:csv)?\s*\n(.*?)\n```'
    matches = re.findall(csv_pattern, response, re.DOTALL | re.IGNORECASE)

    if matches:
        return matches[-1].strip()  # 返回最后一个CSV块

    # 如果没有找到代码块，尝试查找表头开始的CSV数据
    lines = response.split('\n')
    csv_start = -1

    # 更严格的表头匹配：寻找包含 "Title" 和 "Rating" 的行
    for i, line in enumerate(lines):
        if "Title" in line and "Rating" in line and "Likes" in line:
            csv_start = i
            break

    if csv_start >= 0:
        # 从表头开始提取，直到遇到空行或非CSV格式行
        csv_lines = []
        for line in lines[csv_start:]:
            line = line.strip()
            if not line or not (',' in line):
                if csv_lines:  # 如果已经有数据了，遇到空行就停止
                    break
                continue
            csv_lines.append(line)
            if len(csv_lines) > 100:  # 防止提取过多行
                break

        return '\n'.join(csv_lines)

    return None


def validate_csv_data(csv_text):
    """
    验证CSV数据的格式和内容，必须与data.csv完全一致。
    """
    if not csv_text:
        return False, "未找到CSV数据"

    try:
        lines = csv_text.strip().split('\n')

        # 检查总行数（1行表头 + 50行数据 = 51行）
        expected_total_rows = EXPECTED_DATA_ROWS + 1
        if len(lines) != expected_total_rows:
            return False, f"| CSV总行数不匹配，期望：{expected_total_rows}行，实际：{len(lines)}行"

        # 检查表头行格式（必须完全匹配）
        header_line = lines[0].strip()
        if header_line != EXPECTED_HEADER_LINE:
            return False, f"| 表头格式不匹配，期望：'{EXPECTED_HEADER_LINE}'，实际：'{header_line}'"

        # 解析CSV验证结构
        csv_reader = csv.reader(StringIO(csv_text))
        rows = list(csv_reader)

        # 检查每行的列数
        expected_columns = len(EXPECTED_HEADERS)
        for i, row in enumerate(rows):
            if len(row) != expected_columns:
                return False, f"| 第{i+1}行列数不正确，期望：{expected_columns}列，实际：{len(row)}列"

        # 验证数据行格式
        valid_rows = 0
        for i, row in enumerate(rows[1:], 2):  # 跳过表头，从第2行开始
            # 检查每列是否有数据
            if not all(cell.strip() for cell in row):
                return False, f"| 第{i}行存在空数据"

            # 检查数字列格式（Rating, Likes, Views, Replies都不应该带引号）
            for col_idx, col_name in [(1, "Rating"), (2, "Likes"), (3, "Views"), (4, "Replies")]:
                value = row[col_idx].strip()

                # 检查是否有引号（不应该有）
                if value.startswith('"') and value.endswith('"'):
                    return False, f"| 第{i}行{col_name}不应该有引号，实际：{value}"

                # 检查数字格式
                if col_name == "Rating":
                    try:
                        float(value)
                    except ValueError:
                        return False, f"| 第{i}行{col_name}应该是数字，实际：{value}"
                else:
                    if not value.isdigit():
                        return False, f"| 第{i}行{col_name}应该是纯数字，实际：{value}"

            valid_rows += 1

        # 验证数据行数
        if valid_rows != EXPECTED_DATA_ROWS:
            return False, f"| 有效数据行数不匹配，期望：{EXPECTED_DATA_ROWS}行，实际：{valid_rows}行"

        return True, f"| CSV验证成功：格式完全匹配data.csv，{valid_rows}行有效数据"

    except Exception as e:
        return False, f"| CSV格式解析错误：{str(e)}"


def verify():
    """
    验证模型的响应是否包含正确的CSV数据提取结果。
    """
    # 获取模型响应
    model_response = get_model_response()

    if not model_response:
        print("| 未找到模型响应", file=sys.stderr)
        return False

    print(f"|\n| 模型响应（前500字符）: {model_response[:500]}...", file=sys.stderr)

    # 从响应中提取CSV数据
    csv_data = extract_csv_from_response(model_response)

    if not csv_data:
        print("|\n| ✗ 未在响应中找到CSV数据", file=sys.stderr)
        return False

    print(f"|\n| 找到CSV数据（前300字符）:\n| {csv_data[:300]}...", file=sys.stderr)

    # 验证CSV数据
    is_valid, message = validate_csv_data(csv_data)

    if is_valid:
        print(f"|\n| ✓ {message}", file=sys.stderr)
        return True
    else:
        print(f"|\n| ✗ CSV验证失败: {message}", file=sys.stderr)
        return False


def main():
    """
    Executes the verification process and exits with a status code.
    """
    result = verify()
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
