#!/usr/bin/env python3
"""
매일 아침 YouTube 트렌드 브리핑 생성기
키워드별 최근 24시간 인기 영상을 분석하여 Gmail로 발송합니다.
"""

import os
import re
import sys
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
KEYWORDS = ["클로드 코드"]

MAX_RESULTS = 50      # API에서 가져올 후보 수 (상위 5개 선별 위해 여유있게)
TOP_N = 5             # 키워드별 최종 노출 영상 수


def get_api_key() -> str:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise EnvironmentError("환경변수 YOUTUBE_API_KEY가 설정되지 않았습니다.")
    return api_key


def youtube_get(endpoint: str, params: dict) -> dict:
    """YouTube Data API GET 요청 (표준 라이브러리만 사용)"""
    url = f"{YOUTUBE_API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode())


def search_recent_videos(api_key: str, keyword: str) -> list[dict]:
    """최근 24시간 내 업로드된 영상 검색"""
    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        search_data = youtube_get("search", {
            "key": api_key,
            "q": keyword,
            "part": "id,snippet",
            "type": "video",
            "publishedAfter": published_after,
            "maxResults": MAX_RESULTS,
            "order": "relevance",
            "relevanceLanguage": "ko",
        })
    except Exception as e:
        print(f"[오류] '{keyword}' 검색 실패: {e}", file=sys.stderr)
        return []

    video_ids = [
        item["id"]["videoId"]
        for item in search_data.get("items", [])
        if item.get("id", {}).get("kind") == "youtube#video"
    ]
    if not video_ids:
        return []

    # 조회수 등 상세 통계 조회
    try:
        stats_data = youtube_get("videos", {
            "key": api_key,
            "part": "snippet,statistics",
            "id": ",".join(video_ids),
        })
    except Exception as e:
        print(f"[오류] 통계 조회 실패: {e}", file=sys.stderr)
        return []

    videos = []
    for item in stats_data.get("items", []):
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        videos.append({
            "id": item["id"],
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "published_at": snippet["publishedAt"],
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
        })

    # 조회수 기준 내림차순 정렬 후 상위 N개
    videos.sort(key=lambda v: v["view_count"], reverse=True)
    return videos[:TOP_N]


def analyze_title_patterns(videos: list[dict]) -> dict:
    """제목 패턴 분석"""
    patterns = {
        "숫자 포함": [],
        "질문형 (?)": [],
        "비교형 (vs/대)": [],
        "방법/하는법": [],
        "순위/TOP": [],
        "기타": [],
    }

    for v in videos:
        title = v["title"]
        matched = False

        if re.search(r"\d+", title):
            patterns["숫자 포함"].append(title)
            matched = True
        if re.search(r"[?？]", title):
            patterns["질문형 (?)"].append(title)
            matched = True
        if re.search(r"\bvs\b|vs\.| 대 ", title, re.IGNORECASE):
            patterns["비교형 (vs/대)"].append(title)
            matched = True
        if re.search(r"방법|하는법|하는 법|하는 방법|how to", title, re.IGNORECASE):
            patterns["방법/하는법"].append(title)
            matched = True
        if re.search(r"순위|top\s*\d+|best\s*\d+|ranking", title, re.IGNORECASE):
            patterns["순위/TOP"].append(title)
            matched = True
        if not matched:
            patterns["기타"].append(title)

    return {k: v for k, v in patterns.items() if v}


def extract_key_points(keyword: str, videos: list[dict], patterns: dict) -> list[str]:
    """채널 참고용 핵심 포인트 3가지 도출"""
    points = []

    # 포인트 1: 가장 강한 제목 패턴
    if patterns:
        top_pattern = max(patterns, key=lambda k: len(patterns[k]))
        count = len(patterns[top_pattern])
        points.append(
            f"제목 패턴 — '{top_pattern}' 유형이 {count}개로 가장 많음. "
            f"숫자·질문을 제목에 활용하면 클릭율 향상에 유리합니다."
        )
    else:
        points.append("분석할 영상이 부족하여 제목 패턴을 도출하지 못했습니다.")

    # 포인트 2: 상위 채널 특성
    if videos:
        top_channel = videos[0]["channel"]
        top_views = videos[0]["view_count"]
        points.append(
            f"채널 벤치마크 — 1위 채널 '{top_channel}'이 "
            f"{top_views:,}회 조회를 기록. 해당 채널의 썸네일·구성을 참고하세요."
        )
    else:
        points.append(f"'{keyword}' 키워드로 최근 24시간 내 영상이 없습니다.")

    # 포인트 3: 콘텐츠 기회
    gap_hint = (
        "24시간 내 업로드된 영상이 적다면 선점 기회입니다. "
        "경쟁이 낮을 때 빠르게 업로드하면 검색 노출 우위를 가져갈 수 있습니다."
        if len(videos) < 3
        else
        "경쟁 영상이 다수 존재합니다. 차별화된 앵글(심층 튜토리얼, 실사용 후기 등)로 "
        "기존 영상과 다른 가치를 제공하는 콘텐츠 기획을 추천합니다."
    )
    points.append(f"콘텐츠 기회 — {gap_hint}")

    return points


def build_report(results: dict) -> str:
    """최종 브리핑 텍스트 생성"""
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst).strftime("%Y년 %m월 %d일 %H:%M KST")

    lines = [
        "=" * 60,
        f"  YouTube 트렌드 브리핑 — {now_kst}",
        "=" * 60,
        "",
    ]

    for keyword, data in results.items():
        videos = data["videos"]
        patterns = data["patterns"]
        key_points = data["key_points"]

        lines.append(f"■ 키워드: [{keyword}]")
        lines.append(f"  (최근 24시간 업로드, 조회수 기준 상위 {TOP_N}개)")
        lines.append("")

        if not videos:
            lines.append("  ⚠ 검색 결과 없음")
            lines.append("")
            continue

        lines.append("  ── 상위 영상 ──────────────────────────────")
        for i, v in enumerate(videos, 1):
            lines.append(f"  {i}. {v['title']}")
            lines.append(f"     채널: {v['channel']}  |  조회수: {v['view_count']:,}회")
            lines.append(f"     URL : {v['url']}")
        lines.append("")

        lines.append("  ── 제목 패턴 분석 ─────────────────────────")
        for pattern, titles in patterns.items():
            lines.append(f"  [{pattern}] {len(titles)}개")
            for t in titles:
                lines.append(f"    · {t}")
        lines.append("")

        lines.append("  ── 채널 참고 핵심 포인트 ──────────────────")
        for j, pt in enumerate(key_points, 1):
            lines.append(f"  {j}. {pt}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    lines.append("※ 본 브리핑은 자동 생성된 정보입니다.")
    return "\n".join(lines)


def _demo_videos(keyword: str) -> list[dict]:
    """YOUTUBE_API_KEY 없이 구조 검증용 샘플 데이터"""
    return [
        {
            "id": "dQw4w9WgXcQ",
            "title": f"클로드 코드 완전 정복! 5가지 핵심 기능 총정리 (2026 최신)",
            "channel": "AI 개발연구소",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            "view_count": 48200,
            "like_count": 2100,
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        },
        {
            "id": "abc123xyz",
            "title": f"클로드 코드 vs ChatGPT — 실제 코딩 대결 결과는?",
            "channel": "테크 인사이트",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat(),
            "view_count": 31500,
            "like_count": 1450,
            "url": "https://www.youtube.com/watch?v=abc123xyz",
        },
        {
            "id": "def456uvw",
            "title": f"개발자라면 꼭 써봐야 할 클로드 코드 사용법 3단계",
            "channel": "개발하는 민준",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=11)).isoformat(),
            "view_count": 19800,
            "like_count": 870,
            "url": "https://www.youtube.com/watch?v=def456uvw",
        },
        {
            "id": "ghi789rst",
            "title": f"클로드 코드로 앱 만들기 가능할까? 직접 해봤습니다",
            "channel": "노코드 스튜디오",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=15)).isoformat(),
            "view_count": 12300,
            "like_count": 540,
            "url": "https://www.youtube.com/watch?v=ghi789rst",
        },
        {
            "id": "jkl012mno",
            "title": f"클로드 코드 무료로 쓰는 방법 | 완벽 가이드",
            "channel": "AI 툴 리뷰",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=20)).isoformat(),
            "view_count": 8900,
            "like_count": 390,
            "url": "https://www.youtube.com/watch?v=jkl012mno",
        },
    ]


def run(demo: bool = False):
    print("YouTube 트렌드 브리핑 시작...\n")

    if demo:
        print("  ※ 데모 모드: YOUTUBE_API_KEY 없이 샘플 데이터로 실행\n")
    else:
        api_key = get_api_key()

    results = {}
    for keyword in KEYWORDS:
        print(f"  [{keyword}] 검색 중...")
        if demo:
            videos = _demo_videos(keyword)
        else:
            videos = search_recent_videos(api_key, keyword)
        patterns = analyze_title_patterns(videos)
        key_points = extract_key_points(keyword, videos, patterns)
        results[keyword] = {
            "videos": videos,
            "patterns": patterns,
            "key_points": key_points,
        }
        print(f"  → {len(videos)}개 영상 수집 완료")

    report = build_report(results)
    print("\n" + report)

    # JSON 형태로도 저장 (자동화 파이프라인 연동용)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "briefing_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "demo": demo,
                "report_text": report,
                "data": {
                    kw: {
                        "videos": v["videos"],
                        "patterns": v["patterns"],
                        "key_points": v["key_points"],
                    }
                    for kw, v in results.items()
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n결과 저장 완료: {output_path}")
    return report, results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YouTube 트렌드 브리핑 생성기")
    parser.add_argument("--demo", action="store_true", help="샘플 데이터로 실행 (API 키 불필요)")
    args = parser.parse_args()
    run(demo=args.demo)
