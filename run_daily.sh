#!/usr/bin/env bash
# 매일 아침 유튜브 트렌드 브리핑 실행 스크립트
# 크론 등록 예시 (매일 오전 8시):
#   0 8 * * * /path/to/claude-info/run_daily.sh >> /var/log/youtube_briefing.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 가상환경이 있으면 활성화
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

# 필수 환경변수 확인
: "${YOUTUBE_API_KEY:?YOUTUBE_API_KEY 환경변수를 설정하세요}"
: "${BRIEFING_TO:?BRIEFING_TO 환경변수에 수신 이메일을 설정하세요}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 시작"
python3 send_briefing.py
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 브리핑 완료"
