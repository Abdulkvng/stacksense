# StackSense Dashboard Setup (Auth + API Key Manager)

This dashboard now includes:
- Google Sign-In authentication
- Persistent user accounts in the database
- Per-user encrypted API key storage
- Usage analytics (calls, cost, latency, error rate)

## 1. Install dependencies

```bash
# from the stacksense project root
pip install -e ".[dashboard]"
```

## 2. Create Google OAuth credentials

1. Open Google Cloud Console.
2. Create or choose a project.
3. Enable the Google Identity / OAuth consent screen.
4. Create an **OAuth 2.0 Client ID** (Web application).
5. Add an authorized redirect URI:
   - `http://127.0.0.1:5000/auth/google/callback`

## 3. Set environment variables

```bash
export STACKSENSE_GOOGLE_CLIENT_ID="your_google_client_id"
export STACKSENSE_GOOGLE_CLIENT_SECRET="your_google_client_secret"

# Session secret for Flask cookies
export STACKSENSE_SESSION_SECRET="replace_with_long_random_secret"

# Key used to encrypt API keys at rest
# (can be any strong secret string)
export STACKSENSE_ENCRYPTION_KEY="replace_with_long_random_secret"

# Optional: secure cookies when behind HTTPS
# export STACKSENSE_SECURE_COOKIES=true
```

## 4. Run the dashboard

```bash
python3 run_dashboard.py
```

Open:
- `http://127.0.0.1:5000`

## 5. First-time usage flow

1. Click **Continue with Google**.
2. On successful callback, StackSense creates/updates your user account in `users`.
3. Open the **API Keys** tab.
4. Add provider keys (OpenAI, Anthropic, ElevenLabs, Pinecone, or custom).
5. Keys are encrypted before being written to `user_api_keys`.

## Database tables used

- `users`: authenticated dashboard users
- `user_api_keys`: per-user provider keys (encrypted)
- `events`: existing usage/cost/latency logs
- `metrics`: existing aggregated metrics table

## API endpoints

Auth:
- `GET /login`
- `GET /auth/google`
- `GET /auth/google/callback`
- `POST /logout`
- `GET /api/me`

User API keys:
- `GET /api/user/api-keys`
- `POST /api/user/api-keys`
- `PUT /api/user/api-keys/<id>`
- `DELETE /api/user/api-keys/<id>`

Metrics/events (auth required):
- `GET /api/metrics/summary?timeframe=24h`
- `GET /api/metrics/cost-breakdown?timeframe=24h`
- `GET /api/metrics/usage-over-time?timeframe=24h&interval=1h`
- `GET /api/events/recent?limit=20`

## Troubleshooting

- **Google sign-in says not configured**
  - Check `STACKSENSE_GOOGLE_CLIENT_ID` and `STACKSENSE_GOOGLE_CLIENT_SECRET`.

- **OAuth redirect mismatch**
  - Ensure Google console redirect URI exactly matches:
    - `http://127.0.0.1:5000/auth/google/callback`

- **Encryption error**
  - Install dashboard extras: `pip install -e ".[dashboard]"`
  - Set `STACKSENSE_ENCRYPTION_KEY`

- **No metrics visible**
  - Ensure events exist in `stacksense.db`.
