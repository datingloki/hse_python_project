# oauth_config.py
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"] #права доступа настраиваю на google cloud

CLIENT_SECRET_FILE = "client_secret.json"
REDIRECT_URI = "http://localhost:5000/oauth2callback"  # backend URL. куда gmail будет присылать токены доступа к почте
# можно как-то сделать без сервера через ngrok (нужно почитать что это такое)
TOKENS_DIR = "tokens" # хранить на сервере нужно
