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
        print("ERROR: No text provided to parse", file=sys.stderr)
        return None

    # Look for <answer>...</answer> pattern
    match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        print("ERROR: No <answer>...</answer> tags found in the response", file=sys.stderr)
        print("Response text preview (first 200 chars):", text[:200], file=sys.stderr)
        return None

    answer_content = match.group(1).strip()
    print(f"Found answer content with {len(answer_content)} characters", file=sys.stderr)

    # Parse each line
    result = {}
    lines = answer_content.split("\n")
    
    # Expected keys for this task
    expected_keys = [
        "SpriteProducts", "Quantity100Products", "WS12Info", "PendingOrders",
        "GraceOrderID", "HighestOrderInfo", "CheapProduct", "OvernightDufflePrice",
        "HollisterPosition", "CostelloCustomers", "SarahMillerInfo", 
        "PaidInvoices", "Invoice002BillTo"
    ]

    if len(lines) != 13:
        print(f"ERROR: Expected 13 lines in answer, got {len(lines)}", file=sys.stderr)
        print(f"Lines found: {lines}", file=sys.stderr)
        return None

    for i, line in enumerate(lines, 1):
        if "|" not in line:
            print(f"ERROR: Line {i} does not contain pipe separator '|': '{line}'", file=sys.stderr)
            return None
        
        parts = line.split("|", 1)
        if len(parts) != 2:
            print(f"ERROR: Line {i} could not be split into key|value: '{line}'", file=sys.stderr)
            return None
            
        key, value = parts
        result[key.strip()] = normalize_text(value.strip())
    
    # Check if all expected keys are present
    missing_keys = set(expected_keys) - set(result.keys())
    if missing_keys:
        print(f"ERROR: Missing expected keys: {missing_keys}", file=sys.stderr)
        print(f"Keys found: {list(result.keys())}", file=sys.stderr)
        return None
    
    # Check for unexpected keys
    extra_keys = set(result.keys()) - set(expected_keys)
    if extra_keys:
        print(f"WARNING: Unexpected keys found: {extra_keys}", file=sys.stderr)

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

    # Check each expected key
    mismatches = []
    for key, expected_value in expected_answer.items():
        model_value = model_answer.get(key, "")

        if key == "WS12Info":
            # "name:price" — name case-insensitive, price as float
            if ":" in expected_value and ":" in model_value:
                exp_name, exp_price = expected_value.rsplit(":", 1)
                mod_name, mod_price = model_value.rsplit(":", 1)
                if exp_name.strip().lower() != mod_name.strip().lower():
                    mismatches.append(f"{key} name: expected '{exp_name}', got '{mod_name}'")
                exp_price_clean = exp_price.replace("$", "").replace(",", "").strip()
                mod_price_clean = mod_price.replace("$", "").replace(",", "").strip()
                try:
                    if float(exp_price_clean) != float(mod_price_clean):
                        mismatches.append(f"{key} price: expected '{exp_price}', got '{mod_price}'")
                except ValueError:
                    mismatches.append(f"{key} price should be numeric: got '{mod_price}'")
            else:
                if expected_value != model_value:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )

        elif key == "HighestOrderInfo":
            # "customer:amount" — customer case-insensitive, amount as float
            if ":" in expected_value and ":" in model_value:
                exp_customer, exp_amount = expected_value.rsplit(":", 1)
                mod_customer, mod_amount = model_value.rsplit(":", 1)
                if exp_customer.strip().lower() != mod_customer.strip().lower():
                    mismatches.append(f"{key} customer: expected '{exp_customer}', got '{mod_customer}'")
                exp_amount_clean = exp_amount.replace("$", "").replace(",", "").strip()
                mod_amount_clean = mod_amount.replace("$", "").replace(",", "").strip()
                try:
                    if float(exp_amount_clean) != float(mod_amount_clean):
                        mismatches.append(f"{key} amount: expected '{exp_amount}', got '{mod_amount}'")
                except ValueError:
                    mismatches.append(f"{key} amount should be numeric: got '{mod_amount}'")
            else:
                if expected_value != model_value:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )

        elif key == "CheapProduct":
            # "name:quantity" — name case-insensitive, qty as int
            if ":" in expected_value and ":" in model_value:
                exp_name, exp_qty = expected_value.rsplit(":", 1)
                mod_name, mod_qty = model_value.rsplit(":", 1)
                if exp_name.strip().lower() != mod_name.strip().lower():
                    mismatches.append(f"{key} name: expected '{exp_name}', got '{mod_name}'")
                try:
                    if int(exp_qty.strip()) != int(mod_qty.strip()):
                        mismatches.append(f"{key} quantity: expected '{exp_qty}', got '{mod_qty}'")
                except ValueError:
                    mismatches.append(f"{key} quantity should be numeric: got '{mod_qty}'")
            else:
                if expected_value != model_value:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )

        elif key == "OvernightDufflePrice":
            # Strip $ and , then compare as float
            expected_clean = expected_value.replace("$", "").replace(",", "").strip()
            model_clean = model_value.replace("$", "").replace(",", "").strip()
            try:
                if float(expected_clean) != float(model_clean):
                    mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
            except ValueError:
                mismatches.append(f"{key} should be numeric: got '{model_value}'")

        elif key == "HollisterPosition":
            # Position format (1st, 2nd, 3rd, etc.) — case-insensitive
            if model_value.strip().lower() != expected_value.strip().lower():
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        elif key == "SarahMillerInfo":
            # "group:date" — both case-insensitive exact match
            # (split on first ':' only; the date itself contains ':' for the time)
            if ":" in expected_value and ":" in model_value:
                exp_group, exp_date = expected_value.split(":", 1)
                mod_group, mod_date = model_value.split(":", 1)
                if exp_group.strip().lower() != mod_group.strip().lower():
                    mismatches.append(f"{key} group: expected '{exp_group}', got '{mod_group}'")
                if exp_date.strip().lower() != mod_date.strip().lower():
                    mismatches.append(f"{key} date: expected '{exp_date}', got '{mod_date}'")
            else:
                if expected_value != model_value:
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )

        elif key == "Invoice002BillTo":
            # Customer name — case-insensitive
            if model_value.strip().lower() != expected_value.strip().lower():
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        elif key in [
            "SpriteProducts",
            "Quantity100Products",
            "PendingOrders",
            "CostelloCustomers",
            "PaidInvoices",
        ]:
            # Numeric counts: compare as int so "04" / "4" / "4.0" don't fail
            try:
                if int(float(model_value)) != int(float(expected_value)):
                    mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
            except ValueError:
                mismatches.append(f"{key} should be numeric: got '{model_value}'")

        else:
            # Exact string match for IDs and other text fields (e.g.
            # GraceOrderID has leading zeros like "000000114" that must be
            # preserved)
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
    print("\n" + "="*60, file=sys.stderr)
    print("Starting verification of Task 5", file=sys.stderr)
    print("="*60, file=sys.stderr)
    
    # Get the label file path
    label_path = Path(__file__).parent / "label.txt"

    # Load expected answer
    print("\n--- Loading Expected Answer ---", file=sys.stderr)
    expected_answer = load_expected_answer(label_path)
    if not expected_answer:
        print("FATAL ERROR: Could not load expected answer from label.txt", file=sys.stderr)
        return False
    print(f"Successfully loaded {len(expected_answer)} expected values", file=sys.stderr)

    # Get model's response from MCP_MESSAGES
    print("\n--- Loading Model Response ---", file=sys.stderr)
    model_response = get_model_response()
    if not model_response:
        print("FATAL ERROR: No model response found in MCP_MESSAGES", file=sys.stderr)
        return False
    
    print(f"Found model response ({len(model_response)} characters)", file=sys.stderr)
    
    print("\n--- Parsing Answer Format ---", file=sys.stderr)
    model_answer = parse_answer_format(model_response)
    
    if not model_answer:
        print("\nFATAL ERROR: Could not parse answer format from model response", file=sys.stderr)
        print("Verification FAILED", file=sys.stderr)
        return False
    
    print("\n=== Model Answer Successfully Parsed ===", file=sys.stderr)
    for key, value in model_answer.items():
        print(f"  {key}: {value}", file=sys.stderr)

    # Compare answers
    print("\n--- Comparing Answers ---", file=sys.stderr)
    answer_match = compare_answers(model_answer, expected_answer)
    
    if not answer_match:
        print("\n" + "="*60, file=sys.stderr)
        print("VERIFICATION FAILED: Model answer does not match expected answer", file=sys.stderr)
        print("="*60, file=sys.stderr)
        return False
    
    print("\n" + "="*60, file=sys.stderr)
    print("✓ VERIFICATION PASSED: Model answer matches expected answer", file=sys.stderr)
    print("="*60, file=sys.stderr)
    return True


def main():
    """
    Executes the verification process and exits with a status code.
    """
    result = asyncio.run(verify())
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
