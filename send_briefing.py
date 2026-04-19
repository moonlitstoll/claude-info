#!/usr/bin/env python3
"""Gmail API를 이용해 브리핑 이메일을 전송합니다.

사전 준비:
  pip install google-auth google-auth-oauthlib google-api-python-client

환경변수:
  YOUTUBE_API_KEY  — YouTube Data API 키
  BRIEFING_TO      — 수신 이메일 주소 (예: mychannel@gmail.com)
  GMAIL_CREDS_FILE — OAuth2 credentials.json 경로 (기본: credentials.json)
  GMAIL_TOKEN_FILE — 저장된 토큰 파일 경로 (기본: token.json)
"""

import os
import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from youtube_briefing import run as generate_briefing

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDS_FILE = os.environ.get("GMAIL_CREDS_FILE", "credentials.json")
TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "token.json")
RECIPIENT = os.environ.get("BRIEFING_TO", "")


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(service, to: str, subject: str, html: str, text: str) -> str:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    return result.get("id", "")


def main():
    if not RECIPIENT:
        raise SystemExit("BRIEFING_TO 환경변수에 수신 이메일을 지정하세요.")

    print("[1/3] 브리핑 생성 중…")
    subject, html, text = generate_briefing()

    print("[2/3] Gmail 인증 중…")
    service = get_gmail_service()

    print(f"[3/3] '{RECIPIENT}'로 전송 중…")
    msg_id = send_email(service, RECIPIENT, subject, html, text)
    print(f"✅ 전송 완료 (message_id={msg_id})")


if __name__ == "__main__":
    main()
