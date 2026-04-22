#!/usr/bin/env python3
"""YouTube Trend Briefing Generator — 매일 아침 키워드별 트렌드 브리핑"""

import os
import re
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

KEYWORDS = ["클로드 코드"]
TOP_N = 5


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
) -> str:
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
<h2 style="color:#c00">📊 YouTube 트렌드 브리핑 — {generated_at}</h2>
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


DEMO_VIDEOS: list[dict] = [
    {"video_id": "demo1", "title": "클로드 코드 완전 정복! 5가지 핵심 기능 총정리 (2026 최신)", "channel": "AI 마스터", "views": 48200},
    {"video_id": "demo2", "title": "클로드 코드 vs GPT-4o 코딩 대결 — 누가 더 빠를까?", "channel": "개발자의 하루", "views": 31500},
    {"video_id": "demo3", "title": "클로드 코드로 풀스택 앱 만드는 방법 (처음부터 끝까지)", "channel": "코딩스튜디오", "views": 22800},
    {"video_id": "demo4", "title": "Claude Code 솔직 리뷰 — 6개월 써본 현직 개발자 후기", "channel": "프로개발자K", "views": 17900},
    {"video_id": "demo5", "title": "클로드 코드 무료로 쓰는 3가지 방법 2026년 버전", "channel": "절약왕테크", "views": 14300},
]


def run(demo: bool = False) -> tuple[str, str, str]:
    if not YOUTUBE_API_KEY and not demo:
        print("[!] YOUTUBE_API_KEY 미설정 → 데모 모드로 실행합니다.", file=sys.stderr)
        demo = True

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    briefing_html = ""
    briefing_text = ""

    for keyword in KEYWORDS:
        if demo:
            print(f"[*] '{keyword}' 데모 데이터 사용 중…")
            top = DEMO_VIDEOS
        else:
            print(f"[*] '{keyword}' 검색 중…")
            raw = search_videos(keyword)
            top = enrich_and_rank(raw)
            print(f"    → {len(top)}개 영상 수집 완료")

        titles = [v["title"] for v in top]
        patterns = analyze_patterns(titles)
        key_points = derive_key_points(top, patterns)

        demo_banner = (
            "<p style='background:#fff3cd;padding:8px;border-left:4px solid #ffc107'>"
            "⚠️ <b>데모 실행</b> — YOUTUBE_API_KEY 설정 후 실제 데이터로 대체됩니다</p>"
            if demo else ""
        )
        briefing_html += demo_banner + build_html(keyword, top, patterns, key_points, now)
        briefing_text += (
            ("⚠️ 데모 실행 — YOUTUBE_API_KEY 설정 후 실제 데이터로 대체됩니다\n\n" if demo else "")
            + build_text(keyword, top, patterns, key_points, now)
            + "\n\n"
        )

    subject = f"[YouTube 트렌드 브리핑] 클로드 코드 — {datetime.now().strftime('%Y년 %m월 %d일')}"
    return subject, briefing_html, briefing_text


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube 트렌드 브리핑 생성")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    args = parser.parse_args()

    subject, html, text = run()

    if args.json:
        print(json.dumps({"subject": subject, "html": html, "text": text}, ensure_ascii=False))
    else:
        print("\n" + "=" * 60)
        print(text)
        print("=" * 60)
        print("\n✅ 브리핑 생성 완료. send_briefing.py를 실행하면 Gmail 초안이 생성됩니다.")
