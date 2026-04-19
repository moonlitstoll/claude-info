#!/usr/bin/env python3
"""YouTube trend briefing generator for '클로드 코드' keyword."""

import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError

API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
KEYWORD = "클로드 코드"
MAX_RESULTS = 10  # fetch more, pick top 5 by view count


def youtube_search(keyword: str, published_after: str) -> list[dict]:
    params = urlencode({
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "order": "relevance",
        "publishedAfter": published_after,
        "maxResults": MAX_RESULTS,
        "key": API_KEY,
    })
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["items"]


def get_video_stats(video_ids: list[str]) -> dict[str, dict]:
    params = urlencode({
        "part": "statistics",
        "id": ",".join(video_ids),
        "key": API_KEY,
    })
    url = f"https://www.googleapis.com/youtube/v3/videos?{params}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=15) as resp:
        items = json.loads(resp.read())["items"]
    return {item["id"]: item["statistics"] for item in items}


def classify_title(title: str) -> list[str]:
    patterns = []
    if re.search(r"\d+", title):
        patterns.append("숫자 포함")
    if re.search(r"[?？]|방법|어떻게|무엇|이유|왜|뭐", title):
        patterns.append("질문형")
    if re.search(r"vs|비교|차이|대|vs\.|versus", title, re.IGNORECASE):
        patterns.append("비교형")
    if re.search(r"최고|최강|완벽|필수|꼭|반드시|무조건|최신|신기|놀라|충격|대박", title):
        patterns.append("감탄/강조형")
    if re.search(r"튜토리얼|강의|강좌|배우|사용법|입문|시작", title):
        patterns.append("튜토리얼형")
    if re.search(r"리뷰|후기|사용해|써봤|써본", title):
        patterns.append("리뷰형")
    if not patterns:
        patterns.append("일반형")
    return patterns


def generate_briefing(videos: list[dict]) -> str:
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y년 %m월 %d일")

    lines = [
        f"# 유튜브 트렌드 브리핑 — {today}",
        f"## 키워드: {KEYWORD}",
        "",
        "---",
        "## 상위 5개 영상",
        "",
    ]

    all_patterns: list[str] = []
    for i, v in enumerate(videos, 1):
        title = v["title"]
        channel = v["channel"]
        views = f"{int(v['views']):,}" if v["views"] != "N/A" else "N/A"
        published = v["published"][:10]
        patterns = classify_title(title)
        all_patterns.extend(patterns)

        lines += [
            f"### {i}. {title}",
            f"- **채널**: {channel}",
            f"- **조회수**: {views}",
            f"- **업로드**: {published}",
            f"- **제목 패턴**: {', '.join(patterns)}",
            "",
        ]

    # Pattern analysis
    from collections import Counter
    pattern_counts = Counter(all_patterns)
    lines += [
        "---",
        "## 제목 패턴 분석",
        "",
    ]
    for pattern, count in pattern_counts.most_common():
        lines.append(f"- **{pattern}**: {count}개 영상")

    # Key takeaways
    top_pattern = pattern_counts.most_common(1)[0][0] if pattern_counts else "일반형"
    has_numbers = pattern_counts.get("숫자 포함", 0) > 0
    has_questions = pattern_counts.get("질문형", 0) > 0
    has_tutorial = pattern_counts.get("튜토리얼형", 0) > 0

    takeaways = []
    takeaways.append(
        f"가장 많이 사용된 제목 패턴은 **{top_pattern}**입니다. 우리 채널도 이 패턴을 적극 활용하세요."
    )
    if has_numbers:
        takeaways.append(
            "숫자 포함 제목이 트렌드입니다 (예: 'Claude Code 5가지 핵심 기능'). 구체적 수치를 넣으면 클릭률이 높아집니다."
        )
    if has_questions:
        takeaways.append(
            "질문형 제목이 주목받고 있습니다. 시청자의 궁금증을 자극하는 형식으로 썸네일·제목을 구성하세요."
        )
    if has_tutorial:
        takeaways.append(
            "튜토리얼·사용법 콘텐츠 수요가 높습니다. 실습 위주의 단계별 가이드 영상을 제작하면 검색 유입에 유리합니다."
        )
    while len(takeaways) < 3:
        takeaways.append(
            "꾸준한 업로드와 키워드 최적화로 알고리즘 노출을 높이세요."
        )

    lines += [
        "",
        "---",
        "## 우리 채널 참고 핵심 포인트 3가지",
        "",
    ]
    for i, point in enumerate(takeaways[:3], 1):
        lines.append(f"{i}. {point}")

    lines += ["", f"*생성 시각: {datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')}*"]
    return "\n".join(lines)


def main():
    if not API_KEY:
        print("ERROR: YOUTUBE_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    # 24 hours ago in RFC 3339
    published_after = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    print(f"[*] '{KEYWORD}' 키워드로 최근 24시간 내 영상 검색 중...", file=sys.stderr)
    try:
        items = youtube_search(KEYWORD, published_after)
    except URLError as e:
        print(f"ERROR: YouTube API 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)

    if not items:
        print("검색 결과가 없습니다.", file=sys.stderr)
        sys.exit(0)

    video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]

    print(f"[*] {len(video_ids)}개 영상 통계 조회 중...", file=sys.stderr)
    try:
        stats = get_video_stats(video_ids)
    except URLError as e:
        print(f"ERROR: 영상 통계 조회 실패: {e}", file=sys.stderr)
        stats = {}

    # Build video list with view counts
    video_list = []
    for item in items:
        vid_id = item.get("id", {}).get("videoId")
        if not vid_id:
            continue
        snippet = item["snippet"]
        view_count = int(stats.get(vid_id, {}).get("viewCount", 0))
        video_list.append({
            "id": vid_id,
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "published": snippet["publishedAt"],
            "views": str(view_count) if view_count else "N/A",
            "view_count_int": view_count,
        })

    # Sort by view count descending, take top 5
    video_list.sort(key=lambda v: v["view_count_int"], reverse=True)
    top5 = video_list[:5]

    briefing = generate_briefing(top5)
    print(briefing)
    return briefing


if __name__ == "__main__":
    main()
