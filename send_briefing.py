#!/usr/bin/env python3
"""브리핑 이메일 전송 스크립트.

두 가지 전송 방법을 지원합니다:
  1. Gmail OAuth2 (--oauth)  : 서버 자동화 / cron 환경
  2. Gmail MCP (기본, 대화형) : Claude Code 세션에서 직접 실행

환경변수:
  YOUTUBE_API_KEY  — YouTube Data API 키 (필수, --demo 없이 실행 시)
  BRIEFING_TO      — 수신 이메일 주소 (OAuth 모드 필수)
  GMAIL_CREDS_FILE — OAuth2 credentials.json 경로 (기본: credentials.json)
  GMAIL_TOKEN_FILE — 저장된 토큰 파일 경로 (기본: token.json)
"""

import os
import sys
import json
import argparse
import subprocess

RECIPIENT = os.environ.get("BRIEFING_TO", "")


# ---------------------------------------------------------------------------
# OAuth2 전송 (서버 자동화용)
# ---------------------------------------------------------------------------

def _send_via_oauth(subject: str, html: str, text: str) -> None:
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    creds_file = os.environ.get("GMAIL_CREDS_FILE", "credentials.json")
    token_file = os.environ.get("GMAIL_TOKEN_FILE", "token.json")

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"✅ OAuth 전송 완료 (message_id={result.get('id', '')})")


# ---------------------------------------------------------------------------
# MCP 전송 (Claude Code 세션용) — JSON 페이로드 출력
# ---------------------------------------------------------------------------

def _print_mcp_payload(subject: str, html: str, text: str) -> None:
    payload = {"subject": subject, "html": html, "text": text}
    print("\n=== Gmail MCP 페이로드 (Claude가 mcp__Gmail__create_draft 로 전송) ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("=" * 70)
    print("Claude Code 세션에서 위 내용을 Gmail MCP 도구로 전달하세요.")


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 브리핑을 Gmail로 전송")
    parser.add_argument("--demo", action="store_true", help="데모 데이터로 실행")
    parser.add_argument("--oauth", action="store_true", help="Gmail OAuth2로 직접 전송")
    args = parser.parse_args()

    print("[1/2] 브리핑 생성 중…")
    cmd = [sys.executable, "youtube_briefing.py", "--json"]
    if args.demo:
        cmd.append("--demo")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    # youtube_briefing.py 가 stderr 로 진행 메시지를 출력하므로 stdout 만 파싱
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    subject, html, text = payload["subject"], payload["html"], payload["text"]

    print("[2/2] Gmail 전송 중…")
    if args.oauth:
        if not RECIPIENT:
            sys.exit("BRIEFING_TO 환경변수에 수신 이메일을 지정하세요.")
        _send_via_oauth(subject, html, text)
    else:
        _print_mcp_payload(subject, html, text)


if __name__ == "__main__":
    main()
