import sys
import re
from notion_client import Client
from tasks.utils import notion_utils
from collections import Counter


def validate_comma_separated(text: str, expected_items: list) -> bool:
    """
    Validates that a comma-separated list contains expected items (case-insensitive).
    """
    if not text or not expected_items:
        return False

    items = [item.strip().lower() for item in text.split(",")]
    expected_lower = [item.lower() for item in expected_items]

    for expected in expected_lower:
        if not any(expected in item or item in expected for item in items):
            return False
    return True


def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that the inline hyperfocus analysis section has been inserted
    between the 'Why Use the Term "Hyperfocus"?' callout and the divider
    line that follows it inside the Self Assessment page.
    """
    # Find the Self Assessment page
    self_assessment_page_id = main_id
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            self_assessment_page_id = found_id

    if not self_assessment_page_id:
        self_assessment_page_id = notion_utils.find_page(notion, "Self Assessment")

    if not self_assessment_page_id:
        print("Error: Self Assessment page not found.", file=sys.stderr)
        return False

    children = notion.blocks.children.list(block_id=self_assessment_page_id).get(
        "results", []
    )

    # Locate the 'Why Use the Term "Hyperfocus"?' callout and the first divider after it.
    callout_idx = -1
    divider_idx = -1
    for i, child in enumerate(children):
        if callout_idx == -1 and child.get("type") == "callout":
            text = notion_utils.get_block_plain_text(child)
            if "Why Use the Term" in text and "Hyperfocus" in text:
                callout_idx = i
        elif callout_idx != -1 and child.get("type") == "divider":
            divider_idx = i
            break

    if callout_idx == -1:
        print(
            "Error: Could not find 'Why Use the Term \"Hyperfocus\"?' callout.",
            file=sys.stderr,
        )
        return False

    if divider_idx == -1:
        print("Error: Could not find divider after the callout.", file=sys.stderr)
        return False

    # Section blocks: strictly between the callout and the divider.
    section_blocks = children[callout_idx + 1 : divider_idx]

    # Find the worksheet database (recursively, since it lives inside a toggle).
    database_id = None
    for block in notion_utils.get_all_blocks_recursively(
        notion, self_assessment_page_id
    ):
        if block.get("type") == "child_database":
            db_data = notion.databases.retrieve(database_id=block["id"])
            db_title = "".join(
                [t.get("plain_text", "") for t in db_data.get("title", [])]
            )
            if "Hyperfocus Self-Assessment Worksheet" in db_title:
                database_id = block["id"]
                break

    if not database_id:
        print(
            "Error: Database 'Hyperfocus Self-Assessment Worksheet' not found.",
            file=sys.stderr,
        )
        return False

    # Top 2 strategies across ALL entries in the database (not filtered).
    all_sessions = notion.databases.query(database_id=database_id).get("results", [])
    all_strategies = []
    for s in all_sessions:
        strats = (
            s.get("properties", {})
            .get("Key Strategies Used", {})
            .get("multi_select", [])
        )
        all_strategies.extend([x.get("name") for x in strats])
    strategy_counts = Counter(all_strategies)
    top_2_strategies = strategy_counts.most_common(2)

    # Filtered sessions (>80% completion + at least one challenge).
    query_results = notion.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Work Completion Rate", "number": {"greater_than": 0.8}},
                {"property": "Challenges", "multi_select": {"is_not_empty": True}},
            ]
        },
    ).get("results", [])

    expected_sessions = {}
    for r in query_results:
        date_prop = r.get("properties", {}).get("Date", {}).get("date", {})
        activity_prop = (
            r.get("properties", {}).get("Activity", {}).get("select", {})
        )
        if date_prop and date_prop.get("start") and activity_prop:
            date_str = date_prop["start"]
            activity_name = activity_prop.get("name", "")
            focus_factors = [
                f.get("name", "")
                for f in r.get("properties", {})
                .get("Focus Factors", {})
                .get("multi_select", [])
            ]
            challenges = [
                c.get("name", "")
                for c in r.get("properties", {})
                .get("Challenges", {})
                .get("multi_select", [])
            ]
            strategies = [
                s.get("name", "")
                for s in r.get("properties", {})
                .get("Key Strategies Used", {})
                .get("multi_select", [])
            ]
            energy = r.get("properties", {}).get("Energy Level", {}).get("number")
            mood = r.get("properties", {}).get("Mood", {}).get("number")
            completion = (
                r.get("properties", {})
                .get("Work Completion Rate", {})
                .get("number")
            )
            expected_sessions[date_str] = {
                "activity": activity_name,
                "focus_factors": focus_factors,
                "challenges": challenges,
                "strategies": strategies,
                "energy": energy,
                "mood": mood,
                "completion": completion,
            }

    # Walk section blocks.
    has_callout = False
    has_top_strategies = False
    callout_seen_at = -1
    found_sessions = {}
    session_count = 0
    current_session_date = None
    current_session_data = None
    session_bullet_points = {}

    for i, block in enumerate(section_blocks):
        block_type = block.get("type")

        if block_type == "callout":
            text = notion_utils.get_block_plain_text(block)
            if "Top 2 Most Effective Strategies" in text:
                has_callout = True
                if callout_seen_at == -1:
                    callout_seen_at = i
                if len(top_2_strategies) >= 2:
                    s1, n1 = top_2_strategies[0]
                    s2, n2 = top_2_strategies[1]
                    t1 = f"{s1} (used in {n1} sessions)"
                    t2 = f"{s2} (used in {n2} sessions)"
                    if t1 in text and t2 in text:
                        has_top_strategies = True

        if block_type == "heading_2":
            heading_text = notion_utils.get_block_plain_text(block)
            # A new heading_2 closes the previous session's bullet scope.
            current_session_date = None
            current_session_data = None
            for date_str, sd in expected_sessions.items():
                expected_heading = f"{date_str} {sd['activity']}"
                if expected_heading in heading_text:
                    found_sessions[date_str] = sd
                    session_count += 1
                    current_session_date = date_str
                    current_session_data = sd
                    session_bullet_points[date_str] = []
                    break

        if block_type == "bulleted_list_item" and current_session_data:
            bullet_text = notion_utils.get_block_plain_text(block)
            if current_session_date:
                session_bullet_points[current_session_date].append(bullet_text)

            if bullet_text.startswith("Focus factors"):
                content = bullet_text.split(":", 1)[1].strip()
                expected_factors = current_session_data.get("focus_factors", [])
                if not validate_comma_separated(content, expected_factors):
                    print(
                        f"Error: Focus factors mismatch for {current_session_date}. Expected: {expected_factors}, Found: {content}",
                        file=sys.stderr,
                    )
                    return False

            elif "Energy" in bullet_text and "Mood" in bullet_text:
                em = re.search(r"Energy:\s*(\d+)/10", bullet_text)
                mm = re.search(r"Mood:\s*(\d+)/10", bullet_text)
                if em and mm:
                    found_energy = int(em.group(1))
                    found_mood = int(mm.group(1))
                    expected_energy = current_session_data.get("energy")
                    expected_mood = current_session_data.get("mood")
                    if found_energy != expected_energy or found_mood != expected_mood:
                        print(
                            f"Error: Energy/Mood mismatch for {current_session_date}. Expected: Energy: {expected_energy}/10, Mood: {expected_mood}/10",
                            file=sys.stderr,
                        )
                        return False
                else:
                    print(
                        f"Error: Invalid Energy/Mood format for {current_session_date}",
                        file=sys.stderr,
                    )
                    return False

            elif bullet_text.startswith("Challenges"):
                content = bullet_text.split(":", 1)[1].strip()
                expected_challenges = current_session_data.get("challenges", [])
                if not validate_comma_separated(content, expected_challenges):
                    print(
                        f"Error: Challenges mismatch for {current_session_date}. Expected: {expected_challenges}, Found: {content}",
                        file=sys.stderr,
                    )
                    return False

            elif bullet_text.startswith("Strategies"):
                content = bullet_text.split(":", 1)[1].strip()
                expected_strategies = current_session_data.get("strategies", [])
                if len(expected_strategies) > 0 and not validate_comma_separated(
                    content, expected_strategies
                ):
                    print(
                        f"Error: Strategies mismatch for {current_session_date}. Expected: {expected_strategies}, Found: {content}",
                        file=sys.stderr,
                    )
                    return False

            elif bullet_text.startswith("Completion"):
                cm = re.search(r"Completion:\s*(\d+)%", bullet_text)
                if cm:
                    found_completion = int(cm.group(1))
                    expected_completion = int(
                        current_session_data.get("completion", 0) * 100
                    )
                    if found_completion != expected_completion:
                        print(
                            f"Error: Completion rate mismatch for {current_session_date}. Expected: {expected_completion}%, Found: {found_completion}%",
                            file=sys.stderr,
                        )
                        return False
                else:
                    print(
                        f"Error: Invalid completion format for {current_session_date}",
                        file=sys.stderr,
                    )
                    return False

    # Per-session bullet completeness.
    for date_str, bullets in session_bullet_points.items():
        bt = " ".join(bullets)
        required = [
            "Focus factors",
            "Energy:",
            "Mood:",
            "Challenges",
            "Strategies",
            "Completion",
        ]
        missing = [r for r in required if r not in bt]
        if missing:
            print(
                f"Error: Missing bullet points for session {date_str}: {', '.join(missing)}",
                file=sys.stderr,
            )
            return False

    # Final structural checks.
    if not has_callout:
        print(
            "Error: Missing callout block with 'Top 2 Most Effective Strategies' between the 'Why Use the Term \"Hyperfocus\"?' callout and the following divider.",
            file=sys.stderr,
        )
        return False

    if not has_top_strategies and len(top_2_strategies) > 0:
        print(
            "Error: Callout doesn't contain correct top 2 strategy information.",
            file=sys.stderr,
        )
        return False

    # The summary callout must come before any session heading_2.
    first_h2_idx = next(
        (i for i, b in enumerate(section_blocks) if b.get("type") == "heading_2"),
        len(section_blocks),
    )
    if callout_seen_at == -1 or callout_seen_at > first_h2_idx:
        print(
            "Error: 'Top 2 Most Effective Strategies' callout must come before any session heading.",
            file=sys.stderr,
        )
        return False

    if query_results and session_count == 0:
        print(
            "Error: No session sections found with proper headings.", file=sys.stderr
        )
        return False

    missing = [d for d in expected_sessions if d not in found_sessions]
    if missing:
        print(
            f"Error: Missing session sections for dates: {', '.join(missing)}",
            file=sys.stderr,
        )
        return False

    if query_results and session_count < len(query_results):
        print(
            f"Warning: Found {session_count} session sections but expected {len(query_results)}.",
            file=sys.stderr,
        )

    print(
        "Success: Hyperfocus analysis section created with proper structure and content."
    )
    return True


def main():
    """
    Executes the verification process and exits with a status code.
    """
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
