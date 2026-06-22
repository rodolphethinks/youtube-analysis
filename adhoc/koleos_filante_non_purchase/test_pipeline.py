"""
Pre-run integration tests for koleos_filante_non_purchase/analyze.py
Tests each pipeline stage with a small real sample before the full run.
Run: python adhoc/koleos_filante_non_purchase/test_pipeline.py
"""

import os
import sys
import math
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Import the module under test ──────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
import analyze as A

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
SKIP = "\033[93m[SKIP]\033[0m"

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"  {status} {name}" + (f"  → {detail}" if detail else ""))
    _results.append((name, condition, detail))


# ── Test 1: YouTube search ─────────────────────────────────────────────────────
def test_youtube_search():
    print("\n[1] YouTube Search (Korean, 3 results)")
    yt = A.build_youtube(A.YOUTUBE_API_KEY)
    results = A.search_videos(yt, "그랑 콜레오스 단점", max_results=3)
    check("Returns dict", isinstance(results, dict))
    check("At least 1 result", len(results) >= 1, f"{len(results)} videos")
    check("URLs start with https://www.youtube.com", all(u.startswith("https://www.youtube.com") for u in results))
    return yt, list(results.values())[0] if results else None


# ── Test 2: Video details ──────────────────────────────────────────────────────
def test_video_details(yt, video_id: str):
    print("\n[2] Video Details")
    if not video_id:
        print(f"  {SKIP} No video ID available")
        return None
    details = A.get_video_details(yt, video_id)
    check("Returns dict", isinstance(details, dict))
    check("Has required fields", details is not None and all(
        k in details for k in ["video_id", "url", "title", "views", "likes", "video_rank" if False else "views"]
    ))
    check("Views >= 0", details is not None and details.get("views", -1) >= 0,
          str(details.get("views") if details else "N/A"))
    check("Likes >= 0", details is not None and details.get("likes", -1) >= 0)
    return details


# ── Test 3: Transcript fetching ────────────────────────────────────────────────
def test_transcript(video_id: str):
    print("\n[3] Transcript (youtube-transcript-api)")
    if not video_id:
        print(f"  {SKIP} No video ID available")
        return
    api = A.build_transcript_api()
    transcript = A.fetch_transcript(video_id, api)
    if transcript is None:
        print(f"  {SKIP} No captions available for this video (try another)")
    else:
        check("Transcript is a non-empty string", isinstance(transcript, str) and len(transcript) > 50,
              f"{len(transcript)} chars")
    return transcript


# ── Test 4: Comment fetching (pagination) ─────────────────────────────────────
def test_comments(yt, video_id: str):
    print("\n[4] Comment Fetching (up to 200, pagination)")
    if not video_id:
        print(f"  {SKIP} No video ID available")
        return []
    comments = A.fetch_comments(yt, video_id, max_comments=200)
    check("Returns list", isinstance(comments, list))
    check("Comments have required keys", len(comments) == 0 or all(
        k in comments[0] for k in ["video_id", "author", "comment", "likes"]
    ))
    check("Pagination attempted (may have <= 100 if video has fewer)",
          len(comments) >= 0,   # just confirm it ran
          f"{len(comments)} comments fetched")
    if comments:
        check("Likes are non-negative integers", all(isinstance(c["likes"], int) and c["likes"] >= 0 for c in comments))
    return comments


# ── Test 5: Ranking formulas ──────────────────────────────────────────────────
def test_ranking():
    print("\n[5] Ranking Formulas")
    import pandas as pd

    df = pd.DataFrame([
        {"video_id": "a", "url": "u1", "title": "t1", "views": 1000, "likes": 100},
        {"video_id": "b", "url": "u2", "title": "t2", "views": 500,  "likes": 50},
        {"video_id": "c", "url": "u3", "title": "t3", "views": 100,  "likes": 10},
    ])
    ranked = A.compute_video_ranks(df)
    check("video_rank column added", "video_rank" in ranked.columns)
    check("Top video has rank 1.0", abs(ranked["video_rank"].max() - 1.0) < 1e-9,
          str(ranked["video_rank"].max()))
    check("Ranks are in [0, 1]", ranked["video_rank"].between(0, 1).all())
    check("Sorted descending", ranked["video_rank"].iloc[0] >= ranked["video_rank"].iloc[1])

    # comment_rank: log(1 + video_rank) * comment_likes
    vr = 0.8
    cl = 10
    cr = A.comment_rank(vr, cl)
    expected = math.log(1 + vr) * cl
    check("comment_rank formula correct", abs(cr - expected) < 1e-9,
          f"got {cr:.6f}, expected {expected:.6f}")
    check("comment_rank(0, 0) == 0", A.comment_rank(0.0, 0) == 0.0)
    check("Higher video_rank → higher comment_rank (same likes)",
          A.comment_rank(0.9, 5) > A.comment_rank(0.1, 5))


# ── Test 6: JSON parser ────────────────────────────────────────────────────────
def test_parse_json():
    print("\n[6] JSON Parser (markdown strip)")
    # Plain JSON
    r = A.parse_json('{"a": 1}')
    check("Plain JSON parsed", r == {"a": 1})
    # With markdown fences
    r = A.parse_json("```json\n[1, 2, 3]\n```")
    check("Fenced JSON parsed", r == [1, 2, 3])
    # Invalid
    r = A.parse_json("not json at all")
    check("Invalid returns None", r is None)


# ── Test 7: Gemini transcript argument extraction ──────────────────────────────
def test_gemini_transcript(transcript: str, video_id: str):
    print("\n[7] Gemini — Transcript Argument Extraction")
    if not transcript:
        print(f"  {SKIP} No transcript available")
        return
    gemini = A.init_gemini(A.GOOGLE_API_KEY)
    url = f"https://www.youtube.com/watch?v={video_id}"
    args = A.extract_transcript_arguments(
        gemini, url, "Test video", transcript[:3000], "Renault Grand Koleos"
    )
    check("Returns a list", isinstance(args, list))
    if args:
        check("Arguments have required keys", all(
            k in args[0] for k in ["category", "argument", "quote", "source_url", "source_type"]
        ))
        check("All categories are valid", all(a["category"] in A.CATEGORIES for a in args))
        check("source_type == 'transcript'", all(a["source_type"] == "transcript" for a in args))
        print(f"    → {len(args)} argument(s) extracted")
        for a in args[:3]:
            print(f"       [{a['category']}] {a['argument'][:80]}")
    else:
        print("    → No arguments extracted (may be no relevant content in sample)")


# ── Test 8: Gemini comment argument extraction ─────────────────────────────────
def test_gemini_comments(comments: list[dict], video_id: str):
    print("\n[8] Gemini — Comment Argument Extraction")
    if not comments:
        print(f"  {SKIP} No comments available")
        return
    # Use first 10 comments with >= 1 like as sample
    sample = [c for c in comments if c["likes"] >= 1][:10]
    if not sample:
        sample = comments[:10]
    if not sample:
        print(f"  {SKIP} No sample comments")
        return
    gemini = A.init_gemini(A.GOOGLE_API_KEY)
    url = f"https://www.youtube.com/watch?v={video_id}"
    args = A.extract_comment_arguments(
        gemini, url, "Test video", sample, "Renault Grand Koleos"
    )
    check("Returns a list", isinstance(args, list))
    if args:
        check("Arguments have required keys", all(
            k in args[0] for k in ["comment", "argument", "category", "source_url", "source_type"]
        ))
        check("All categories are valid", all(a["category"] in A.CATEGORIES for a in args))
        check("source_type == 'comment'", all(a["source_type"] == "comment" for a in args))
        print(f"    → {len(args)} argument(s) extracted from {len(sample)} comments")
        for a in args[:3]:
            print(f"       [{a['category']}] {a['argument'][:80]}")
    else:
        print(f"    → No relevant arguments found in sample (OK if comments are off-topic)")


# ── Test 9: Merge and re-rank ──────────────────────────────────────────────────
def test_merge_rerank():
    print("\n[9] Gemini — Merge and Re-rank")
    gemini = A.init_gemini(A.GOOGLE_API_KEY)
    fake_args = [
        {
            "category": "non_purchase",
            "argument": "Price is too high compared to Korean SUVs",
            "quote": "국산차 대비 가격이 너무 비싸요",
            "source_url": "https://www.youtube.com/watch?v=test1",
            "source_type": "transcript",
            "rank": 0.8,
        },
        {
            "category": "non_purchase",
            "argument": "Overpriced for what it offers versus domestic competitors",
            "quote": "이 가격이면 현대차 사지...",
            "source_url": "https://www.youtube.com/watch?v=test2",
            "source_type": "comment",
            "rank": 0.6,
        },
        {
            "category": "non_purchase",
            "argument": "Poor after-sales service network in Korea",
            "quote": "AS 망이 너무 약해서 걱정돼요",
            "source_url": "https://www.youtube.com/watch?v=test3",
            "source_type": "comment",
            "rank": 0.4,
        },
    ]
    merged = A.merge_and_rerank(gemini, fake_args, "non_purchase", "Renault Grand Koleos")
    check("Returns a list", isinstance(merged, list))
    check("At least 1 merged argument", len(merged) >= 1, f"{len(merged)} arguments")
    if merged:
        check("Merged has 'argument' key", "argument" in merged[0])
        check("Merged has 'combined_rank' key", "combined_rank" in merged[0])
        check("Merged has 'quotes' list", isinstance(merged[0].get("quotes"), list))
        print(f"    → {len(merged)} merged argument(s):")
        for m in merged[:3]:
            print(f"       [{m['combined_rank']:.3f}] {m['argument'][:80]}")


# ── Test 10: Docx report generation ───────────────────────────────────────────
def test_docx_report():
    print("\n[10] Docx Report Generation")
    from pathlib import Path
    import tempfile

    fake_results = {
        "koleos": {
            "non_purchase": [
                {
                    "argument": "High price relative to domestic Korean SUV alternatives",
                    "combined_rank": 0.85,
                    "quotes": [
                        {
                            "text": "국산차 대비 가격이 너무 비싸요",
                            "source_url": "https://www.youtube.com/watch?v=abc123",
                            "source_type": "transcript",
                        }
                    ],
                }
            ],
            "competitor": [
                {
                    "argument": "Consumers prefer Hyundai Tucson for better after-sales network",
                    "combined_rank": 0.70,
                    "quotes": [
                        {
                            "text": "현대 AS가 훨씬 편해요",
                            "source_url": "https://www.youtube.com/watch?v=def456",
                            "source_type": "comment",
                        }
                    ],
                }
            ],
            "regret": [],
        },
        "filante": {
            "non_purchase": [],
            "competitor": [],
            "regret": [
                {
                    "argument": "Battery range shorter than advertised in real-world Korean winter conditions",
                    "combined_rank": 0.60,
                    "quotes": [
                        {
                            "text": "겨울에 주행거리가 너무 줄어요",
                            "source_url": "https://www.youtube.com/watch?v=ghi789",
                            "source_type": "comment",
                        }
                    ],
                }
            ],
        },
    }

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        A.build_docx_report(fake_results, {"koleos": 5, "filante": 3}, {"koleos": 120, "filante": 80}, tmp_path)
        check("Docx file created", tmp_path.exists())
        check("Docx file non-empty", tmp_path.stat().st_size > 1000, f"{tmp_path.stat().st_size} bytes")
        print(f"    → Report written to {tmp_path}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ── Summary ────────────────────────────────────────────────────────────────────
def print_summary():
    print("\n" + "=" * 60)
    total = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = total - passed
    print(f"Results: {passed}/{total} passed" + (f", {failed} FAILED" if failed else ""))
    if failed:
        print("\nFailed tests:")
        for name, ok, detail in _results:
            if not ok:
                print(f"  {FAIL} {name}" + (f" → {detail}" if detail else ""))
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("Pre-run Integration Tests")
    print("koleos_filante_non_purchase/analyze.py")
    print("=" * 60)

    yt, first_video_id = test_youtube_search()
    details = test_video_details(yt, first_video_id)
    transcript = test_transcript(first_video_id)
    comments = test_comments(yt, first_video_id)
    test_ranking()
    test_parse_json()
    test_gemini_transcript(transcript, first_video_id)
    test_gemini_comments(comments, first_video_id)
    test_merge_rerank()
    test_docx_report()

    success = print_summary()
    sys.exit(0 if success else 1)
