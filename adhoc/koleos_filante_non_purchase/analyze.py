"""
Ad-hoc Analysis: Why Koreans Don't Buy the Grand Koleos or Filante
------------------------------------------------------------------
Objective:
  - Understand main reasons Korean consumers avoid the Grand Koleos or Filante
  - Understand why they prefer competitor cars instead
  - Understand post-purchase regret (kept in a separate section)

Approach:
  1. Multiple Korean YouTube search queries per car (regionCode=KR, relevanceLanguage=ko)
  2. Fetch video transcripts via youtube-transcript-api (Korean captions preferred)
  3. Fetch up to 200 comments per video; pre-filter to >=2 likes
  4. Rank each video: video_rank = 0.5*(likes/max_likes) + 0.5*(views/max_views)
  5. Rank each comment: comment_rank = log(1 + video_rank) * comment_likes
  6. Extract categorized arguments from transcripts (parallel Gemini calls per video)
  7. Extract categorized arguments from comments (parallel Gemini calls, 50 comments/batch)
  8. Merge & re-rank similar arguments per category via Gemini semantic clustering
  9. Output: structured .docx report + intermediate CSVs
"""

import os
import re
import sys
import json
import time
import math
import logging
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import re
import tempfile
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, Field
import yt_dlp
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Setup ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / "run.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")   # Gemini only
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "") or GOOGLE_API_KEY  # fallback for backwards compat
if not GOOGLE_API_KEY:
    raise EnvironmentError("GOOGLE_API_KEY is not set in .env")
if not YOUTUBE_API_KEY:
    raise EnvironmentError("YOUTUBE_API_KEY is not set in .env")

# ── Config ─────────────────────────────────────────────────────────────────────
COOKIES_PATH = ROOT / "cookies.txt"   # export from browser via "Get cookies.txt LOCALLY"
GEMINI_MODEL = "gemini-3.1-flash-lite"
MAX_COMMENTS = 200
MIN_COMMENT_LIKES = 2
COMMENT_BATCH_SIZE = 50
GEMINI_WORKERS = 5        # parallel Gemini threads
MAX_RESULTS_PER_QUERY = 25
GEMINI_RETRY_ATTEMPTS = 3

CAR_NAMES = {
    "koleos": "Renault Grand Koleos",
    "filante": "Renault Filante",
}

# Korean search queries per car — focused on non-purchase & competitor preference
SEARCH_QUERIES: dict[str, list[str]] = {
    "koleos": [
        "그랑 콜레오스 단점",               # Grand Koleos disadvantages
        "그랑 콜레오스 구매 안하는 이유",    # Reasons not to buy Grand Koleos
        "그랑 콜레오스 실망",               # Grand Koleos disappointment
        "그랑 콜레오스 후회",               # Grand Koleos regret
        "그랑 콜레오스 문제점",             # Grand Koleos problems
        "그랑 콜레오스 경쟁차 비교",         # Grand Koleos vs competitors
        "그랑 콜레오스 VS",                # Grand Koleos vs
        "르노 그랑 콜레오스 솔직 리뷰",      # Honest review
        "그랑 콜레오스 대신 추천",           # Recommended instead of Grand Koleos
        "그랑 콜레오스 비추",               # Do not recommend Grand Koleos
    ],
    "filante": [
        "필랑트 단점",                     # Filante disadvantages
        "필랑트 구매 안하는 이유",           # Reasons not to buy Filante
        "필랑트 후회",                     # Filante regret
        "필랑트 실망",                     # Filante disappointment
        "필랑트 문제점",                   # Filante problems
        "필랑트 VS",                       # Filante vs
        "르노 필랑트 솔직 리뷰",             # Honest Filante review
        "필랑트 대신 추천",                 # Recommended instead of Filante
        "필랑트 비추",                     # Do not recommend Filante
        "필랑트 경쟁차",                   # Filante competitors
    ],
}

CATEGORIES = ["non_purchase", "competitor", "regret"]
CATEGORY_LABELS = {
    "non_purchase": "Reasons Not to Buy",
    "competitor":   "Reasons to Prefer a Competitor",
    "regret":       "Post-Purchase Regret",
}


# ── YouTube helpers ────────────────────────────────────────────────────────────

def build_youtube(api_key: str):
    return build("youtube", "v3", developerKey=api_key)


def search_videos(yt, query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> dict[str, str]:
    """
    Search YouTube with Korean region/language filters.
    Falls back to removing regionCode if no results are returned.
    Returns {url: video_id}.
    """
    base_kwargs = dict(
        part="snippet",
        maxResults=max_results,
        q=query,
        type="video",
        relevanceLanguage="ko",
    )
    for use_region in (True, False):
        kwargs = dict(base_kwargs)
        if use_region:
            kwargs["regionCode"] = "KR"
        try:
            resp = yt.search().list(**kwargs).execute()
            items = resp.get("items", [])
            if items:
                return {
                    f"https://www.youtube.com/watch?v={item['id']['videoId']}": item["id"]["videoId"]
                    for item in items
                }
        except HttpError as e:
            log.warning(f"Search error for '{query}' (region={use_region}): {e}")
    return {}


def get_video_details(yt, video_id: str) -> Optional[dict]:
    """Fetch snippet + statistics for a single video."""
    try:
        resp = yt.videos().list(
            part="snippet,statistics",
            id=video_id,
        ).execute()
        if not resp.get("items"):
            return None
        item = resp["items"][0]
        stats = item["statistics"]
        return {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": item["snippet"]["title"],
            "channel": item["snippet"].get("channelTitle", ""),
            "published_at": item["snippet"]["publishedAt"][:10],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
        }
    except HttpError as e:
        log.warning(f"Video details error for {video_id}: {e}")
        return None


def fetch_comments(yt, video_id: str, max_comments: int = MAX_COMMENTS) -> list[dict]:
    """
    Fetch up to max_comments top-level comments ordered by relevance.
    Paginates across up to 2 pages (200 comments max).
    """
    comments: list[dict] = []

    def _parse_page(response: dict) -> None:
        for item in response.get("items", []):
            s = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "video_id": video_id,
                "author": s.get("authorDisplayName", ""),
                "comment": s.get("textDisplay", ""),
                "likes": int(s.get("likeCount", 0)),
                "reply_count": int(item["snippet"].get("totalReplyCount", 0)),
                "published_at": s.get("publishedAt", "")[:10],
            })

    try:
        resp = yt.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            order="relevance",
            textFormat="plainText",
        ).execute()
        _parse_page(resp)

        page_token = resp.get("nextPageToken")
        if page_token and len(comments) < max_comments:
            resp2 = yt.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                order="relevance",
                textFormat="plainText",
                pageToken=page_token,
            ).execute()
            _parse_page(resp2)

    except HttpError as e:
        reason = str(e)
        if "commentsDisabled" in reason or e.resp.status == 403:
            log.info(f"Comments disabled: {video_id}")
        else:
            log.warning(f"Comments error for {video_id}: {e}")

    return comments[:max_comments]


def build_transcript_api() -> None:
    """No-op — kept for API compatibility. Audio is now fetched via yt_dlp in extract_transcript_arguments."""
    return None


_AUDIO_MIME: dict[str, str] = {
    "m4a": "audio/mp4", "mp4": "audio/mp4",
    "webm": "audio/webm", "opus": "audio/ogg",
    "mp3": "audio/mpeg", "ogg": "audio/ogg",
}


def _download_audio(video_url: str, output_dir: str) -> Optional[tuple[str, str]]:
    """
    Download best audio (no ffmpeg needed) to output_dir.
    Tries multiple yt_dlp player clients sequentially.
    Returns (file_path, mime_type) or None on failure.
    """
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or None
    cookies_path = str(COOKIES_PATH) if COOKIES_PATH.exists() else None
    # android* clients don't support cookies; web clients use cookies
    android_clients = {"android", "android_vr", "android_embedded", "android_creator"}

    for client_hint in [["android_vr"], ["android"], ["web"], ["ios"], ["tv_embedded"], ["mweb"]]:
        ydl_opts: dict = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
            "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": client_hint}},
        }
        if proxy:
            ydl_opts["proxy"] = proxy
        if cookies_path and client_hint[0] not in android_clients:
            ydl_opts["cookiefile"] = cookies_path
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                vid_id = info.get("id", "")
                ext = info.get("ext", "m4a")
                path = os.path.join(output_dir, f"{vid_id}.{ext}")
                if os.path.exists(path):
                    return path, _AUDIO_MIME.get(ext, "audio/mpeg")
        except Exception:
            continue
    log.warning(f"Audio download failed for all clients: {video_url}")
    return None


# ── Ranking ────────────────────────────────────────────────────────────────────

def compute_video_ranks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add video_rank column.
    video_rank = 0.5 * (likes / max_likes) + 0.5 * (views / max_views)
    Normalized within the current set of videos.
    """
    df = df.copy()
    max_likes = df["likes"].max() or 1
    max_views = df["views"].max() or 1
    df["video_rank"] = (
        0.5 * (df["likes"] / max_likes) +
        0.5 * (df["views"] / max_views)
    )
    return df


def comment_rank(video_rank: float, comment_likes: int) -> float:
    """
    comment_rank = log(1 + video_rank) * comment_likes
    log(1 + video_rank) softens the video popularity multiplier.
    """
    return math.log(1.0 + video_rank) * comment_likes


# ── Pydantic schemas for structured Gemini output ─────────────────────────────

class ArgumentItem(BaseModel):
    category: str = Field(description="One of: non_purchase, competitor, regret")
    argument: str = Field(description="Concise English argument summary (max 20 words)")
    quote: str = Field(description="Verbatim quote from audio (Korean OK, max 60 words)")
    mention_count: int = Field(description="How many times this argument theme is mentioned in the audio (1 if only once)")

class TranscriptArguments(BaseModel):
    arguments: list[ArgumentItem] = Field(default_factory=list)

class CommentItem(BaseModel):
    comment: str = Field(description="Exact verbatim comment text")
    argument: str = Field(description="Concise English argument summary (max 15 words)")
    category: str = Field(description="One of: non_purchase, competitor, regret")

class CommentArguments(BaseModel):
    items: list[CommentItem] = Field(default_factory=list)

class QuoteItem(BaseModel):
    text: str = Field(description="Original quote text (Korean or English)")
    source_url: str
    source_type: str = Field(description="transcript or comment")

class MergedArgument(BaseModel):
    argument: str = Field(description="Merged management-ready English argument title (max 20 words)")
    combined_rank: float = Field(description="Sum of ranks of merged items, capped at 1.0")
    quotes: list[QuoteItem] = Field(description="2-3 most illustrative quotes")
    source_count: int = Field(description="Total number of input lines (comments/transcript mentions) grouped into this merged argument, i.e. the sum of each input line's own count:N value")

class MergedArguments(BaseModel):
    merged_arguments: list[MergedArgument]


# ── Gemini helpers ─────────────────────────────────────────────────────────────

def init_gemini(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def _gemini_call(client: genai.Client, prompt: str, schema: type, contents=None) -> Optional[object]:
    """Call Gemini with structured JSON output and exponential backoff retry."""
    payload = contents if contents is not None else prompt
    for attempt in range(GEMINI_RETRY_ATTEMPTS):
        try:
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=payload,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return schema.model_validate_json(resp.text)
        except Exception as e:
            if attempt < GEMINI_RETRY_ATTEMPTS - 1:
                wait = 2 ** (attempt + 1)
                log.warning(f"Gemini error (attempt {attempt + 1}): {e} — retrying in {wait}s")
                time.sleep(wait)
            else:
                log.error(f"Gemini failed after {GEMINI_RETRY_ATTEMPTS} attempts: {e}")
    return None


# Keep parse_json for any legacy use
def parse_json(text: str) -> Optional[dict | list]:
    """Strip markdown code fences and parse JSON."""
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ── Argument extraction: transcripts ──────────────────────────────────────────

AUDIO_DOWNLOAD_DELAY = 2.0  # seconds between sequential audio downloads


def extract_transcript_arguments(
    client: genai.Client,
    video_url: str,
    title: str,
    audio_path: str,    # pre-downloaded audio file path (empty string = skip)
    car_name: str,
    mime_type: str = "audio/mp4",
) -> list[dict]:
    """
    Upload a pre-downloaded audio file to Gemini Files API and extract arguments.
    audio_path must exist. Returns [] if path is empty or upload fails.
    """
    if not audio_path or not os.path.exists(audio_path):
        return []

    video_id = video_url.split("v=")[-1].split("&")[0]

    try:
        uploaded = client.files.upload(
            file=audio_path,
            config={"mime_type": mime_type},
        )
    except Exception as e:
        log.warning(f"Gemini file upload error ({video_id}): {e}")
        return []

    try:
        prompt = (
            f"You are a Korean automotive market research analyst preparing a management briefing.\n\n"
            f"Listen to this YouTube video about the {car_name} and extract negative arguments.\n\n"
            f"Extract arguments in exactly these three categories:\n"
            f'1. "non_purchase" – explicit reasons a consumer would NOT buy the {car_name}\n'
            f'2. "competitor" – reasons to prefer a competitor car over the {car_name}\n'
            f'3. "regret" – reasons why a buyer of the {car_name} might regret the purchase\n\n'
            f"Rules:\n"
            f"- Only include arguments clearly stated or strongly implied in the audio\n"
            f"- argument: concise English sentence (max 20 words)\n"
            f"- quote: verbatim phrase from the audio (Korean OK, max 60 words)\n"
            f"- mention_count: how many times this theme appears in the audio\n"
            f"- Sort by mention_count descending within each category\n"
            f"- Skip purely positive or off-topic content\n\n"
            f"Video title: {title}"
        )
        result = _gemini_call(client, prompt, TranscriptArguments, contents=[prompt, uploaded])
        if not result:
            return []
        return [
            {
                "category": arg.category,
                "argument": arg.argument,
                "quote": arg.quote,
                "mention_count": arg.mention_count,
                "source_url": video_url,
                "source_title": title,
                "source_type": "audio",
            }
            for arg in result.arguments
            if arg.category in CATEGORIES
        ]
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass




# ── Argument extraction: comments ─────────────────────────────────────────────

def extract_comment_arguments(
    client: genai.Client,
    video_url: str,
    title: str,
    comments: list[dict],
    car_name: str,
) -> list[dict]:
    """
    Send comments in batches of COMMENT_BATCH_SIZE to Gemini.
    Returns list of {category, argument, comment, comment_likes, source_url, source_title, source_type}.
    """
    results: list[dict] = []

    likes_lookup: dict[str, int] = {}
    for c in comments:
        if c["comment"] not in likes_lookup:
            likes_lookup[c["comment"]] = c["likes"]

    for batch_start in range(0, len(comments), COMMENT_BATCH_SIZE):
        batch = comments[batch_start: batch_start + COMMENT_BATCH_SIZE]
        numbered = "\n".join(
            f"{i + 1}. [likes:{c['likes']}] {c['comment']}"
            for i, c in enumerate(batch)
        )
        prompt = (
            f"You are a Korean automotive market research analyst.\n\n"
            f"Below are YouTube comments from a video about the {car_name}.\n\n"
            f"Identify ONLY comments that contain arguments in these categories:\n"
            f'1. "non_purchase" – reasons not to buy the {car_name}\n'
            f'2. "competitor" – reasons to prefer a competitor car over the {car_name}\n'
            f'3. "regret" – regret after buying the {car_name}\n\n'
            f"Ignore: general praise, off-topic comments, questions without arguments, greetings, emojis-only.\n\n"
            f"Video: {title}\nComments:\n{numbered}"
        )
        result = _gemini_call(client, prompt, CommentArguments)
        if result:
            for item in result.items:
                if item.category in CATEGORIES:
                    results.append({
                        "comment": item.comment,
                        "argument": item.argument,
                        "category": item.category,
                        "comment_likes": likes_lookup.get(item.comment, 0),
                        "source_url": video_url,
                        "source_title": title,
                        "source_type": "comment",
                    })

        time.sleep(0.3)

    return results


# ── Argument merging ───────────────────────────────────────────────────────────

MERGE_CHUNK_SIZE = 100   # args per Gemini merge call
MERGE_MAX_FINAL = 15     # hard cap on final merged arguments


def _merge_chunk(
    client: genai.Client,
    chunk: list[dict],
    category_label: str,
    car_name: str,
) -> list[dict]:
    """Merge one chunk of ≤MERGE_CHUNK_SIZE arguments via Gemini structured output."""
    def _safe_str(v) -> str:
        # Guards against NaN (float) values coming from pandas round-trips through CSV,
        # where a missing 'quote'/'comment' cell becomes float('nan') instead of "".
        return v if isinstance(v, str) else ""

    lines = [
        f"[rank:{a.get('rank', 0.0):.4f}|type:{a.get('source_type','')}|url:{a.get('source_url','')}|count:{a.get('source_count', 1)}] "
        f"{a.get('argument','')} || quote: {(_safe_str(a.get('quote')) or _safe_str(a.get('comment')))[:120]}"
        for a in chunk
    ]
    prompt = (
        f"You are a senior market research analyst writing a management briefing.\n\n"
        f"Arguments from Korean YouTube videos/comments about the {car_name} — category: {category_label}.\n\n"
        f"Each line: [rank:X|type:transcript/comment|url:...|count:N] argument || quote: ...\n"
        f"Higher rank = more impactful source. count:N is how many individual sources that single line already represents.\n\n"
        f"Task:\n"
        f"1. Group semantically similar/overlapping arguments together\n"
        f"2. Merge each group into ONE clear English argument title (max 20 words)\n"
        f"3. Sum ranks of merged items (cap combined_rank at 1.0)\n"
        f"4. Keep 2-3 most illustrative quotes per group (original Korean OK)\n"
        f"5. Set source_count to the sum of count:N across every input line placed in that group\n"
        f"6. Target 5-10 merged arguments maximum — aggressively group similar themes\n"
        f"7. Sort by combined_rank descending\n\n"
        f"Arguments:\n" + "\n".join(lines)
    )
    result = _gemini_call(client, prompt, MergedArguments)
    if not result:
        return []
    return [
        {
            "argument": m.argument,
            "combined_rank": min(m.combined_rank, 1.0),
            "quotes": [{"text": q.text, "source_url": q.source_url, "source_type": q.source_type} for q in m.quotes],
            "source_count": max(m.source_count, 1),
        }
        for m in result.merged_arguments
    ]


def merge_and_rerank(
    client: genai.Client,
    arguments: list[dict],
    category: str,
    car_name: str,
) -> list[dict]:
    """
    Two-pass chunked merge:
      Pass 1 — split raw args into MERGE_CHUNK_SIZE chunks, merge each independently
      Pass 2 — merge the pass-1 results into final MERGE_MAX_FINAL arguments
    Falls back to top-N deduplication if both passes fail.
    """
    if not arguments:
        return []

    category_label = CATEGORY_LABELS[category]

    # Pass 1: chunk merge
    pass1_results: list[dict] = []
    chunks = [arguments[i:i + MERGE_CHUNK_SIZE] for i in range(0, len(arguments), MERGE_CHUNK_SIZE)]
    log.info(f"  Merge {category} — {len(arguments)} args → {len(chunks)} chunk(s)")

    for idx, chunk in enumerate(chunks):
        merged = _merge_chunk(client, chunk, category_label, car_name)
        if merged:
            pass1_results.extend(merged)
            log.info(f"    Chunk {idx+1}/{len(chunks)}: {len(chunk)} args → {len(merged)} merged")
        else:
            # chunk fallback: top-5 by rank
            log.warning(f"    Chunk {idx+1}/{len(chunks)}: merge failed, using top-5 fallback")
            for a in sorted(chunk, key=lambda x: x.get("rank", 0.0), reverse=True)[:5]:
                _q, _c = a.get("quote"), a.get("comment")
                quote_text = (_q if isinstance(_q, str) else "") or (_c if isinstance(_c, str) else "")
                pass1_results.append({
                    "argument": a.get("argument", ""),
                    "combined_rank": round(a.get("rank", 0.0), 4),
                    "quotes": [{"text": quote_text[:200], "source_url": a.get("source_url", ""), "source_type": a.get("source_type", "")}],
                    "source_count": a.get("source_count", 1),
                })

    if not pass1_results:
        return []

    # Pass 2: final merge across chunk results (already small enough)
    log.info(f"  Merge {category} — pass 2: {len(pass1_results)} → target ≤{MERGE_MAX_FINAL}")
    if len(pass1_results) <= MERGE_MAX_FINAL:
        final = sorted(pass1_results, key=lambda x: x.get("combined_rank", 0.0), reverse=True)
    else:
        # Convert pass1 results to arg dicts compatible with _merge_chunk
        p1_as_args = [
            {
                "argument": r["argument"],
                "rank": r.get("combined_rank", 0.0),
                "quote": r["quotes"][0]["text"] if r.get("quotes") else "",
                "source_url": r["quotes"][0]["source_url"] if r.get("quotes") else "",
                "source_type": r["quotes"][0]["source_type"] if r.get("quotes") else "",
                "source_count": r.get("source_count", 1),
            }
            for r in pass1_results
        ]
        final = _merge_chunk(client, p1_as_args, category_label, car_name)
        if not final:
            log.warning(f"  Pass 2 merge failed for {car_name}/{category}, using pass1 top-{MERGE_MAX_FINAL}")
            final = sorted(pass1_results, key=lambda x: x.get("combined_rank", 0.0), reverse=True)

    # Hard cap
    return final[:MERGE_MAX_FINAL]


# ── Docx helpers ───────────────────────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str) -> None:
    """Set background color of a table cell."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _add_separator(doc: Document) -> None:
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pb = OxmlElement("w:pageBreakBefore")
    pb.set(qn("w:val"), "0")
    pPr.append(pb)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run("─" * 80)
    run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    run.font.size = Pt(8)


def _add_argument_block(doc: Document, rank_idx: int, merged: dict) -> None:
    """Add one ranked argument with its quotes to the document."""
    arg_text = merged.get("argument", "N/A")
    combined_rank = merged.get("combined_rank", 0.0)
    quotes = merged.get("quotes", [])
    source_count = merged.get("source_count", 1)

    # Argument title
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    run_num = p.add_run(f"{rank_idx}. ")
    run_num.bold = True
    run_num.font.size = Pt(11)
    run_main = p.add_run(arg_text)
    run_main.bold = True
    run_main.font.size = Pt(11)
    source_label = "source" if source_count == 1 else "sources"
    run_score = p.add_run(f"  [score: {combined_rank:.3f} · {source_count} {source_label}]")
    run_score.font.size = Pt(9)
    run_score.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # Quotes
    for q in quotes[:3]:
        q_text = q.get("text", "").strip()
        q_url = q.get("source_url", "")
        q_type = q.get("source_type", "")
        if not q_text:
            continue

        q_para = doc.add_paragraph()
        q_para.paragraph_format.left_indent = Inches(0.4)
        q_para.paragraph_format.space_before = Pt(2)
        q_para.paragraph_format.space_after = Pt(2)

        quote_run = q_para.add_run(f'"{q_text}"')
        quote_run.italic = True
        quote_run.font.size = Pt(9.5)
        quote_run.font.color.rgb = RGBColor(0x33, 0x33, 0x55)

        if q_url:
            src_run = q_para.add_run(f"\n  → {q_url}  [{q_type}]")
            src_run.font.size = Pt(8)
            src_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


def build_docx_report(
    results_per_car: dict,
    video_counts: dict,
    comment_counts: dict,
    output_path: Path,
) -> None:
    """
    Generate the structured .docx management report.

    Structure:
      - Title + methodology
      - Per car: non_purchase + competitor reasons
      - Separate section: regret (both cars)
    """
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1.2)

    # ── Title ──────────────────────────────────────────────────────────────────
    title = doc.add_heading("Korean Consumer Barriers to Purchase", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph("Grand Koleos & Filante — YouTube Analysis")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.runs[0].font.size = Pt(13)
    sub.runs[0].font.color.rgb = RGBColor(0x44, 0x44, 0x44)

    date_p = doc.add_paragraph(f"Date: {pd.Timestamp.now().strftime('%B %d, %Y')}")
    date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_p.runs[0].font.size = Pt(10)
    date_p.runs[0].font.color.rgb = RGBColor(0x77, 0x77, 0x77)

    doc.add_paragraph()

    # ── Methodology ────────────────────────────────────────────────────────────
    doc.add_heading("Methodology", 1)

    total_videos = sum(video_counts.values())
    total_comments = sum(comment_counts.values())

    p = doc.add_paragraph()
    p.add_run("Data Sources: ").bold = True
    p.add_run(
        f"{total_videos} Korean YouTube videos ({total_comments} comments with ≥2 likes). "
        "Transcripts extracted via YouTube caption API (Korean preferred, English fallback). "
        "Comments filtered to top 200 per video by relevance."
    )

    p = doc.add_paragraph()
    p.add_run("Video Rank: ").bold = True
    p.add_run("0.5 × (likes / max_likes) + 0.5 × (views / max_views), normalized within each car.")

    p = doc.add_paragraph()
    p.add_run("Comment Rank: ").bold = True
    p.add_run("log(1 + video_rank) × comment_likes — softens video popularity bias while rewarding liked comments.")

    p = doc.add_paragraph()
    p.add_run("Argument Extraction: ").bold = True
    p.add_run(
        f"{GEMINI_MODEL} extracts arguments from transcripts (per video) "
        "and from comment batches of 50. Arguments are then semantically clustered "
        "and re-ranked by Gemini, with ranks summed across matching sources."
    )

    for car_key in ["koleos", "filante"]:
        p = doc.add_paragraph()
        p.add_run(f"{CAR_NAMES[car_key]}: ").bold = True
        p.add_run(f"{video_counts.get(car_key, 0)} videos, {comment_counts.get(car_key, 0)} qualifying comments.")

    doc.add_paragraph()

    # ── Per-car non-purchase + competitor sections ──────────────────────────────
    for car_key, car_name in CAR_NAMES.items():
        car_results = results_per_car.get(car_key, {})

        # Car header
        doc.add_heading(car_name, 1)

        for category in ["non_purchase", "competitor"]:
            label = CATEGORY_LABELS[category]
            merged_args = car_results.get(category, [])

            doc.add_heading(label, 2)

            if not merged_args:
                doc.add_paragraph("No significant arguments found for this category.")
            else:
                doc.add_paragraph(f"{len(merged_args)} argument(s) identified, ranked by combined score.")
                for idx, merged in enumerate(merged_args, 1):
                    _add_argument_block(doc, idx, merged)

            doc.add_paragraph()

        _add_separator(doc)

    # ── Post-Purchase Regret (separate section) ─────────────────────────────────
    doc.add_heading("Post-Purchase Regret", 1)
    doc.add_paragraph(
        "The following arguments represent reasons why consumers who already purchased "
        "the Grand Koleos or Filante express regret. These are distinct from purchase "
        "barriers and reflect real ownership pain points."
    )
    doc.add_paragraph()

    for car_key, car_name in CAR_NAMES.items():
        car_results = results_per_car.get(car_key, {})
        merged_args = car_results.get("regret", [])

        doc.add_heading(f"{car_name} — Regret Reasons", 2)

        if not merged_args:
            doc.add_paragraph("No significant regret arguments found.")
        else:
            doc.add_paragraph(f"{len(merged_args)} argument(s) identified, ranked by combined score.")
            for idx, merged in enumerate(merged_args, 1):
                _add_argument_block(doc, idx, merged)

        doc.add_paragraph()

    doc.save(str(output_path))
    log.info(f"Report saved → {output_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    yt = build_youtube(YOUTUBE_API_KEY)
    gemini = init_gemini(GOOGLE_API_KEY)

    results_per_car: dict[str, dict[str, list]] = {}
    video_counts: dict[str, int] = {}
    comment_counts: dict[str, int] = {}

    for car_key, car_name in CAR_NAMES.items():
        log.info(f"\n{'=' * 60}\nProcessing: {car_name}\n{'=' * 60}")

        # ── Step 1: Search videos ──────────────────────────────────────────────
        log.info("Step 1: Searching YouTube for relevant videos...")
        video_dict: dict[str, str] = {}
        for query in SEARCH_QUERIES[car_key]:
            found = search_videos(yt, query)
            new = {url: vid for url, vid in found.items() if url not in video_dict}
            video_dict.update(new)
            log.info(f"  '{query}' → {len(found)} videos ({len(new)} new)")
            time.sleep(0.2)

        log.info(f"Total unique videos found: {len(video_dict)}")

        # ── Step 2: Fetch video details ────────────────────────────────────────
        log.info("Step 2: Fetching video details...")
        video_details: list[dict] = []
        for url, video_id in video_dict.items():
            details = get_video_details(yt, video_id)
            if details:
                video_details.append(details)
            time.sleep(0.05)

        if not video_details:
            log.warning(f"No video details returned for {car_name} — skipping.")
            results_per_car[car_key] = {c: [] for c in CATEGORIES}
            video_counts[car_key] = 0
            comment_counts[car_key] = 0
            continue

        videos_df = pd.DataFrame(video_details)
        videos_df = compute_video_ranks(videos_df)
        video_counts[car_key] = len(videos_df)

        # Save video metadata
        videos_df.to_csv(OUTPUT_DIR / f"{car_key}_videos.csv", index=False, encoding="utf-8-sig")
        log.info(f"Videos with details: {len(videos_df)}")

        # ── Step 3: Fetch comments ─────────────────────────────────────────────
        log.info("Step 3: Fetching comments...")
        video_data: list[dict] = []
        total_qualifying_comments = 0

        for _, row in videos_df.iterrows():
            vid_id = row["video_id"]
            v_rank = float(row["video_rank"])

            raw_comments = fetch_comments(yt, vid_id)

            # Filter + rank comments
            qualifying = [
                {**c, "rank": comment_rank(v_rank, c["likes"]), "video_rank": v_rank}
                for c in raw_comments
                if c["likes"] >= MIN_COMMENT_LIKES
            ]
            total_qualifying_comments += len(qualifying)

            video_data.append({
                "video_id": vid_id,
                "url": row["url"],
                "title": row["title"],
                "video_rank": v_rank,
                "comments": qualifying,
            })

            log.info(f"  [{len(qualifying)} comments] {row['title'][:65]}")
            time.sleep(0.2)

        comment_counts[car_key] = total_qualifying_comments
        log.info(f"Comments qualifying (≥{MIN_COMMENT_LIKES} likes): {total_qualifying_comments}")

        # Save comments to CSV immediately (crash safety)
        comment_rows = [
            {**c, "video_title": vd["title"]}
            for vd in video_data for c in vd["comments"]
        ]
        if comment_rows:
            pd.DataFrame(comment_rows).to_csv(
                OUTPUT_DIR / f"{car_key}_comments.csv", index=False, encoding="utf-8-sig"
            )
        log.info(f"Comments saved to CSV.")

        # ── Step 4: Extract arguments in parallel ──────────────────────────────
        n_audio_videos = len(video_data)
        n_comment_videos = sum(1 for vd in video_data if vd["comments"])
        log.info(
            f"Step 4: Extracting arguments with Gemini ({GEMINI_WORKERS} workers)...\n"
            f"  Audio jobs: {n_audio_videos} | Comment-batch jobs: {n_comment_videos}"
        )

        # Phase 4a: sequential audio downloads (avoids hammering YouTube)
        log.info("  Phase 4a: downloading audio sequentially...")
        audio_dir = OUTPUT_DIR / f"{car_key}_audio"
        audio_dir.mkdir(exist_ok=True)
        for i, vd in enumerate(video_data):
            result = _download_audio(vd["url"], str(audio_dir))
            if result:
                vd["audio_path"], vd["audio_mime"] = result
                log.info(f"  [{i+1}/{n_audio_videos} ✓] {vd['title'][:65]}")
            else:
                vd["audio_path"], vd["audio_mime"] = "", "audio/mp4"
                log.info(f"  [{i+1}/{n_audio_videos} ✗] {vd['title'][:65]}")
            time.sleep(AUDIO_DOWNLOAD_DELAY)

        raw_arguments: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
        audio_futures: dict = {}
        comment_futures: dict = {}

        import threading
        _lock = threading.Lock()
        t_done = 0
        c_done = 0

        # Phase 4b: parallel Gemini extraction (audio upload + comment batches)
        log.info("  Phase 4b: parallel Gemini extraction...")
        with ThreadPoolExecutor(max_workers=GEMINI_WORKERS) as executor:
            for vd in video_data:
                if vd.get("audio_path"):
                    f = executor.submit(
                        extract_transcript_arguments,
                        gemini, vd["url"], vd["title"], vd["audio_path"], car_name, vd["audio_mime"],
                    )
                    audio_futures[f] = vd

                if vd["comments"]:
                    f = executor.submit(
                        extract_comment_arguments,
                        gemini, vd["url"], vd["title"], vd["comments"], car_name,
                    )
                    comment_futures[f] = vd

            for future in as_completed(audio_futures):
                vd = audio_futures[future]
                try:
                    args = future.result()
                    found = {cat: 0 for cat in CATEGORIES}
                    for arg in args:
                        mc = arg.pop("mention_count", 1)
                        arg["rank"] = vd["video_rank"] * math.log(1 + mc)
                        cat = arg.get("category")
                        if cat in raw_arguments:
                            with _lock:
                                raw_arguments[cat].append(arg)
                            found[cat] += 1
                    with _lock:
                        t_done += 1
                        done_now = t_done
                    summary = ", ".join(f"{cat}:{n}" for cat, n in found.items() if n)
                    log.info(
                        f"  [audio {done_now}/{n_audio_videos}] "
                        f"{vd['title'][:55]} → {summary or 'no args'}"
                    )
                except Exception as e:
                    log.warning(f"Audio future error ({vd['url']}): {e}")

            for future in as_completed(comment_futures):
                vd = comment_futures[future]
                try:
                    args = future.result()
                    rank_lookup = {c["comment"]: c["rank"] for c in vd["comments"]}
                    found = {cat: 0 for cat in CATEGORIES}
                    for arg in args:
                        c_text = arg.get("comment", "")
                        arg["rank"] = rank_lookup.get(c_text, 0.0)
                        cat = arg.get("category")
                        if cat in raw_arguments:
                            with _lock:
                                raw_arguments[cat].append(arg)
                            found[cat] += 1
                    with _lock:
                        c_done += 1
                        done_now = c_done
                    n_batches = math.ceil(len(vd["comments"]) / COMMENT_BATCH_SIZE)
                    summary = ", ".join(f"{cat}:{n}" for cat, n in found.items() if n)
                    log.info(
                        f"  [comments  {done_now}/{n_comment_videos}] "
                        f"{vd['title'][:55]} ({n_batches} batch{'es' if n_batches>1 else ''}) "
                        f"→ {summary or 'no args'}"
                    )
                except Exception as e:
                    log.warning(f"Comment future error ({vd['url']}): {e}")

        for cat, args in raw_arguments.items():
            log.info(f"  Raw arguments — {cat}: {len(args)}")

        # Save raw arguments to CSV
        all_raw = []
        for cat, args in raw_arguments.items():
            for a in args:
                all_raw.append({**a, "category": cat})
        if all_raw:
            pd.DataFrame(all_raw).to_csv(
                OUTPUT_DIR / f"{car_key}_raw_arguments.csv", index=False, encoding="utf-8-sig"
            )

        # ── Step 5: Merge and re-rank ──────────────────────────────────────────
        log.info("Step 5: Merging and re-ranking arguments with Gemini...")
        merged_results: dict[str, list] = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            merge_futures = {
                executor.submit(merge_and_rerank, gemini, raw_arguments[cat], cat, car_name): cat
                for cat in CATEGORIES
                if raw_arguments[cat]
            }
            for f in as_completed(merge_futures):
                cat = merge_futures[f]
                try:
                    merged = f.result()
                    merged_results[cat] = merged
                    log.info(f"  Merged — {cat}: {len(merged)} arguments")
                except Exception as e:
                    log.warning(f"Merge future error ({cat}): {e}")
                    merged_results[cat] = []

        # Fill empty categories
        for cat in CATEGORIES:
            if cat not in merged_results:
                merged_results[cat] = []

        results_per_car[car_key] = merged_results

    # ── Step 6: Generate .docx report ─────────────────────────────────────────
    log.info("\nStep 6: Generating .docx report...")
    output_path = OUTPUT_DIR / "koleos_filante_non_purchase_analysis.docx"
    build_docx_report(results_per_car, video_counts, comment_counts, output_path)

    log.info(f"\nDone. Report: {output_path}")


if __name__ == "__main__":
    main()
