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
        with open(messages_path, 'r') as f:
            messages = json.load(f)
        
        # Find the last assistant message
        for message in reversed(messages):
            if (
                message.get('role') == 'assistant'
                and message.get('status') == 'completed'
                and message.get('type') == 'message'
            ):
                content = message.get('content', [])
                for item in content:
                    if item.get('type') == 'output_text':
                        return item.get('text', '')
        
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
        return None

    # Look for <answer>...</answer> pattern
    match = re.search(r'<answer>(.*?)</answer>', text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    answer_content = match.group(1).strip()

    # Parse each line
    result = {}
    lines = answer_content.split('\n')

    # Skip the check for exact number of lines - just parse what we have
    # if len(lines) != 13:
    #     print(f"Error: Expected 13 lines in answer, got {len(lines)}", file=sys.stderr)
    #     return None

    for line in lines:
        if '|' in line:
            key, value = line.split('|', 1)
            result[key.strip()] = normalize_text(value.strip())

    return result

def load_expected_answer(label_path):
    """
    Load the expected answer from label.txt file.
    Returns a dictionary with the expected values.
    """
    try:
        with open(label_path, 'r') as f:
            lines = f.read().strip().split('\n')

        expected = {}
        for line in lines:
            if '|' in line:
                key, value = line.split('|', 1)
                expected[key.strip()] = normalize_text(value.strip())

        return expected
    except Exception as e:
        print(f"Error reading label file: {str(e)}", file=sys.stderr)
        return None

def _normalize_bestseller(value):
    """
    Parse a Bestseller line "name:price:quantity:sku:salable_quantity:status"
    into a normalized tuple so the three lines can be compared as a set
    (order-independent). Returns None if the value is malformed.
    """
    if ':' not in value:
        return None
    parts = value.split(':')
    if len(parts) != 6:
        return None
    name, price, qty, sku, salable, status = parts
    try:
        return (
            name.replace('&trade;', '™').strip().lower(),
            float(price.replace('$', '').replace(',', '').strip()),
            int(qty.strip()),
            sku.strip().lower(),
            float(salable.replace(',', '').strip()),
            status.strip().lower(),
        )
    except ValueError:
        return None


def compare_answers(model_answer, expected_answer):
    """
    Compare the model's answer with the expected answer.
    Returns True if all key information matches, False otherwise.
    """
    if not model_answer or not expected_answer:
        return False

    bestseller_keys = ['Bestseller1', 'Bestseller2', 'Bestseller3']
    mismatches = []

    # Bestseller1/2/3 are compared as a set — model may list the three lines
    # in any order
    expected_bs_raw = [expected_answer.get(k, '') for k in bestseller_keys if k in expected_answer]
    if expected_bs_raw:
        model_bs_raw = [model_answer.get(k, '') for k in bestseller_keys if k in model_answer]
        expected_bs = [_normalize_bestseller(v) for v in expected_bs_raw]
        model_bs = [_normalize_bestseller(v) for v in model_bs_raw]
        if None in expected_bs:
            mismatches.append(f"Bestseller (label): malformed line in label.txt: {expected_bs_raw}")
        elif None in model_bs:
            bad = [r for r, n in zip(model_bs_raw, model_bs) if n is None]
            mismatches.append(f"Bestseller: malformed or non-numeric line(s): {bad}")
        else:
            expected_set = set(expected_bs)
            model_set = set(model_bs)
            missing = expected_set - model_set
            extra = model_set - expected_set
            if missing or extra:
                mismatches.append(
                    f"Bestseller set mismatch — missing: {sorted(missing)}; extra: {sorted(extra)}"
                )

    for key, expected_value in expected_answer.items():
        if key in bestseller_keys:
            continue  # already handled above
        model_value = model_answer.get(key, '')

        if key == 'BestsellerInSearch':
            # Check search term and count
            if expected_value.lower() != model_value.lower():
                mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
        
        elif key == 'PercentageDiscountRule':
            # Check rule name and percentage
            if ':' in expected_value and ':' in model_value:
                expected_name, expected_pct = expected_value.rsplit(':', 1)
                model_name, model_pct = model_value.rsplit(':', 1)
                if expected_name.lower() != model_name.lower():
                    mismatches.append(f"{key} name: expected '{expected_name}', got '{model_name}'")
                # Normalize percentage (20 vs 20% vs 20.0)
                exp_pct_clean = expected_pct.replace('%', '').strip()
                mod_pct_clean = model_pct.replace('%', '').strip()
                try:
                    if float(exp_pct_clean) != float(mod_pct_clean):
                        mismatches.append(f"{key} percentage: expected '{expected_pct}', got '{model_pct}'")
                except ValueError:
                    mismatches.append(f"{key} percentage should be numeric: got '{model_pct}'")
            else:
                if expected_value != model_value:
                    mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
        
        elif key == 'TopCustomer':
            # Check name:email:group
            if ':' in expected_value and ':' in model_value:
                expected_parts = expected_value.split(':')
                model_parts = model_value.split(':')
                if len(expected_parts) == 3 and len(model_parts) == 3:
                    exp_name, exp_email, exp_group = expected_parts
                    mod_name, mod_email, mod_group = model_parts
                    if exp_name.lower() != mod_name.lower():
                        mismatches.append(f"{key} name: expected '{exp_name}', got '{mod_name}'")
                    if exp_email.lower() != mod_email.lower():
                        mismatches.append(f"{key} email: expected '{exp_email}', got '{mod_email}'")
                    if exp_group.lower() != mod_group.lower():
                        mismatches.append(f"{key} group: expected '{exp_group}', got '{mod_group}'")
                else:
                    mismatches.append(f"{key}: format mismatch - expected '{expected_value}', got '{model_value}'")
            else:
                if expected_value != model_value:
                    mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
        
        elif key in ['ActiveRulesCount', 'TotalOrders', 'SameGroupCustomers']:
            # Numeric counts: compare as int so "04" vs "4" doesn't fail
            try:
                if int(model_value) != int(expected_value):
                    mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
            except ValueError:
                mismatches.append(f"{key} should be numeric: got '{model_value}'")

        else:
            # Exact string match for IDs and other text fields (e.g. MostRecentOrderID
            # has leading zeros like "000000299" that must be preserved)
            if str(model_value) != str(expected_value):
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
    Verifies that the bestseller analysis and promotion task has been completed correctly.
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
            print("Warning: Could not parse answer format from model response", file=sys.stderr)
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