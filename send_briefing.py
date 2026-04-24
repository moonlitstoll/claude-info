#!/usr/bin/env python3
"""YouTube 브리핑을 Gmail로 전송합니다.

전송 방법 A — Gmail OAuth (독립 실행):
  pip install google-auth google-auth-oauthlib google-api-python-client
  YOUTUBE_API_KEY=... BRIEFING_TO=me@example.com python send_briefing.py

전송 방법 B — Claude Code Gmail MCP (권장):
  python send_briefing.py --mock --save    # briefing_result.json 생성
  # Claude Code가 briefing_result.json 을 읽어 Gmail MCP로 초안 생성

환경변수:
  YOUTUBE_API_KEY  — YouTube Data API 키 (--mock 시 불필요)
  BRIEFING_TO      — 수신 이메일 주소
  GMAIL_CREDS_FILE — OAuth2 credentials.json 경로 (기본: credentials.json)
  GMAIL_TOKEN_FILE — 저장된 토큰 파일 경로 (기본: token.json)
"""

import os
import sys
import json
import argparse
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from youtube_briefing import run as generate_briefing

RECIPIENT = os.environ.get("BRIEFING_TO", "")
CREDS_FILE = os.environ.get("GMAIL_CREDS_FILE", "credentials.json")
TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "token.json")


def send_via_oauth(to: str, subject: str, html: str, text: str) -> str:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit(
            "Google 라이브러리 없음. 설치: "
            "pip install google-auth google-auth-oauthlib google-api-python-client"
        )

    scopes = ["https://www.googleapis.com/auth/gmail.send"]
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, scopes)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id", "")


def save_for_mcp(subject: str, html: str, text: str) -> None:
    """briefing_result.json 을 저장합니다. Claude Code Gmail MCP가 이 파일을 읽어 전송합니다."""
    output = {"subject": subject, "html": html, "text": text}
    with open("briefing_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("[저장] briefing_result.json 생성 완료")
    print()
    print("Claude Code에서 다음 명령으로 Gmail 초안을 생성하세요:")
    print("  'briefing_result.json 을 읽어 Gmail 초안으로 보내줘'")


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 브리핑 Gmail 전송")
    parser.add_argument("--mock", action="store_true", help="샘플 데이터로 실행 (API 키 불필요)")
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="OAuth 대신 briefing_result.json 으로 저장 (Claude Code Gmail MCP 사용)",
    )
    args = parser.parse_args()

    print("[1/2] 브리핑 생성 중…")
    subject, html, text = generate_briefing(mock=args.mock)

    if args.mcp:
        print("[2/2] MCP용 파일 저장 중…")
        save_for_mcp(subject, html, text)
        return

    if not RECIPIENT:
        sys.exit("BRIEFING_TO 환경변수에 수신 이메일을 지정하세요.\n대안: --mcp 플래그로 파일 저장 후 Claude Code로 전송")

    print(f"[2/2] '{RECIPIENT}'로 Gmail 전송 중…")
    msg_id = send_via_oauth(RECIPIENT, subject, html, text)
    print(f"전송 완료 (message_id={msg_id})")


if __name__ == "__main__":
    main()
