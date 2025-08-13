import re
import json
import os
import sys


def verify(messages):
    """
    Verify that the agent has successfully performed complex search and filtering operations
    in the Magento Admin panel and extracted all required information correctly.

    Args:
        messages: List of message dictionaries containing the conversation

    Returns:
        Dictionary with 'valid' boolean and 'reason' string
    """

    # Find the last assistant message with status "completed" and type "message"
    answer_content = None
    for message in reversed(messages):
        if (
            message.get("role") == "assistant"
            and message.get("status") == "completed"
            and message.get("type") == "message"
            and message.get("content")
        ):
            # Extract text from content structure
            content = message["content"]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "output_text":
                        text = item.get("text", "")
                        # Look for answer tags
                        answer_match = re.search(
                            r"<answer>(.*?)</answer>", text, re.DOTALL
                        )
                        if answer_match:
                            answer_content = answer_match.group(1).strip()
                            break
            elif isinstance(content, str):
                # Look for answer tags in string content
                answer_match = re.search(r"<answer>(.*?)</answer>", content, re.DOTALL)
                if answer_match:
                    answer_content = answer_match.group(1).strip()
                    break

            if answer_content:
                break

    if not answer_content:
        return {"valid": False, "reason": "No answer found in <answer> tags"}

    # Expected format - each line should have a key|value pair
    expected_keys = [
        "TankSearchCount",
        "ZeroResultsCount",
        "HighestUseTerm",
        "Results20to30Term",
        "Hits15PlusCount",
        "ID10to15MaxResults",
        "DefaultStoreViewCount",
        "OneResultTerm",
        "HighestResultLastSearch",
        "Position3Bestseller",
        "TopUseTerm",
        "FirstNonZeroResult",
        "TotalUniqueTerms",
    ]

    # Parse the answer
    lines = answer_content.strip().split("\n")

    # Check if we have exactly 13 lines
    if len(lines) != 13:
        return {"valid": False, "reason": f"Expected 13 data lines, found {len(lines)}"}

    # Parse each line and validate format
    extracted_data = {}
    for line in lines:
        if "|" not in line:
            return {
                "valid": False,
                "reason": f"Invalid format in line: {line}. Expected 'key|value' format",
            }

        parts = line.split("|", 1)
        if len(parts) != 2:
            return {"valid": False, "reason": f"Invalid format in line: {line}"}

        key, value = parts
        extracted_data[key] = value

    # Check all required keys are present
    missing_keys = set(expected_keys) - set(extracted_data.keys())
    if missing_keys:
        return {
            "valid": False,
            "reason": f"Missing required keys: {', '.join(missing_keys)}",
        }

    # Validate specific data formats and expected values based on the current data

    # 1. TankSearchCount should be a number (2 terms containing 'tank')
    if not extracted_data["TankSearchCount"].isdigit():
        return {
            "valid": False,
            "reason": f"TankSearchCount should be a number, got: {extracted_data['TankSearchCount']}",
        }

    # Expected: "Antonia Racer Tank" and "tanks" contain 'tank'
    if extracted_data["TankSearchCount"] != "2":
        return {
            "valid": False,
            "reason": f"TankSearchCount should be '2', got: {extracted_data['TankSearchCount']}",
        }

    # 2. ZeroResultsCount should be a number (nike has 0 results)
    if not extracted_data["ZeroResultsCount"].isdigit():
        return {
            "valid": False,
            "reason": f"ZeroResultsCount should be a number, got: {extracted_data['ZeroResultsCount']}",
        }

    if extracted_data["ZeroResultsCount"] != "1":
        return {
            "valid": False,
            "reason": f"ZeroResultsCount should be '1', got: {extracted_data['ZeroResultsCount']}",
        }

    # 3. HighestUseTerm should be in format "term:uses"
    if ":" not in extracted_data["HighestUseTerm"]:
        return {
            "valid": False,
            "reason": f"HighestUseTerm should be in format 'term:uses', got: {extracted_data['HighestUseTerm']}",
        }

    # hollister has 19 uses (highest among terms with > 10 uses)
    if extracted_data["HighestUseTerm"] != "hollister:19":
        return {
            "valid": False,
            "reason": f"HighestUseTerm should be 'hollister:19', got: {extracted_data['HighestUseTerm']}",
        }

    # 4. Results20to30Term should be in format "term:results"
    if ":" not in extracted_data["Results20to30Term"]:
        return {
            "valid": False,
            "reason": f"Results20to30Term should be in format 'term:results', got: {extracted_data['Results20to30Term']}",
        }

    # Both "tanks" and "Antonia Racer Tank" have 23 results (between 20-30)
    valid_results20to30 = ["tanks:23", "Antonia Racer Tank:23"]
    # Check if answer contains one of the valid values or both separated by |
    if not any(
        val in extracted_data["Results20to30Term"] for val in valid_results20to30
    ):
        return {
            "valid": False,
            "reason": f"Results20to30Term should contain 'tanks:23' or 'Antonia Racer Tank:23', got: {extracted_data['Results20to30Term']}",
        }

    # 5. Hits15PlusCount should be a number (only hollister has 19 hits > 15)
    if not extracted_data["Hits15PlusCount"].isdigit():
        return {
            "valid": False,
            "reason": f"Hits15PlusCount should be a number, got: {extracted_data['Hits15PlusCount']}",
        }

    if extracted_data["Hits15PlusCount"] != "1":
        return {
            "valid": False,
            "reason": f"Hits15PlusCount should be '1', got: {extracted_data['Hits15PlusCount']}",
        }

    # 6. ID10to15MaxResults should be in format "term:results"
    if ":" not in extracted_data["ID10to15MaxResults"]:
        return {
            "valid": False,
            "reason": f"ID10to15MaxResults should be in format 'term:results', got: {extracted_data['ID10to15MaxResults']}",
        }

    # ID 11 is hollister (1 result), ID 13 is Antonia Racer Tank (23 results)
    if extracted_data["ID10to15MaxResults"] != "Antonia Racer Tank:23":
        return {
            "valid": False,
            "reason": f"ID10to15MaxResults should be 'Antonia Racer Tank:23', got: {extracted_data['ID10to15MaxResults']}",
        }

    # 7. DefaultStoreViewCount should be a number (all 7 terms are from Default Store View)
    if not extracted_data["DefaultStoreViewCount"].isdigit():
        return {
            "valid": False,
            "reason": f"DefaultStoreViewCount should be a number, got: {extracted_data['DefaultStoreViewCount']}",
        }

    if extracted_data["DefaultStoreViewCount"] != "7":
        return {
            "valid": False,
            "reason": f"DefaultStoreViewCount should be '7', got: {extracted_data['DefaultStoreViewCount']}",
        }

    # 8. OneResultTerm should be in format "term:uses"
    if ":" not in extracted_data["OneResultTerm"]:
        return {
            "valid": False,
            "reason": f"OneResultTerm should be in format 'term:uses', got: {extracted_data['OneResultTerm']}",
        }

    # Both hollister and WP10 have exactly 1 result
    valid_one_result = ["hollister:19", "WP10:1"]
    if not any(val in extracted_data["OneResultTerm"] for val in valid_one_result):
        return {
            "valid": False,
            "reason": f"OneResultTerm should contain 'hollister:19' or 'WP10:1', got: {extracted_data['OneResultTerm']}",
        }

    # 9. HighestResultLastSearch should be in format "term:results"
    if ":" not in extracted_data["HighestResultLastSearch"]:
        return {
            "valid": False,
            "reason": f"HighestResultLastSearch should be in format 'term:results', got: {extracted_data['HighestResultLastSearch']}",
        }

    # In Last Search Terms: tanks and Antonia Racer Tank both have 23 results (highest)
    valid_highest_last = ["tanks:23", "Antonia Racer Tank:23"]
    if not any(
        val in extracted_data["HighestResultLastSearch"] for val in valid_highest_last
    ):
        return {
            "valid": False,
            "reason": f"HighestResultLastSearch should contain 'tanks:23' or 'Antonia Racer Tank:23', got: {extracted_data['HighestResultLastSearch']}",
        }

    # 10. Position3Bestseller should be in format "product:quantity"
    if ":" not in extracted_data["Position3Bestseller"]:
        return {
            "valid": False,
            "reason": f"Position3Bestseller should be in format 'product:quantity', got: {extracted_data['Position3Bestseller']}",
        }

    # Position 3 in Bestsellers is "Sprite Stasis Ball 65 cm" with quantity 6
    if extracted_data["Position3Bestseller"] != "Sprite Stasis Ball 65 cm:6":
        return {
            "valid": False,
            "reason": f"Position3Bestseller should be 'Sprite Stasis Ball 65 cm:6', got: {extracted_data['Position3Bestseller']}",
        }

    # 11. TopUseTerm should be in format "term:uses"
    if ":" not in extracted_data["TopUseTerm"]:
        return {
            "valid": False,
            "reason": f"TopUseTerm should be in format 'term:uses', got: {extracted_data['TopUseTerm']}",
        }

    # hollister has 19 uses (highest)
    if extracted_data["TopUseTerm"] != "hollister:19":
        return {
            "valid": False,
            "reason": f"TopUseTerm should be 'hollister:19', got: {extracted_data['TopUseTerm']}",
        }

    # 12. FirstNonZeroResult should be in format "term:results"
    if ":" not in extracted_data["FirstNonZeroResult"]:
        return {
            "valid": False,
            "reason": f"FirstNonZeroResult should be in format 'term:results', got: {extracted_data['FirstNonZeroResult']}",
        }

    # When sorted by results ascending, first non-zero is WP10 (has 1 result)
    if extracted_data["FirstNonZeroResult"] != "WP10:1":
        return {
            "valid": False,
            "reason": f"FirstNonZeroResult should be 'WP10:1', got: {extracted_data['FirstNonZeroResult']}",
        }

    # 13. TotalUniqueTerms should be a number
    if not extracted_data["TotalUniqueTerms"].isdigit():
        return {
            "valid": False,
            "reason": f"TotalUniqueTerms should be a number, got: {extracted_data['TotalUniqueTerms']}",
        }

    # There are 7 unique search terms in the system
    if extracted_data["TotalUniqueTerms"] != "7":
        return {
            "valid": False,
            "reason": f"TotalUniqueTerms should be '7', got: {extracted_data['TotalUniqueTerms']}",
        }

    # All validations passed
    return {
        "valid": True,
        "reason": "All complex search and filtering operations completed successfully",
    }


if __name__ == "__main__":
    # Load messages from environment variable
    messages_path = os.getenv("MCP_MESSAGES")
    if not messages_path:
        print(
            json.dumps(
                {"valid": False, "reason": "MCP_MESSAGES environment variable not set"}
            )
        )
        exit(1)

    try:
        with open(messages_path, "r") as f:
            messages = json.load(f)
    except Exception as e:
        print(
            json.dumps({"valid": False, "reason": f"Failed to load messages: {str(e)}"})
        )
        exit(1)

    # Run verification
    result = verify(messages)
    print(json.dumps(result))
    # Exit with appropriate code based on verification result
    sys.exit(0 if result["valid"] else 1)
