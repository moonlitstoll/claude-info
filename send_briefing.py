#!/usr/bin/env python3
"""YouTube 브리핑을 생성하고 JSON으로 출력합니다.

이 스크립트는 youtube_briefing.py로 브리핑을 생성한 뒤
JSON을 stdout에 출력합니다. Claude Code(Gmail MCP)가 이 출력을
읽어 Gmail 초안을 자동으로 생성합니다.

환경변수:
  YOUTUBE_API_KEY  — YouTube Data API 키 (필수)
  BRIEFING_TO      — 수신 이메일 주소 (선택, 기본값: 발신자 본인)
"""

import os
import json
import sys

from youtube_briefing import run as generate_briefing

RECIPIENT = os.environ.get("BRIEFING_TO", "")


def main() -> dict:
    demo = not os.environ.get("YOUTUBE_API_KEY")
    print("[1/2] YouTube API로 브리핑 생성 중…", file=sys.stderr)
    subject, html, text = generate_briefing(demo=demo)
    print("[2/2] 브리핑 생성 완료.", file=sys.stderr)

    result = {
        "subject": subject,
        "html": html,
        "text": text,
        "to": RECIPIENT,
    }
    # stdout에 JSON 출력 → Claude Code가 파싱해 Gmail MCP로 전송
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
