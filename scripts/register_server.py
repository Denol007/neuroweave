"""Register a Discord server and its channels in the database.

Usage:
    python scripts/register_server.py <server_discord_id> <server_name> <channel_id1> [channel_id2 ...]

Example:
    python scripts/register_server.py 1234567890 "My Server" 111222333 444555666

Get IDs: in Discord, enable Developer Mode (Settings → Advanced),
then right-click server/channel → Copy ID.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings
from api.models.channel import Channel
from api.models.server import Server, ServerPlan

sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
engine = create_engine(sync_url)


def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/register_server.py <server_discord_id> <server_name> <channel_id1> [channel_id2 ...]")
        print("")
        print("Get IDs: Discord → Settings → Advanced → Developer Mode ON")
        print("Then right-click server/channel → Copy ID")
        sys.exit(1)

    server_discord_id = sys.argv[1]
    server_name = sys.argv[2]
    channel_ids = sys.argv[3:]

    with Session(engine) as db:
        # Check if server exists
        existing = db.execute(
            text("SELECT id FROM servers WHERE discord_id = :did"),
            {"did": server_discord_id},
        ).fetchone()

        if existing:
            server_id = existing[0]
            print(f"Server already exists (id={server_id})")
        else:
            server = Server(
                discord_id=server_discord_id,
                name=server_name,
                plan=ServerPlan.FREE,
            )
            db.add(server)
            db.flush()
            server_id = server.id
            print(f"Created server: {server_name} (id={server_id})")

        # Add channels
        for ch_id in channel_ids:
            existing_ch = db.execute(
                text("SELECT id FROM channels WHERE discord_id = :did"),
                {"did": ch_id},
            ).fetchone()

            if existing_ch:
                # Update to monitored
                db.execute(
                    text("UPDATE channels SET is_monitored = true WHERE discord_id = :did"),
                    {"did": ch_id},
                )
                print(f"  Channel {ch_id}: already exists, set to monitored")
            else:
                channel = Channel(
                    server_id=server_id,
                    discord_id=ch_id,
                    name=f"channel-{ch_id}",
                    is_monitored=True,
                )
                db.add(channel)
                print(f"  Channel {ch_id}: created (monitored)")

        db.commit()

    print()
    print("Done! Now start the bot:")
    print("  .venv/bin/python -m bot.main")
    print()
    print("The bot will listen to messages in the registered channels.")
    print("When 50 messages accumulate (or 5 min pass), the pipeline runs automatically.")


if __name__ == "__main__":
    main()
