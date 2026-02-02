"""
Quick test script to verify the full pipeline with YouTube captions.
Tests a single video: https://www.youtube.com/watch?v=klQq_FpJWZc
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

print("=" * 60)
print("Testing Full Pipeline with YouTube Captions")
print("=" * 60)

# Test video about Renault
video_url = "https://www.youtube.com/watch?v=klQq_FpJWZc"
video_id = "klQq_FpJWZc"

# Step 1: Fetch captions
print(f"\n[Step 1] Fetching YouTube captions for {video_id}...")

from youtube_transcript_api import YouTubeTranscriptApi

api = YouTubeTranscriptApi()
transcript_data = api.fetch(video_id, languages=['ko', 'en'])
transcript = " ".join([segment.text for segment in transcript_data])

print(f"✓ Got {len(transcript)} characters from {len(transcript_data)} segments")

# Step 2: Check API key for Gemini analysis
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("\n⚠ GOOGLE_API_KEY not set - skipping AI analysis")
    print("  Set it with: $env:GOOGLE_API_KEY='your-key'")
    print("\n[Transcript Preview]")
    print("-" * 40)
    print(transcript[:1000])
    print("-" * 40)
    sys.exit(0)

# Step 3: Run AI Analysis
print(f"\n[Step 2] Running AI Analysis with Gemini...")

from src.config import CarModel
from src.analysis import GeminiClient, VideoAnalyzer

car_model = CarModel(
    company="르노",
    model="Scenic E-Tech",
    search_queries=["르노 세닉"]
)

gemini = GeminiClient(api_key, model_name="gemini-2.0-flash")
analyzer = VideoAnalyzer(gemini)

print("  Analyzing transcript...")
analysis = analyzer.analyze_transcript(video_url, transcript, car_model)

print(f"\n[Analysis Results]")
print("=" * 60)
print(f"Overall Sentiment: {analysis.overall_sentiment} ({analysis.sentiment_score}/100)")
print(f"\nKey Strengths:")
for s in analysis.key_strengths[:5]:
    print(f"  • {s}")
print(f"\nKey Weaknesses:")
for w in analysis.key_weaknesses[:5]:
    print(f"  • {w}")
print(f"\nBrand Sentiment: {analysis.brand_sentiment}")
print(f"Renault Brand Sentiment: {analysis.renault_brand_sentiment}")
print(f"\nCompetitor Mentions:")
for c in analysis.competitor_mentions[:3]:
    print(f"  • {c.competitor}: {c.comparison_summary[:100]}...")
print(f"\nFinal Verdict: {analysis.final_verdict}")
print("=" * 60)
print("\n✓ Full pipeline test complete!")
