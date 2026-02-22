# Discord Bot

discord.py 2.x bot that listens to messages, publishes to Redis Streams, and provides slash commands.

## Architecture

- **Cogs** for modularity: each cog handles one domain
- `on_message` → hash author ID → Redis Stream XADD (not directly to pipeline)
- All slash commands are **ephemeral** (only visible to the invoking user)
- Consent UI uses Discord components (Buttons, Selects)

## Cogs

- `cogs/listener.py` — `on_message` handler: captures messages from monitored channels, hashes author, publishes to Redis Stream
- `cogs/consent.py` — `/privacy` slash command: shows consent options (knowledge base, AI training), stores in API
- `cogs/search.py` — `/nw-ask` slash command: searches knowledge base via API, returns embedded result

## Redis Streams

- Stream key: `messages:{server_id}:{channel_id}`
- Message format: `{author_hash, content, timestamp, reply_to, mentions, has_code}`
- Consumer group: `extraction_workers`
- Batch trigger: 50 messages OR 5-minute window

## PII at Bot Level

- Author IDs are SHA-256 hashed BEFORE publishing to Redis
- Real Discord user IDs never leave the bot process
- Usernames in message content are handled by the downstream anonymizer service

## Intents Required

- `message_content` (privileged)
- `guilds`
- `guild_messages`
