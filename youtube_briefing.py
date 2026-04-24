#!/usr/bin/env python3
"""YouTube Trend Briefing Generator — 매일 아침 키워드별 트렌드 브리핑

사용법:
  python youtube_briefing.py             # 실제 YouTube API 호출
  python youtube_briefing.py --mock      # API 키 없이 샘플 데이터로 테스트
  python youtube_briefing.py --save      # briefing_result.json 저장
  python youtube_briefing.py --mock --save
"""

import os
import re
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta, timezone

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

KEYWORDS = ["클로드 코드"]
TOP_N = 5

# --mock 모드에서 사용할 샘플 데이터
MOCK_DATA: dict[str, list[dict]] = {
    "클로드 코드": [
        {"video_id": "mock1", "title": "클로드 코드 완벽 사용법 — 5가지 핵심 기능", "channel": "AI 튜토리얼 채널", "published_at": "", "views": 15420},
        {"video_id": "mock2", "title": "Claude Code vs Cursor: 어떤 AI 코딩 도구가 더 좋을까?", "channel": "개발자 인사이트", "published_at": "", "views": 9870},
        {"video_id": "mock3", "title": "클로드 코드로 30분 만에 풀스택 앱 만들기", "channel": "빠른 개발 연구소", "published_at": "", "views": 7340},
        {"video_id": "mock4", "title": "Claude Code 무료 vs 유료 — 솔직 후기·장단점 비교", "channel": "테크 리뷰 코리아", "published_at": "", "views": 6210},
        {"video_id": "mock5", "title": "클로드 코드 설치·설정 완전 정복 (2025 최신)", "channel": "코딩 왕초보 탈출", "published_at": "", "views": 4980},
    ]
}


def search_videos(keyword: str, max_results: int = 10) -> list[dict]:
    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "publishedAfter": published_after,
        "maxResults": max_results,
        "order": "relevance",
        "key": YOUTUBE_API_KEY,
    }
    resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        {
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
        }
        for item in items
        if item.get("id", {}).get("videoId")
    ]


def fetch_stats(video_ids: list[str]) -> dict[str, dict]:
    params = {
        "part": "statistics",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }
    resp = requests.get(YOUTUBE_VIDEOS_URL, params=params, timeout=15)
    resp.raise_for_status()
    return {
        item["id"]: item.get("statistics", {})
        for item in resp.json().get("items", [])
    }


def enrich_and_rank(videos: list[dict]) -> list[dict]:
    if not videos:
        return []
    stats = fetch_stats([v["video_id"] for v in videos])
    for v in videos:
        s = stats.get(v["video_id"], {})
        v["views"] = int(s.get("viewCount", 0))
    videos.sort(key=lambda v: v["views"], reverse=True)
    return videos[:TOP_N]


def analyze_patterns(titles: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        "숫자 포함": [],
        "질문형": [],
        "비교형 (vs/대비)": [],
        "방법·튜토리얼": [],
        "리뷰·분석": [],
        "기타": [],
    }
    for t in titles:
        tagged = False
        if re.search(r"\d+", t):
            buckets["숫자 포함"].append(t)
            tagged = True
        if re.search(r"[?？]|어떻게|무엇|왜|언제|어디|어느", t):
            buckets["질문형"].append(t)
            tagged = True
        if re.search(r"\bvs\b|VS|대비|비교|차이점", t, re.IGNORECASE):
            buckets["비교형 (vs/대비)"].append(t)
            tagged = True
        if re.search(r"방법|하는\s*법|사용법|튜토리얼|강좌|강의|설치|설정|세팅", t):
            buckets["방법·튜토리얼"].append(t)
            tagged = True
        if re.search(r"리뷰|후기|분석|솔직|장단점|평가|써봤", t):
            buckets["리뷰·분석"].append(t)
            tagged = True
        if not tagged:
            buckets["기타"].append(t)
    return {k: v for k, v in buckets.items() if v}


def derive_key_points(
    all_videos: list[dict], all_patterns: dict[str, list[str]]
) -> list[str]:
    points: list[str] = []

    top_pattern = max(all_patterns, key=lambda k: len(all_patterns[k]), default=None)
    if top_pattern:
        count = len(all_patterns[top_pattern])
        points.append(
            f"**제목 패턴 — '{top_pattern}' 유형이 {count}건으로 가장 많습니다.** "
            "제목에 구체적인 숫자나 질문을 넣으면 클릭률이 높아지는 경향이 있으니 참고하세요."
        )

    if all_videos:
        top = all_videos[0]
        points.append(
            f"**최고 조회수 영상 분석 — '{top['title'][:40]}…' ({top['views']:,}회).** "
            "해당 영상의 썸네일·길이·게시 시간대를 참고하여 콘텐츠 기획에 활용하세요."
        )

    unique_channels = {v["channel"] for v in all_videos}
    if len(unique_channels) >= 3:
        points.append(
            f"**경쟁 채널 다양성 — {len(unique_channels)}개 채널이 동일 키워드를 다루고 있습니다.** "
            "차별화된 관점(심층 튜토리얼, 한국어 번역 해설 등)을 강조해 틈새를 공략하세요."
        )
    else:
        points.append(
            "**키워드 공백 발견 — 24시간 내 경쟁 영상이 적습니다.** "
            "지금 업로드하면 초기 노출 우위를 선점할 수 있습니다."
        )

    return points[:3]


def build_html(
    keyword: str,
    videos: list[dict],
    patterns: dict[str, list[str]],
    key_points: list[str],
    generated_at: str,
    is_mock: bool = False,
) -> str:
    mock_badge = (
        '<span style="background:#f90;color:#fff;padding:2px 8px;border-radius:4px;'
        'font-size:0.75em;margin-left:8px">샘플 데이터</span>'
        if is_mock else ""
    )
    rows = "".join(
        f"<tr><td>{i + 1}</td><td>{v['title']}</td>"
        f"<td>{v['channel']}</td><td>{v['views']:,}</td></tr>"
        for i, v in enumerate(videos)
    )
    pattern_rows = "".join(
        f"<tr><td><b>{p}</b></td><td>{len(vs)}건</td>"
        f"<td style='font-size:0.85em'>{' / '.join(vs[:2])}{'…' if len(vs) > 2 else ''}</td></tr>"
        for p, vs in patterns.items()
    )
    kp_items = "".join(f"<li style='margin-bottom:8px'>{kp}</li>" for kp in key_points)

    return f"""
<html><body style="font-family:sans-serif;max-width:700px;margin:auto;color:#222">
<h2 style="color:#c00">📊 YouTube 트렌드 브리핑 — {generated_at}{mock_badge}</h2>
<h3>키워드: <span style="color:#1a73e8">{keyword}</span></h3>

<h4>🎬 상위 {TOP_N}개 영상 (최근 24시간)</h4>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
  <thead style="background:#f5f5f5">
    <tr><th>#</th><th>제목</th><th>채널</th><th>조회수</th></tr>
  </thead>
  <tbody>{rows}</tbody>
</table>

<h4>🔍 제목 패턴 분석</h4>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
  <thead style="background:#f5f5f5">
    <tr><th>패턴</th><th>건수</th><th>예시</th></tr>
  </thead>
  <tbody>{pattern_rows}</tbody>
</table>

<h4>💡 우리 채널을 위한 핵심 포인트 3가지</h4>
<ol>{kp_items}</ol>

<hr style="margin-top:24px">
<p style="font-size:0.8em;color:#888">자동 생성 · YouTube Data API v3 · {generated_at}</p>
</body></html>
"""


def build_text(
    keyword: str,
    videos: list[dict],
    patterns: dict[str, list[str]],
    key_points: list[str],
    generated_at: str,
) -> str:
    lines = [
        f"YouTube 트렌드 브리핑 — {generated_at}",
        f"키워드: {keyword}",
        "",
        f"[상위 {TOP_N}개 영상]",
    ]
    for i, v in enumerate(videos, 1):
        lines.append(f"  {i}. {v['title']} | {v['channel']} | {v['views']:,}회")
    lines += ["", "[제목 패턴 분석]"]
    for p, vs in patterns.items():
        lines.append(f"  {p}: {len(vs)}건 — {', '.join(vs[:2])}")
    lines += ["", "[핵심 포인트]"]
    for idx, kp in enumerate(key_points, 1):
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", kp)
        lines.append(f"  {idx}. {clean}")
    return "\n".join(lines)


def run(mock: bool = False) -> tuple[str, str, str]:
    if not mock and not YOUTUBE_API_KEY:
        sys.exit("YOUTUBE_API_KEY 환경변수가 설정되지 않았습니다. 테스트하려면 --mock 플래그를 사용하세요.")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_videos: list[dict] = []
    briefing_html = ""
    briefing_text = ""

    for keyword in KEYWORDS:
        if mock:
            print(f"[*] '{keyword}' 샘플 데이터 사용 중…")
            top = MOCK_DATA.get(keyword, [])[:TOP_N]
        else:
            print(f"[*] '{keyword}' 검색 중…")
            raw = search_videos(keyword)
            top = enrich_and_rank(raw)

        titles = [v["title"] for v in top]
        patterns = analyze_patterns(titles)
        key_points = derive_key_points(top, patterns)
        all_videos.extend(top)

        briefing_html += build_html(keyword, top, patterns, key_points, now, is_mock=mock)
        briefing_text += build_text(keyword, top, patterns, key_points, now) + "\n\n"
        print(f"    → {len(top)}개 영상 수집 완료")

    subject = f"[YouTube 브리핑] 클로드 코드 트렌드 — {now}"
    return subject, briefing_html, briefing_text


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 트렌드 브리핑 생성기")
    parser.add_argument("--mock", action="store_true", help="API 키 없이 샘플 데이터로 실행")
    parser.add_argument("--save", action="store_true", help="briefing_result.json 파일로 저장")
    args = parser.parse_args()

    subject, html, text = run(mock=args.mock)

    if args.save:
        output = {"subject": subject, "html": html, "text": text}
        with open("briefing_result.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print("\n[저장] briefing_result.json 생성 완료")

    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)
    print("\n브리핑 생성 완료.")
    if not args.save:
        print("Gmail 전송: python send_briefing.py [--mock]")


if __name__ == "__main__":
    main()
