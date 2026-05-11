import asyncio
import sys
import re
import os
import json
from pathlib import Path


def get_model_response():
    """
    Get the model's response from the MCP_MESSAGES environment variable.
    Returns the last assistant message text.
    """
    messages_path = os.getenv("MCP_MESSAGES")
    print(f"MCP_MESSAGES: {messages_path}", file=sys.stderr)
    if not messages_path:
        print("Warning: MCP_MESSAGES environment variable not set", file=sys.stderr)
        return None

    try:
        with open(messages_path, "r") as f:
            messages = json.load(f)

        # Find the last assistant message with status='completed', type='message'
        for message in reversed(messages):
            if (
                message.get("role") == "assistant"
                and message.get("status") == "completed"
                and message.get("type") == "message"
            ):
                content = message.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") in ["text", "output_text"]:
                            return item.get("text", "")
                elif isinstance(content, str):
                    return content

        print("Warning: No assistant response found in messages", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading messages file: {str(e)}", file=sys.stderr)
        return None


def normalize_text(text):
    """
    Normalize text for comparison by collapsing whitespace.
    """
    if not isinstance(text, str):
        return str(text)

    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')

    # Normalize whitespace
    text = " ".join(text.split())

    return text.strip()


def parse_answer_format(text):
    """
    Parse the <answer>...</answer> format from the agent's output.
    Returns a dictionary with the parsed values.
    """
    if not text:
        print("Error: No text provided to parse", file=sys.stderr)
        return None

    match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        print("Error: No <answer>...</answer> tags found in response", file=sys.stderr)
        return None

    answer_content = match.group(1).strip()
    if not answer_content:
        print("Error: Empty answer content", file=sys.stderr)
        return None

    lines = [line.strip() for line in answer_content.split("\n") if line.strip()]

    if len(lines) != 12:
        print(f"Error: Expected 12 lines in answer, got {len(lines)}", file=sys.stderr)
        print(f"Lines found: {lines}", file=sys.stderr)
        return None

    expected_keys = [
        "TankSearchCount", "ZeroResultsCount", "HighestUseTerm",
        "Results20to30Term", "Hits15PlusCount", "ID10to15MaxResults",
        "DefaultStoreViewCount", "OneResultTerm", "HighestResultLastSearch",
        "TopUseTerm", "FirstNonZeroResult", "TotalUniqueTerms",
    ]

    result = {}
    for line in lines:
        if "|" not in line:
            print(f"Error: Line missing '|' separator: {line}", file=sys.stderr)
            return None
        parts = line.split("|", 1)
        if len(parts) != 2:
            print(f"Error: Invalid line format: {line}", file=sys.stderr)
            return None
        key, value = parts[0].strip(), normalize_text(parts[1].strip())
        if not key or not value:
            print(f"Error: Empty key or value in line: {line}", file=sys.stderr)
            return None
        result[key] = value

    missing_keys = set(expected_keys) - set(result.keys())
    if missing_keys:
        print(f"Error: Missing required keys: {missing_keys}", file=sys.stderr)
        return None

    return result


def load_expected_answer(label_path):
    """
    Load the expected answer from label.txt file.
    Returns a dictionary with the expected values.

    Each line is "Key|value..."; split only on the first '|' so values that
    themselves contain '|' (e.g. "term1:c1|term2:c2") are preserved.
    """
    try:
        with open(label_path, "r") as f:
            lines = f.read().strip().split("\n")

        expected = {}
        for line in lines:
            if "|" in line:
                key, value = line.split("|", 1)
                expected[key.strip()] = normalize_text(value.strip())

        return expected
    except Exception as e:
        print(f"Error reading label file: {str(e)}", file=sys.stderr)
        return None


def compare_answers(model_answer, expected_answer):
    """
    Compare the model's answer with the expected answer.
    Returns True if all key information matches, False otherwise.
    """
    if not model_answer or not expected_answer:
        return False

    mismatches = []
    for key, expected_value in expected_answer.items():
        model_value = model_answer.get(key, "")

        if key in [
            "TankSearchCount",
            "ZeroResultsCount",
            "Hits15PlusCount",
            "DefaultStoreViewCount",
            "TotalUniqueTerms",
        ]:
            # Numeric counts: compare as int so "04" / "4" / "4.0" don't fail
            try:
                if int(float(model_value)) != int(float(expected_value)):
                    mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
            except ValueError:
                mismatches.append(f"{key} should be numeric: got '{model_value}'")

        elif key in [
            "HighestUseTerm",
            "ID10to15MaxResults",
            "HighestResultLastSearch",
            "TopUseTerm",
            "FirstNonZeroResult",
        ]:
            # Single "term:count" — term case-insensitive, count as int
            if ":" not in expected_value or ":" not in model_value:
                mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
                continue
            exp_term, exp_count = expected_value.rsplit(":", 1)
            mod_term, mod_count = model_value.rsplit(":", 1)
            if exp_term.strip().lower() != mod_term.strip().lower():
                mismatches.append(f"{key} term: expected '{exp_term}', got '{mod_term}'")
            try:
                if int(exp_count.strip()) != int(mod_count.strip()):
                    mismatches.append(f"{key} count: expected '{exp_count}', got '{mod_count}'")
            except ValueError:
                mismatches.append(f"{key} count should be numeric: got '{mod_count}'")

        elif key in ["Results20to30Term", "OneResultTerm"]:
            # Multi-entry "term1:count1;term2:count2;..." — order-independent;
            # term case-insensitive, count as int
            expected_entries = set()
            for item in expected_value.split(";"):
                item = item.strip()
                if ":" not in item:
                    continue
                term, count = item.rsplit(":", 1)
                expected_entries.add((term.strip().lower(), int(count.strip())))
            model_entries = set()
            for item in model_value.split(";"):
                item = item.strip()
                if ":" not in item:
                    mismatches.append(f"{key}: malformed entry '{item}'")
                    continue
                term, count = item.rsplit(":", 1)
                try:
                    model_entries.add((term.strip().lower(), int(count.strip())))
                except ValueError:
                    mismatches.append(f"{key}: non-numeric count in '{item}'")
            if expected_entries != model_entries:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        else:
            # Fallback exact match for any unrecognized key
            if model_value != expected_value:
                mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")

    if mismatches:
        print("\n=== Answer Comparison Mismatches ===", file=sys.stderr)
        for mismatch in mismatches:
            print(f"✗ {mismatch}", file=sys.stderr)
        return False

    print("\n=== Answer Comparison ===", file=sys.stderr)
    print("✓ All key information matches the expected answer", file=sys.stderr)
    return True


async def verify() -> bool:
    """
    Verify the search and filtering operations task by comparing the model's
    answer against the expected label.
    """
    label_path = Path(__file__).parent / "label.txt"

    expected_answer = load_expected_answer(label_path)
    if not expected_answer:
        print("Error: Could not load expected answer from label.txt", file=sys.stderr)
        return False

    model_response = get_model_response()
    if not model_response:
        print("No model response found", file=sys.stderr)
        return False

    print("Found model response, parsing answer format...", file=sys.stderr)
    model_answer = parse_answer_format(model_response)
    if not model_answer:
        print("Could not parse answer format from model response", file=sys.stderr)
        return False

    print("\n=== Model Answer Parsed ===", file=sys.stderr)
    for key, value in model_answer.items():
        print(f"{key}: {value}", file=sys.stderr)

    answer_match = compare_answers(model_answer, expected_answer)
    if not answer_match:
        print("\nModel answer does not match expected answer", file=sys.stderr)
        return False
    print("\n✓ Model answer matches expected answer", file=sys.stderr)
    return True


def main():
    """
    Executes the verification process and exits with a status code.
    """
    result = asyncio.run(verify())
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
