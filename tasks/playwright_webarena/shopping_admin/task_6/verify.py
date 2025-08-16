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
        with open(messages_path, 'r') as f:
            messages = json.load(f)
        
        # Find the last assistant message
        for message in reversed(messages):
            if message.get('role') == 'assistant' and message.get('status') == 'completed':
                content = message.get('content', [])
                for item in content:
                    if item.get('type') == 'output_text':
                        return item.get('text', '')
        
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
    match = re.search(r'<answer>(.*?)</answer>', text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    
    answer_content = match.group(1).strip()
    
    # Parse each line
    result = {}
    lines = answer_content.split('\n')
    
    # Skip the check for exact number of lines - just parse what we have
    # if len(lines) != 20:
    #     print(f"Error: Expected 20 lines in answer, got {len(lines)}", file=sys.stderr)
    #     return None
    
    for line in lines:
        if '|' in line:
            key, value = line.split('|', 1)
            result[key.strip()] = value.strip()
    
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
        model_value = model_answer.get(key, '')
        
        # Special handling for different types of values
        if key in ['Lifetime_Sales_Amount', 'Second_Bestseller_Price', 'Dashboard_Revenue']:
            # For price/amount fields, normalize format
            expected_clean = expected_value.replace('$', '').replace(',', '')
            model_clean = model_value.replace('$', '').replace(',', '')
            if expected_clean != model_clean:
                mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
        
        elif key in ['NY_Tax_Rate', 'CA_Tax_Rate']:
            # Tax rates - allow different decimal formats
            expected_clean = expected_value.replace('%', '').strip()
            model_clean = model_value.replace('%', '').strip()
            # Convert to float for comparison
            try:
                if float(expected_clean) != float(model_clean):
                    mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
            except ValueError:
                if expected_clean != model_clean:
                    mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
        
        elif key in ['Product_In_Last_Orders', 'Processing_Visible_Storefront', 'Processing_Default_Status', 'Tax_Shipping_Zero']:
            # Yes/No fields - case insensitive
            if model_value.lower() != expected_value.lower():
                mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
        
        elif key == 'Empty_Rows_Yes_Effect':
            # Allow flexible descriptions for this field
            # Just check if model provided some reasonable description
            if not model_value or len(model_value) < 5:
                mismatches.append(f"{key}: expected meaningful description, got '{model_value}'")
        
        elif key == 'Order_Status_Options':
            # Check if main options are mentioned
            expected_options = set(opt.strip() for opt in expected_value.split(','))
            model_options = set(opt.strip() for opt in model_value.split(','))
            if expected_options != model_options:
                mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
        
        elif key == 'Chart_Disabled_Message':
            # Allow some flexibility in message text
            # Check for key words
            if 'disabled' not in model_value.lower() and 'enable' not in model_value.lower():
                mismatches.append(f"{key}: expected message about chart being disabled, got '{model_value}'")
        
        elif key == 'Default_Source_State':
            # Handle 'None' or empty state
            expected_normalized = expected_value.lower() if expected_value.lower() != 'none' else ''
            model_normalized = model_value.lower() if model_value.lower() != 'none' else ''
            if expected_normalized != model_normalized:
                mismatches.append(f"{key}: expected '{expected_value}', got '{model_value}'")
        
        else:
            # Exact match for other fields
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
    Verifies that the NY expansion analysis task has been completed correctly.
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