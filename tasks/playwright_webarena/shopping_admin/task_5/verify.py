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
    print(f"MCP_MESSAGES: {messages_path}")
    if not messages_path:
        print("Warning: MCP_MESSAGES environment variable not set", file=sys.stderr)
        return None

    try:
        with open(messages_path, "r") as f:
            messages = json.load(f)

        # Find the last assistant message with type='message', status='completed'
        for message in reversed(messages):
            if (
                message.get("role") == "assistant"
                and message.get("status") == "completed"
                and message.get("type") == "message"
            ):
                content = message.get("content", [])
                for item in content:
                    # Check for both 'text' and 'output_text' types
                    if item.get("type") in ["text", "output_text"]:
                        return item.get("text", "")

        print("Warning: No assistant response found in messages", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading messages file: {str(e)}", file=sys.stderr)
        return None


def parse_answer_format(text):
    """
    Parse the <answer>...</answer> format from the agent's output.
    Returns a dictionary with the parsed values.
    """
    if not text:
        return None

    # Look for <answer>...</answer> pattern
    match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    answer_content = match.group(1).strip()

    # Parse each line
    result = {}
    lines = answer_content.split("\n")

    if len(lines) != 13:
        print(f"Error: Expected 13 lines in answer, got {len(lines)}", file=sys.stderr)
        return None

    for line in lines:
        if "|" in line:
            key, value = line.split("|", 1)
            result[key.strip()] = value.strip()

    return result


def load_expected_answer(label_path):
    """
    Load the expected answer from label.txt file.
    Returns a dictionary with the expected values.
    """
    try:
        with open(label_path, "r") as f:
            lines = f.read().strip().split("\n")

        expected = {}
        for line in lines:
            if "|" in line:
                key, value = line.split("|", 1)
                expected[key.strip()] = value.strip()

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

    # Check each expected key
    mismatches = []
    for key, expected_value in expected_answer.items():
        model_value = model_answer.get(key, "")

        # Special handling for different types of values
        if key == "WS12Info":
            # Check if product name and price match (format: name:price)
            if ":" in expected_value and ":" in model_value:
                expected_name, expected_price = expected_value.rsplit(":", 1)
                model_name, model_price = model_value.rsplit(":", 1)
                # Normalize price format
                expected_price_clean = expected_price.replace("$", "").replace(",", "")
                model_price_clean = model_price.replace("$", "").replace(",", "")
                if (
                    expected_name != model_name
                    or expected_price_clean != model_price_clean
                ):
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )
            else:
                if expected_value != model_value:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )

        elif key == "GraceOrderID":
            # Order ID should start with "000" and match exactly
            if not model_value.startswith("000"):
                mismatches.append(
                    f"{key}: expected to start with '000', got '{model_value}'"
                )
            elif model_value != expected_value:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        elif key == "HighestOrderInfo":
            # Check format customer:amount
            if ":" in expected_value and ":" in model_value:
                expected_customer, expected_amount = expected_value.rsplit(":", 1)
                model_customer, model_amount = model_value.rsplit(":", 1)
                # Normalize amount format
                expected_amount_clean = expected_amount.replace("$", "").replace(
                    ",", ""
                )
                model_amount_clean = model_amount.replace("$", "").replace(",", "")
                if (
                    expected_customer != model_customer
                    or expected_amount_clean != model_amount_clean
                ):
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )
            else:
                if expected_value != model_value:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )

        elif key == "Position2Product":
            # Check if product name and quantity match
            if ":" in expected_value and ":" in model_value:
                expected_name, expected_qty = expected_value.rsplit(":", 1)
                model_name, model_qty = model_value.rsplit(":", 1)
                if expected_name != model_name or expected_qty != model_qty:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )
            else:
                if expected_value != model_value:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )

        elif key == "OvernightDufflePrice":
            # Normalize price format
            expected_clean = expected_value.replace("$", "").replace(",", "")
            model_clean = model_value.replace("$", "").replace(",", "")
            if expected_clean != model_clean:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        elif key == "HollisterPosition":
            # Position format (1st, 2nd, 3rd, etc.)
            if model_value.lower() != expected_value.lower():
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        elif key == "SarahMillerInfo":
            # Format: group:date
            if ":" in expected_value and ":" in model_value:
                expected_group, expected_date = expected_value.split(":", 1)
                model_group, model_date = model_value.split(":", 1)
                # Allow some flexibility in date format
                if expected_group != model_group:
                    mismatches.append(
                        f"{key}: expected group '{expected_group}', got '{model_group}'"
                    )
                # For date, check if key parts match
                if not (expected_date in model_date or model_date in expected_date):
                    mismatches.append(
                        f"{key}: expected date '{expected_date}', got '{model_date}'"
                    )
            else:
                if expected_value != model_value:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )

        elif key == "Invoice002BillTo":
            # Name should match exactly
            if model_value != expected_value:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        else:
            # Exact match for count fields and other numeric values
            if model_value != expected_value:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

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
    Verifies that the sales and inventory analysis task has been completed correctly.
    First checks the model's answer against the expected label,
    then optionally verifies the actual state in the Magento Admin.
    """
    # Get the label file path
    label_path = Path(__file__).parent / "label.txt"

    # Load expected answer
    expected_answer = load_expected_answer(label_path)
    if not expected_answer:
        print("Error: Could not load expected answer from label.txt", file=sys.stderr)
        return False

    # Get model's response from MCP_MESSAGES
    model_response = get_model_response()
    if model_response:
        print("Found model response, parsing answer format...", file=sys.stderr)
        model_answer = parse_answer_format(model_response)

        if model_answer:
            print("\n=== Model Answer Parsed ===", file=sys.stderr)
            for key, value in model_answer.items():
                print(f"{key}: {value}", file=sys.stderr)

            # Compare answers
            answer_match = compare_answers(model_answer, expected_answer)
            if not answer_match:
                print("\nModel answer does not match expected answer", file=sys.stderr)
                return False
            print("\n✓ Model answer matches expected answer", file=sys.stderr)
            return True
        else:
            print(
                "Warning: Could not parse answer format from model response",
                file=sys.stderr,
            )
            return False
    else:
        print("No model response found", file=sys.stderr)
        return False


def main():
    """
    Executes the verification process and exits with a status code.
    """
    result = asyncio.run(verify())
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
