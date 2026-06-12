#!/usr/bin/env python3
"""
Verification script for checking Playwright web data extraction tasks.

This script verifies whether the model successfully extracted CSV format data from web pages
by checking the last assistant message in messages.json.
"""

import sys
import json
import os
import re
import csv
from io import StringIO

# Expected CSV columns (order in output is flexible, but the set must match)
EXPECTED_HEADERS = ["Title", "Rating", "Likes", "Views", "Replies"]


def _load_expected_rows():
    """Load ground-truth rows from data.csv as a set of normalized tuples."""
    path = os.path.join(os.path.dirname(__file__), "data.csv")
    expected = set()
    with open(path, newline='') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            cells = [c.strip() for c in row]
            expected.add((cells[0], float(cells[1]), int(cells[2]), int(cells[3]), int(cells[4])))
    return expected


EXPECTED_ROWS = _load_expected_rows()
# Exact number of data rows (must match data.csv exactly)
EXPECTED_DATA_ROWS = len(EXPECTED_ROWS)


def get_model_response():
    """
    Get the model's response from the MCP_MESSAGES environment variable.
    Returns the last assistant message text.
    """
    messages_path = os.getenv("MCP_MESSAGES")
    print(f"| MCP_MESSAGES: {messages_path}", file=sys.stderr)
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
    Extract CSV data from model response.
    """
    # Look for CSV code blocks
    csv_pattern = r'```(?:csv)?\s*\n(.*?)\n```'
    matches = re.findall(csv_pattern, response, re.DOTALL | re.IGNORECASE)

    if matches:
        return matches[-1].strip()  # Return the last CSV block

    # If no code block found, try to find CSV data starting with header
    lines = response.split('\n')
    csv_start = -1

    # Stricter header matching: look for lines containing all expected column names
    for i, line in enumerate(lines):
        if all(h in line for h in EXPECTED_HEADERS):
            csv_start = i
            break

    if csv_start >= 0:
        # Extract from header until empty line or non-CSV format line
        csv_lines = []
        for line in lines[csv_start:]:
            line = line.strip()
            if not line or not (',' in line):
                if csv_lines:  # If we already have data, stop at empty line
                    break
                continue
            csv_lines.append(line)
            if len(csv_lines) > 100:  # Prevent extracting too many rows
                break

        return '\n'.join(csv_lines)

    return None


def validate_csv_data(csv_text):
    """
    Validate CSV data format and content, must match data.csv exactly.
    """
    if not csv_text:
        return False, "CSV data not found"

    try:
        lines = csv_text.strip().split('\n')

        # Check total number of rows (1 header row + data rows)
        expected_total_rows = EXPECTED_DATA_ROWS + 1
        if len(lines) != expected_total_rows:
            return False, f"| CSV total row count mismatch, expected: {expected_total_rows} rows, actual: {len(lines)} rows"

        # Parse CSV to validate structure
        csv_reader = csv.reader(StringIO(csv_text))
        rows = list(csv_reader)

        # Check column count for each row
        expected_columns = len(EXPECTED_HEADERS)
        for i, row in enumerate(rows):
            if len(row) != expected_columns:
                return False, f"| Row {i+1} column count incorrect, expected: {expected_columns} columns, actual: {len(row)} columns"

        # Check header columns — order can vary, but the set must match exactly
        header_cells = [c.strip() for c in rows[0]]
        if set(header_cells) != set(EXPECTED_HEADERS):
            missing_h = set(EXPECTED_HEADERS) - set(header_cells)
            extra_h = set(header_cells) - set(EXPECTED_HEADERS)
            return False, f"| Header columns mismatch, missing: {sorted(missing_h)}, extra: {sorted(extra_h)}"
        col_idx = {name: i for i, name in enumerate(header_cells)}

        # Validate data row format
        valid_rows = 0
        seen = set()
        for i, row in enumerate(rows[1:], 2):  # Skip header, start from row 2
            # Check if each column has data
            if not all(cell.strip() for cell in row):
                return False, f"| Row {i} contains empty data"

            # Check numeric column format (Rating, Likes, Views, Replies should not have quotes)
            for col_name in ("Rating", "Likes", "Views", "Replies"):
                value = row[col_idx[col_name]].strip()

                # Check for quotes (should not have any)
                if value.startswith('"') and value.endswith('"'):
                    return False, f"| Row {i} {col_name} should not have quotes, actual: {value}"

                # Check numeric format
                if col_name == "Rating":
                    try:
                        float(value)
                    except ValueError:
                        return False, f"| Row {i} {col_name} should be a number, actual: {value}"
                else:
                    if not value.isdigit():
                        return False, f"| Row {i} {col_name} should be pure digits, actual: {value}"

            seen.add((
                row[col_idx["Title"]].strip(),
                float(row[col_idx["Rating"]].strip()),
                int(row[col_idx["Likes"]].strip()),
                int(row[col_idx["Views"]].strip()),
                int(row[col_idx["Replies"]].strip()),
            ))
            valid_rows += 1

        # Validate number of data rows
        if valid_rows != EXPECTED_DATA_ROWS:
            return False, f"| Valid data row count mismatch, expected: {EXPECTED_DATA_ROWS} rows, actual: {valid_rows} rows"

        # Validate row contents match data.csv exactly (order independent)
        missing = EXPECTED_ROWS - seen
        extra = seen - EXPECTED_ROWS
        if missing or extra:
            return False, f"| Row content mismatch, missing: {len(missing)} row(s), extra: {len(extra)} row(s); sample missing: {sorted(missing)[:2]}"

        return True, f"| CSV validation successful: format matches data.csv exactly, {valid_rows} valid data rows"

    except Exception as e:
        return False, f"| CSV format parsing error: {str(e)}"


def verify():
    """
    Verify if the model's response contains correct CSV data extraction results.
    """
    # Get model response
    model_response = get_model_response()

    if not model_response:
        print("| Model response not found", file=sys.stderr)
        return False

    print(f"|\n| Model response (first 500 characters): {model_response[:500]}...", file=sys.stderr)

    # Extract CSV data from response
    csv_data = extract_csv_from_response(model_response)

    if not csv_data:
        print("|\n| ✗ CSV data not found in response", file=sys.stderr)
        return False

    print(f"|\n| Found CSV data (first 300 characters):\n| {csv_data[:300]}...", file=sys.stderr)

    # Validate CSV data
    is_valid, message = validate_csv_data(csv_data)

    if is_valid:
        print(f"|\n| ✓ {message}", file=sys.stderr)
        return True
    else:
        print(f"|\n| ✗ CSV validation failed: {message}", file=sys.stderr)
        return False


def main():
    """
    Executes the verification process and exits with a status code.
    """
    result = verify()
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
