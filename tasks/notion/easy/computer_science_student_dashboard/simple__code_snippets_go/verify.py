import sys
from notion_client import Client
from tasks.utils import notion_utils

# Expected code blocks (language=go)
EXPECTED_CODE_BLOCKS = [
    {
        "caption": "Basic Go program",
        "code": (
            'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello, World!")\n}'
        ),
    },
    {
        "caption": "For loop in Go",
        "code": ("for i := 0; i < 5; i++ {\n    fmt.Println(i)\n}"),
    },
    {
        "caption": "Function definition in Go",
        "code": ("func add(a, b int) int {\n    return a + b\n}"),
    },
]

HEADER_TEXT = "Go"


def _normalize(text: str) -> str:
    """Remove trailing spaces on each line and strip leading/trailing blank lines."""
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _find_page(notion: Client, main_id: str | None) -> str | None:
    """Return a page_id to verify against or None if not found."""
    page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            page_id = found_id
    if not page_id:
        page_id = notion_utils.find_page(notion, "Computer Science Student Dashboard")
    return page_id


def _has_bold_header_text(block, text: str) -> bool:
    """Generic bold header/paragraph check for a given text."""
    block_type = block.get("type")
    if block_type not in {"paragraph", "heading_1", "heading_2", "heading_3"}:
        return False
    rich_text_list = block.get(block_type, {}).get("rich_text", [])
    if not rich_text_list:
        return False
    plain = "".join(rt.get("plain_text", "") for rt in rich_text_list).strip()
    if plain != text:
        return False
    return any(rt.get("annotations", {}).get("bold", False) for rt in rich_text_list)


def _collect_code_blocks(blocks):
    """Return list of (code_content, caption) tuples for code blocks with language 'go'."""
    collected = []
    for block in blocks:
        if block.get("type") != "code":
            continue
        code_data = block.get("code", {})
        if code_data.get("language") != "go":
            continue
        code_plain = "".join(
            rt.get("plain_text", "") for rt in code_data.get("rich_text", [])
        )
        caption_plain = "".join(
            rt.get("plain_text", "") for rt in code_data.get("caption", [])
        )
        collected.append((code_plain, caption_plain))
    return collected


def verify(notion: Client, main_id: str | None = None) -> bool:
    page_id = _find_page(notion, main_id)
    if not page_id:
        print("Error: Target page not found.", file=sys.stderr)
        return False

    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)

    # Verify header
    header_ok = any(_has_bold_header_text(b, HEADER_TEXT) for b in all_blocks)
    if not header_ok:
        print("Failure: Bold header 'Go' not found.", file=sys.stderr)
        return False

    # Verify code blocks
    code_blocks_found = _collect_code_blocks(all_blocks)

    remaining = EXPECTED_CODE_BLOCKS.copy()
    for code, caption in code_blocks_found:
        norm_code = _normalize(code)
        for expected in remaining:
            if (
                _normalize(expected["code"]) == norm_code
                and expected["caption"] == caption
            ):
                remaining.remove(expected)
                break
    if remaining:
        missing = ", ".join(exp["caption"] for exp in remaining)
        print(
            f"Failure: Missing or incorrect Go code blocks: {missing}", file=sys.stderr
        )
        return False

    print(
        "Success: Verified Go header and required Go code blocks."
    )
    return True


def main():
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(0 if verify(notion, main_id) else 1)


if __name__ == "__main__":
    main()
