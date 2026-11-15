# AI coaching, key storage and parent controls

## Data flow

1. Parent signs into JChess over HTTPS and pastes a project API key once in **AI coach**.
2. The browser sends the key over HTTPS only to the JChess backend, never to OpenAI directly. JChess encrypts the key using Fernet authenticated encryption, derived from the server-side `AI_ENCRYPTION_KEY` environment variable. PostgreSQL stores the ciphertext, not the raw key. The key is **never sent back** to a browser; the status API returns only a boolean `has_key`.
3. The parent may enable or disable AI, set a limit of 1–10 reports a day, replace the key or permanently delete the saved ciphertext. The child cannot access these settings.
4. Only when a parent clicks **Get learning recommendations** does the backend decrement its per-parent daily budget and call the official OpenAI API over HTTPS. The `Authorization: Bearer` header contains the decrypted key (sent exclusively server-to-OpenAI).
5. JChess sends only aggregated category performance counts: attempted/correct/accuracy. It sends **no names, usernames, passwords, specific moves, board FENs or full games**.
6. The OpenAI API returns brief practice suggestions to the signed-in parent. JChess does not store the response text in PostgreSQL.
7. The saved key is not the same as a ChatGPT subscription and OpenAI API requests may incur separate charges. Configure a project budget and usage alerts in the OpenAI platform as an additional control. A request-count cap is **not** a monetary spend cap.

## Operational security

- `AI_ENCRYPTION_KEY` is generated and held in Render environment configuration; never include it in a repository, log, screenshot or frontend bundle. Losing or rotating it will make existing stored keys undecryptable, so parents must re-enter them.
- Browser sessions are HttpOnly/Secure cookies on Render. API responses set `Cache-Control: no-store`. Password changes revoke sessions on other devices.
- `ai_usage` stores one row per parent and enforces a daily limit, guarded by a PostgreSQL row lock. The day resets in UTC.
- Even a failed provider attempt consumes one quota slot, preventing unlimited retries. JChess never prints API keys or provider error payloads in logs.
- A key deletion clears the ciphertext in JChess. It cannot revoke a key issued by OpenAI: revoke it separately in the OpenAI dashboard when appropriate.
- Only the parent may initiate coaching. The child may use all guided lessons without AI or any API key.
- Provider data controls are separate from JChess storage. Under standard API settings, OpenAI does not use API inputs for model training by default; abuse-monitoring logs may be retained for up to 30 days. Check current policy at https://developers.openai.com/api/docs/guides/your-data.

## Limitations and next production hardening

- Calls per day are controlled, but token-based cost ceilings are **not** enforced in JChess; use project-level billing limits and alerts.
- The encryption secret protects the database backup from a standalone leak, but anyone with access to both the production database and the Render encryption key could still decrypt the stored keys. Restrict Render project access.
- An authorized parent's browser can create requests, so protect the parent login and change bootstrap passwords promptly.
- Automatic provider coaching and any chat for children are intentionally disabled. AI is an **optional parent tool**, never used to validate chess moves.
