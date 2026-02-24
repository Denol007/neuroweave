"""CLI: Fetch GitHub Discussions and process through pipeline.

Usage:
    python scripts/fetch_github.py vercel/next.js [--limit 10] [--category Q&A]

Requires GITHUB_TOKEN and ANTHROPIC_API_KEY in .env
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub Discussions")
    parser.add_argument("repo", help="owner/repo (e.g. vercel/next.js)")
    parser.add_argument("--limit", type=int, default=10, help="Max discussions to fetch")
    parser.add_argument("--all", action="store_true", help="Fetch ALL discussions (backfill history)")
    parser.add_argument("--category", type=str, help="Filter by category name")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but don't process")
    args = parser.parse_args()

    parts = args.repo.split("/")
    if len(parts) != 2:
        print(f"Error: repo must be owner/repo format, got '{args.repo}'")
        sys.exit(1)

    owner, repo = parts

    from api.config import settings

    if not settings.GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN not set in .env")
        sys.exit(1)

    from api.services.github_fetcher import GitHubDiscussionsFetcher

    fetcher = GitHubDiscussionsFetcher(settings.GITHUB_TOKEN)

    async def run():
        # Fetch categories
        print(f"Fetching categories for {owner}/{repo}...")
        categories = await fetcher.fetch_categories(owner, repo)
        print(f"  Categories: {', '.join(c['name'] for c in categories)}")

        # Filter category if specified
        category_id = None
        if args.category:
            for cat in categories:
                if cat["name"].lower() == args.category.lower():
                    category_id = cat["id"]
                    break
            if not category_id:
                print(f"  Warning: category '{args.category}' not found, fetching all")

        # Fetch discussions
        limit = 10000 if args.all else args.limit
        print(f"Fetching discussions (limit={limit}{', FULL BACKFILL' if args.all else ''})...")
        discussions = await fetcher.fetch_discussions(owner, repo, category_id=category_id, limit=limit)
        print(f"  Found {len(discussions)} discussions")

        for i, d in enumerate(discussions, 1):
            comments = len(d.get("comments", []))
            answer = "YES" if d.get("answer") else "no"
            print(f"  {i}. [{d['category'].get('name', '?')}] {d['title'][:60]} ({comments} comments, answer={answer})")

        if args.dry_run:
            print("\n--dry-run: skipping pipeline processing")
            return

        # Process through pipeline
        if not settings.ANTHROPIC_API_KEY:
            print("\nWarning: ANTHROPIC_API_KEY not set, skipping pipeline")
            return

        print(f"\nProcessing {len(discussions)} discussions through pipeline...")
        from api.tasks.process_messages import process_message_batch

        processed = 0
        for d in discussions:
            messages = fetcher.discussion_to_messages(d)
            if len(messages) < 2:
                continue

            category = d.get("category", {})
            channel_id = category.get("id", "uncategorized")

            try:
                result = process_message_batch(
                    channel_id=channel_id,
                    server_id=f"{owner}/{repo}",
                    messages=messages,
                    source_type="github",
                )
                quality = result.get("quality_score", 0)
                classification = result.get("classification", "?")
                print(f"  [{classification}] {d['title'][:50]} → quality={quality}")
                processed += 1
            except Exception as e:
                print(f"  ERROR: {d['title'][:50]} → {e}")

        print(f"\nDone! Processed {processed}/{len(discussions)} discussions")

    asyncio.run(run())


if __name__ == "__main__":
    main()
