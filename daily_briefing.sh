#!/usr/bin/env bash
# 매일 아침 YouTube 트렌드 브리핑을 생성하고 Gmail로 전송합니다.
#
# crontab 등록 예시 (매일 오전 8시):
#   0 8 * * * /home/user/claude-info/daily_briefing.sh >> /home/user/claude-info/briefing.log 2>&1
#
# 필수 환경변수:
#   YOUTUBE_API_KEY — YouTube Data API 키
#   BRIEFING_TO     — 수신 이메일 (OAuth 전송 시)
#
# 선택 환경변수:
#   BRIEFING_MODE   — "oauth" (기본) | "mcp" (briefing_result.json 저장)
#   BRIEFING_MOCK   — "1" 이면 샘플 데이터 사용 (API 키 불필요)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${BRIEFING_MODE:-oauth}"
MOCK_FLAG=""
[ "${BRIEFING_MOCK:-0}" = "1" ] && MOCK_FLAG="--mock"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 시작 (mode=$MODE)"

if [ "$MODE" = "mcp" ]; then
    python3 send_briefing.py $MOCK_FLAG --mcp
else
    python3 send_briefing.py $MOCK_FLAG
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 완료"
