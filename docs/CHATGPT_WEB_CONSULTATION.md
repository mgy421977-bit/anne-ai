# ChatGPT Web consultation (local Windows)

ANNE can use **chatgpt.com** in Chrome as a **consultation instrument** (evidence only).
This is separate from the OpenAI API adapter.

## Config

```env
ANNE_CONSULTATION_PROVIDER=chatgpt_web
ANNE_CONSULTATION_FALLBACK=openai_api
# ANNE_CHATGPT_WEB_USER_DATA_DIR=C:\\Users\\YOU\\AppData\\Local\\Google\\Chrome\\User Data
ANNE_CHATGPT_WEB_TIMEOUT=90
```

Default remains API-oriented (`auto` + `ANNE_CHATGPT_CONSULTATION=true`).

## Install (Windows)

```bat
.venv\Scripts\python.exe -m pip install -e ".[api,chatgpt-web]"
.venv\Scripts\python.exe -m playwright install chrome
```

1. Sign in at https://chatgpt.com/ in Chrome.
2. Set `ANNE_CONSULTATION_PROVIDER=chatgpt_web` in `anne_config.env`.
3. Run `START_ANNE.bat`.

ANNE does **not** store ChatGPT passwords, cookies, or tokens in memory.

## CI

Real chatgpt.com is **not** run in CI. Mock tests: `tests/test_chatgpt_web_consultation.py`.
