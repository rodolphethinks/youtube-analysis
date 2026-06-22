"""
Standalone merge-only runner for koleos_filante_non_purchase.

Reads the already-saved raw argument CSVs and re-runs only:
  - Step 5: merge_and_rerank (chunked, structured Gemini output)
  - Step 6: build_docx_report

This avoids re-doing the ~45-minute YouTube collection + extraction steps.

Usage:
    python adhoc/koleos_filante_non_purchase/rerun_merge.py
"""

import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))
import analyze as A

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(A.OUTPUT_DIR / "rerun_merge.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def load_raw_arguments(car_key: str) -> dict[str, list[dict]]:
    """Load {category: [arg_dict, ...]} from the saved CSV."""
    csv_path = A.OUTPUT_DIR / f"{car_key}_raw_arguments.csv"
    if not csv_path.exists():
        log.error(f"Missing: {csv_path}")
        return {c: [] for c in A.CATEGORIES}

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    log.info(f"Loaded {len(df)} raw arguments from {csv_path.name}")

    result: dict[str, list[dict]] = {c: [] for c in A.CATEGORIES}
    for _, row in df.iterrows():
        cat = row.get("category", "")
        if cat in A.CATEGORIES:
            result[cat].append(row.to_dict())

    for cat in A.CATEGORIES:
        log.info(f"  {car_key}/{cat}: {len(result[cat])} args")

    return result


def run_merge_for_car(
    client,
    car_key: str,
    car_name: str,
) -> dict[str, list]:
    raw_arguments = load_raw_arguments(car_key)

    log.info(f"\nMerging arguments for {car_name}...")
    merged_results: dict[str, list] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(A.merge_and_rerank, client, raw_arguments[cat], cat, car_name): cat
            for cat in A.CATEGORIES
            if raw_arguments[cat]
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

    return merged_results


def main() -> None:
    log.info("=" * 60)
    log.info("Merge-only rerun")
    log.info("=" * 60)

    client = A.init_gemini(A.GOOGLE_API_KEY)

    # Load video/comment counts for report header (best-effort)
    video_counts: dict[str, int] = {}
    comment_counts: dict[str, int] = {}
    for car_key in A.CAR_NAMES:
        vid_csv = A.OUTPUT_DIR / f"{car_key}_videos.csv"
        if vid_csv.exists():
            video_counts[car_key] = len(pd.read_csv(vid_csv, encoding="utf-8-sig"))
        else:
            video_counts[car_key] = 0

        comment_csv = A.OUTPUT_DIR / f"{car_key}_comments.csv"
        if comment_csv.exists():
            comment_counts[car_key] = len(pd.read_csv(comment_csv, encoding="utf-8-sig"))
        else:
            comment_counts[car_key] = 0

    results_per_car: dict[str, dict[str, list]] = {}

    for car_key, car_name in A.CAR_NAMES.items():
        results_per_car[car_key] = run_merge_for_car(client, car_key, car_name)

    log.info("\nGenerating .docx report...")
    output_path = A.OUTPUT_DIR / "koleos_filante_non_purchase_analysis.docx"
    A.build_docx_report(results_per_car, video_counts, comment_counts, output_path)
    log.info(f"Done. Report: {output_path}")


if __name__ == "__main__":
    main()
