"""
Re-run transcript fetching + argument extraction, then merge with existing comment arguments.

Use this when:
- transcripts were mostly blocked before (no cookies)
- you now have cookies.txt and want to capture transcript data without redoing comments

Steps:
  1. Read {car}_videos.csv  → video list with ranks
  2. Re-fetch transcripts   → now authenticated via cookies.txt
  3. Gemini extraction      → transcript arguments (parallel)
  4. Load existing comment arguments from {car}_raw_arguments.csv (source_type == "comment")
  5. Combine + save as new  {car}_raw_arguments.csv  (overwrites)
  6. Merge & re-rank        → step 5 of main pipeline
  7. Build .docx report     → overwrites existing report

Usage:
    python adhoc/koleos_filante_non_purchase/rerun_transcripts_and_merge.py
"""

import sys
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import analyze as A

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(A.OUTPUT_DIR / "rerun_transcripts.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def refetch_audio_arguments(
    client,
    car_key: str,
    car_name: str,
) -> list[dict]:
    """
    Load videos CSV, download audio sequentially, extract arguments via Gemini in parallel.
    Returns list of argument dicts (source_type == "audio").
    """
    import math, threading
    vid_csv = A.OUTPUT_DIR / f"{car_key}_videos.csv"
    if not vid_csv.exists():
        log.error(f"Missing: {vid_csv}")
        return []

    videos_df = pd.read_csv(vid_csv, encoding="utf-8-sig")
    total = len(videos_df)
    log.info(f"{car_name}: {total} videos — downloading audio sequentially then extracting")

    # Phase 1: sequential audio download
    audio_dir = A.OUTPUT_DIR / f"{car_key}_audio"
    audio_dir.mkdir(exist_ok=True)
    video_list = []
    for i, (_, row) in enumerate(videos_df.iterrows()):
        url = row["url"]
        result = A._download_audio(url, str(audio_dir))
        if result:
            audio_path, mime = result
            log.info(f"  [{i+1}/{total} ✓] {str(row['title'])[:65]}")
        else:
            audio_path, mime = "", "audio/mp4"
            log.info(f"  [{i+1}/{total} ✗] {str(row['title'])[:65]}")
        video_list.append({
            "url": url, "title": row["title"],
            "video_rank": float(row["video_rank"]),
            "audio_path": audio_path, "audio_mime": mime,
        })
        import time; time.sleep(A.AUDIO_DOWNLOAD_DELAY)

    # Phase 2: parallel Gemini extraction
    results: list[dict] = []
    _lock = threading.Lock()
    done = 0
    jobs = [v for v in video_list if v["audio_path"]]
    log.info(f"{car_name}: {len(jobs)}/{total} audio files ready — extracting with Gemini")

    with ThreadPoolExecutor(max_workers=A.GEMINI_WORKERS) as executor:
        futures = {
            executor.submit(
                A.extract_transcript_arguments,
                client, v["url"], v["title"], v["audio_path"], car_name, v["audio_mime"],
            ): v
            for v in jobs
        }
        for f in as_completed(futures):
            v = futures[f]
            try:
                args = f.result()
                for arg in args:
                    mc = arg.pop("mention_count", 1)
                    arg["rank"] = v["video_rank"] * math.log(1 + mc)
                with _lock:
                    results.extend(args)
                    done += 1
                    n = done
                counts = ", ".join(
                    f"{c}:{sum(1 for a in args if a['category']==c)}"
                    for c in A.CATEGORIES
                    if any(a['category']==c for a in args)
                )
                log.info(f"  [audio {n}/{len(jobs)}] {str(v['title'])[:55]} → {counts or 'no args'}")
            except Exception as e:
                log.warning(f"  Extraction error ({v['url']}): {e}")

    log.info(f"{car_name}: {len(results)} audio arguments extracted")
    return results


def load_comment_arguments(car_key: str) -> list[dict]:
    """Load only comment-sourced arguments from the existing raw_arguments CSV."""
    csv_path = A.OUTPUT_DIR / f"{car_key}_raw_arguments.csv"
    if not csv_path.exists():
        log.warning(f"No existing raw_arguments CSV for {car_key} — no comment args loaded")
        return []
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    comment_args = df[df["source_type"] == "comment"].to_dict("records")
    log.info(f"{car_key}: loaded {len(comment_args)} existing comment arguments")
    return comment_args


def main() -> None:
    log.info("=" * 60)
    log.info("Re-run: transcripts + merge")
    log.info("=" * 60)

    client = A.init_gemini(A.GOOGLE_API_KEY)

    # Load video counts for report header (comment counts are filled in per-car below,
    # once we know how many comment-sourced arguments were actually loaded/used).
    video_counts: dict[str, int] = {}
    comment_counts: dict[str, int] = {}
    for car_key in A.CAR_NAMES:
        vid_csv = A.OUTPUT_DIR / f"{car_key}_videos.csv"
        video_counts[car_key] = len(pd.read_csv(vid_csv, encoding="utf-8-sig")) if vid_csv.exists() else 0

    results_per_car: dict[str, dict[str, list]] = {}

    for car_key, car_name in A.CAR_NAMES.items():
        log.info(f"\n{'=' * 60}\n{car_name}\n{'=' * 60}")

        # Extract audio arguments for all videos, load existing comment arguments
        audio_args = refetch_audio_arguments(client, car_key, car_name)

        # Step 4: load existing comment arguments
        comment_args = load_comment_arguments(car_key)
        # Count distinct qualifying comments (one comment can yield >1 argument rows
        # across categories, so dedupe on the original comment text for an accurate count).
        comment_counts[car_key] = len({a.get("comment") for a in comment_args if a.get("comment")})

        # Combine and save
        all_args = audio_args + comment_args
        if all_args:
            pd.DataFrame(all_args).to_csv(
                A.OUTPUT_DIR / f"{car_key}_raw_arguments.csv", index=False, encoding="utf-8-sig"
            )
            log.info(f"Saved {len(all_args)} combined arguments to {car_key}_raw_arguments.csv")

        # Split by category for merge
        raw_by_cat: dict[str, list[dict]] = {c: [] for c in A.CATEGORIES}
        for arg in all_args:
            cat = arg.get("category", "")
            if cat in A.CATEGORIES:
                raw_by_cat[cat].append(arg)
        for cat in A.CATEGORIES:
            log.info(f"  {car_key}/{cat}: {len(raw_by_cat[cat])} args")

        # Step 5: merge
        log.info(f"Merging arguments for {car_name}...")
        merged_results: dict[str, list] = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(A.merge_and_rerank, client, raw_by_cat[cat], cat, car_name): cat
                for cat in A.CATEGORIES
                if raw_by_cat[cat]
            }
            for f in as_completed(futures):
                cat = futures[f]
                try:
                    merged = f.result()
                    merged_results[cat] = merged
                    log.info(f"  Merged — {cat}: {len(merged)} arguments")
                except Exception as e:
                    log.warning(f"  Merge error ({cat}): {e}")
                    merged_results[cat] = []

        for cat in A.CATEGORIES:
            if cat not in merged_results:
                merged_results[cat] = []

        results_per_car[car_key] = merged_results

    # Step 6: docx
    log.info("\nGenerating .docx report...")
    output_path = A.OUTPUT_DIR / "koleos_filante_non_purchase_analysis.docx"
    A.build_docx_report(results_per_car, video_counts, comment_counts, output_path)

    sources_path = A.OUTPUT_DIR / "koleos_filante_sources_deep_dive.csv"
    A.build_sources_csv(results_per_car, sources_path)

    log.info(f"Done. Report: {output_path}")


if __name__ == "__main__":
    main()
