import argparse
import json
import re
from pathlib import Path


def decode_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def strip_html(value: str) -> str:
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def main():
    parser = argparse.ArgumentParser(description="Export a Longman MDX file into backend JSON.")
    parser.add_argument("--mdx", required=True, help="Path to Longman .mdx file")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--limit", type=int, default=0, help="Optional max entries for testing")
    args = parser.parse_args()

    try:
        from readmdict import MDX
    except ImportError as exc:
        raise SystemExit("Please install readmdict first: python -m pip install readmdict") from exc

    mdx = MDX(args.mdx)
    output: dict[str, dict[str, str]] = {}

    for index, (key, value) in enumerate(mdx.items(), start=1):
        word = decode_value(key).strip().lower()
        if not word or " " in word:
            continue

        raw_html = decode_value(value)
        output[word] = {
            "html": raw_html,
            "text": strip_html(raw_html)[:1600],
        }

        if args.limit and len(output) >= args.limit:
            break

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(output)} entries to {output_path}")


if __name__ == "__main__":
    main()
