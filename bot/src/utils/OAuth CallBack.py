# куда гугл отдает токен доступа к почте

import os
from flask import Flask, request #cерверная фигня

from google_auth_oauthlib.flow import Flow
from config.oauth_config import SCOPES, CLIENT_SECRET_FILE, REDIRECT_URI, TOKENS_DIR

app = Flask(__name__)


@app.route("/oauth/callback")
def oauth_callback():
    telegram_user_id = request.args.get("state")
    code = request.args.get("code")

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=telegram_user_id,
    )

    flow.fetch_token(code=code)
    creds = flow.credentials

    os.makedirs(TOKENS_DIR, exist_ok=True)
    token_path = os.path.join(TOKENS_DIR, f"{telegram_user_id}.json")

    with open(token_path, "w") as f:
        f.write(creds.to_json())

    return "✅ Gmail успешно подключён. Можешь вернуться в Telegram."
