#!/usr/bin/env python3
"""브리핑 데이터를 JSON으로 stdout에 출력합니다.

사용:
  python3 send_briefing.py

환경변수:
  YOUTUBE_API_KEY  — YouTube Data API 키 (필수)
  BRIEFING_TO      — 수신 이메일 주소 (기본: 빈 문자열)

출력:
  {"subject": "...", "html": "...", "text": "...", "to": "..."}
"""

import json
import os
import sys

from youtube_briefing import run as generate_briefing

RECIPIENT = os.environ.get("BRIEFING_TO", "")


def main() -> None:
    subject, html, text = generate_briefing()
    payload = {
        "subject": subject,
        "html": html,
        "text": text,
        "to": RECIPIENT,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
