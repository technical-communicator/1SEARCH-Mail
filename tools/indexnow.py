#!/usr/bin/env python3
"""Tell Bing (and other IndexNow search engines) which pages changed.

IndexNow is a free "ping": instead of waiting for Bing to notice a new
event or blog post, we send it the list of new or updated addresses.
Bing then checks they're really ours by reading the key file at
https://www.searchcentralfl.com/<key>.txt (the build writes it; the key
is in seo/site.json).

Which pages changed? Every build records each public page's fingerprint
in seo/published.json. This script compares that file now with an older
version from git, and sends every address that is new, changed or gone.

Usage (from the repo root):
    python3 tools/indexnow.py --since HEAD~1     # changes in the last commit
    python3 tools/indexnow.py --since <commit>   # changes since that commit
    python3 tools/indexnow.py --all              # every page
    add --dry-run to print the list without sending it

The GitHub workflow .github/workflows/indexnow.yml runs this
automatically after each push to main that changes seo/published.json,
once GitHub Pages has had time to publish the new pages.
"""

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "seo" / "site.json").read_text(encoding="utf-8"))
PUBLISHED = "seo/published.json"
ENDPOINT = "https://api.indexnow.org/indexnow"


def published_at(revision):
    """seo/published.json as it was at a git commit ({} if it didn't exist)."""
    result = subprocess.run(["git", "show", f"{revision}:{PUBLISHED}"],
                            cwd=ROOT, capture_output=True, text=True)
    return json.loads(result.stdout) if result.returncode == 0 else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", help="git commit to compare with, e.g. HEAD~1")
    parser.add_argument("--all", action="store_true", help="send every page")
    parser.add_argument("--dry-run", action="store_true", help="only print the list")
    args = parser.parse_args()

    now = json.loads((ROOT / PUBLISHED).read_text(encoding="utf-8"))
    if args.all or not args.since:
        urls = sorted(now)
    else:
        before = published_at(args.since)
        changed = [u for u, info in now.items() if before.get(u, {}).get("hash") != info["hash"]]
        removed = [u for u in before if u not in now]  # IndexNow also wants to hear about removed pages
        urls = sorted(changed + removed)

    if not urls:
        print("No pages changed, nothing to send.")
        return
    print(f"{len(urls)} page(s):")
    for url in urls:
        print("  " + url)
    if args.dry_run:
        return

    base = SITE["base_url"].rstrip("/")
    key = SITE["indexnow_key"]
    body = json.dumps({
        "host": base.split("://", 1)[1],
        "key": key,
        "keyLocation": f"{base}/{key}.txt",
        "urlList": urls[:10000],   # IndexNow's limit per request
    }).encode()
    request = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"IndexNow answered {response.status} (200 or 202 means it worked).")
    except urllib.error.HTTPError as error:
        # 403: the key file isn't live yet. 422: an address isn't on our site.
        sys.exit(f"IndexNow said {error.code}: {error.read().decode(errors='replace')[:300]}")


if __name__ == "__main__":
    main()
