"""
AI-powered analysis module using Google Gemini.
Handles sentiment analysis, content extraction, and persona generation.
"""

import json
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, asdict
from enum import Enum

import google.generativeai as genai
import pandas as pd
from tqdm import tqdm

if TYPE_CHECKING:
    from .config import CarModel, PipelineConfig


class Sentiment(Enum):
    """Sentiment classification."""
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


@dataclass
class CompetitorMention:
    """Information about competitor mention."""
    competitor: str
    comparison_summary: str


@dataclass
class VideoAnalysis:
    """Result of video transcript analysis."""
    video_url: str
    overall_sentiment: str
    sentiment_score: int
    key_strengths: List[str]
    key_weaknesses: List[str]
    renault_brand_sentiment: str
    competitor_mentions: List[CompetitorMention]
    trends: List[str]
    battery_performance: str
    noise_levels: str
    competitor_perception: str
    chinese_brand_mentions: str
    final_verdict: str
    raw_response: Optional[str] = None


@dataclass
class UserPersona:
    """User persona derived from comment analysis."""
    name: str
    description: str
    age_group: str
    interests: List[str]
    motivations: List[str]
    pain_points: List[str]
    content_preferences: List[str]


@dataclass
class CommentAnalysis:
    """Result of comment analysis for a video."""
    video_url: str
    themes: List[str]
    sentiment_breakdown: Dict[str, float]
    recurring_topics: List[str]
    keywords: List[str]
    personas: List[UserPersona]
    raw_response: Optional[str] = None


class GeminiClient:
    """Client for Google Gemini AI."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
    def generate(self, prompt: str) -> str:
        """Generate response from Gemini."""
        response = self.model.generate_content(prompt)
        return response.text.strip()


class VideoAnalyzer:
    """Analyzer for video transcripts."""
    
    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client
    
    def _build_analysis_prompt(self, car_model: "CarModel") -> str:
        """Build the analysis instruction prompt."""
        return f'''Analyze the following transcript of a YouTube video discussing the {car_model.company} {car_model.model}. Write everything in English.
Do not make any comments that are unrelated to the video to introduce the task.
Your goal is only to extract key insights and classify the content based on the following criteria:

Overall Sentiment: Determine if the video is positive, neutral, or negative toward the {car_model.model}.
Provide a percentage score for your classification, 0 being extremely negative, 50 being neutral, 100 being extremely positive.

Key Strengths Highlighted: Identify the main positive aspects the influencer mentions (e.g., design, performance, technology, comfort, pricing).

Key Weaknesses Highlighted: Identify the main negative aspects the influencer mentions (e.g., high price, poor fuel economy, lack of features).
Do not hesitate to point them out.

Comments on Renault Brand: Does the influencer mention Renault as a brand? If so, is the sentiment positive, neutral, or negative?

Comparison to Competitors: If the video mentions other car brands/models, list them and summarize the comparisons.

Trends & Topics (if available, otherwise return only '/'): Identify any recurring themes (e.g., luxury appeal, fuel efficiency, safety features).

Influencer's Overall Verdict: Summarize the influencer's final thoughts on the {car_model.model} in one or two sentences.

Additional Insights to Extract:
- Battery Performance: Does the influencer mention issues like fast charging/discharging, battery life, or management system?
- Noise Levels: Are there comments on the vehicle being too noisy or too quiet at certain speeds?
- Competitor Perception: What car is perceived as the {car_model.model}'s main competitor?
- References to Chinese Brands: Does the influencer mention Chinese brands (e.g., BYD, Geely, Haval)? If so, in what context?

Return ONLY valid JSON in the following format (no markdown code blocks):
{{
  "sentiment_analysis": {{
    "overall_sentiment": "Positive",
    "score": 85
  }},
  "key_strengths": ["Spacious interior", "Fuel efficiency", "Modern technology"],
  "key_weaknesses": ["Expensive", "Limited color options"],
  "renault_brand_sentiment": "Neutral",
  "competitor_mentions": [
    {{
      "competitor": "Toyota RAV4",
      "comparison_summary": "Influencer states that the car has a better interior but higher price."
    }}
  ],
  "trends": ["Luxury appeal", "Fuel efficiency"],
  "battery_performance": "Fast discharge rate mentioned as a concern",
  "noise_levels": "Noted as being noisier than competitors at low speeds",
  "competitor_perception": "Compared mainly to Hyundai Tucson",
  "chinese_brand_mentions": "BYD frequently referenced regarding battery technology",
  "final_verdict": "The influencer believes that the car is a premium SUV with great features but might be slightly overpriced."
}}'''
    
    def analyze_transcript(
        self, 
        video_url: str, 
        transcript: str, 
        car_model: "CarModel"
    ) -> VideoAnalysis:
        """Analyze a video transcript."""
        instruction = self._build_analysis_prompt(car_model)
        prompt = f"{instruction}\n\nTranscript:\n{transcript}"
        
        try:
            response = self.client.generate(prompt)
            
            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]  # Remove first line
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            
            return VideoAnalysis(
                video_url=video_url,
                overall_sentiment=data.get("sentiment_analysis", {}).get("overall_sentiment", "N/A"),
                sentiment_score=data.get("sentiment_analysis", {}).get("score", 50),
                key_strengths=data.get("key_strengths", []),
                key_weaknesses=data.get("key_weaknesses", []),
                renault_brand_sentiment=data.get("renault_brand_sentiment", "N/A"),
                competitor_mentions=[
                    CompetitorMention(c.get("competitor", ""), c.get("comparison_summary", ""))
                    for c in data.get("competitor_mentions", [])
                ],
                trends=data.get("trends", []),
                battery_performance=data.get("battery_performance", "N/A"),
                noise_levels=data.get("noise_levels", "N/A"),
                competitor_perception=data.get("competitor_perception", "N/A"),
                chinese_brand_mentions=data.get("chinese_brand_mentions", "N/A"),
                final_verdict=data.get("final_verdict", "N/A"),
                raw_response=response
            )
        except json.JSONDecodeError as e:
            print(f"JSON parsing error for {video_url}: {e}")
            return VideoAnalysis(
                video_url=video_url,
                overall_sentiment="N/A",
                sentiment_score=50,
                key_strengths=[],
                key_weaknesses=[],
                renault_brand_sentiment="N/A",
                competitor_mentions=[],
                trends=[],
                battery_performance="N/A",
                noise_levels="N/A",
                competitor_perception="N/A",
                chinese_brand_mentions="N/A",
                final_verdict="N/A",
                raw_response=response
            )
    
    def analyze_multiple(
        self, 
        transcriptions: Dict[str, str], 
        car_model: "CarModel"
    ) -> List[VideoAnalysis]:
        """Analyze multiple video transcripts."""
        results = []
        
        for url, transcript in tqdm(transcriptions.items(), desc="Analyzing transcripts", unit="video"):
            analysis = self.analyze_transcript(url, transcript, car_model)
            results.append(analysis)
        
        return results


class CommentAnalyzer:
    """Analyzer for video comments to build user personas."""
    
    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client
    
    def _build_comment_prompt(self, car_model: "CarModel") -> str:
        """Build the comment analysis instruction prompt."""
        return f'''You are an AI trained in natural language processing, sentiment analysis, and user profiling.
Your task is to analyze YouTube comments and extract meaningful insights to build detailed customer/user profiles.
The YouTube video should be about the {car_model.company} {car_model.model}.

### Instructions:
1. **Comment Analysis:**
   - Identify common themes, topics, and patterns in the comments.
   - Detect recurring words, phrases, or sentiments.
   - Categorize comments into positive, negative, and neutral sentiments.

2. **User Profile Extraction:**
   - Determine key demographic traits (age, interests) based on language, slang, or references.
   - Identify user personas (e.g., casual viewer, enthusiast, expert, potential buyer).
   - Detect potential customer needs, pain points, and preferences.

3. **Engagement Insights:**
   - Assess the level of enthusiasm or emotional connection with the content.
   - Identify users' expectations, feedback, and suggestions for improvement.

4. **Summarized User Profiles:**
   - Generate 3-5 user personas based on the comment patterns.
   - Describe each persona with details such as age group, interests, motivations, and content preferences.

Return ONLY valid JSON in the following format (no markdown code blocks):
{{
  "themes": ["Design appreciation", "Price concerns", "Technology features"],
  "sentiment_breakdown": {{
    "positive": 65.0,
    "neutral": 25.0,
    "negative": 10.0
  }},
  "recurring_topics": ["Exterior design", "Interior quality", "Charging speed"],
  "keywords": ["beautiful", "expensive", "technology", "comfortable"],
  "personas": [
    {{
      "name": "Tech Enthusiast Tom",
      "description": "Male, 30-40 years old, interested in latest technology and EV innovations",
      "age_group": "30-40",
      "interests": ["Electric vehicles", "Technology", "Automotive reviews"],
      "motivations": ["Staying updated on EV market", "Comparing features"],
      "pain_points": ["High prices", "Limited charging infrastructure"],
      "content_preferences": ["Detailed tech reviews", "Comparison videos"]
    }}
  ]
}}'''
    
    def analyze_comments(
        self, 
        video_url: str, 
        comments: str, 
        car_model: "CarModel"
    ) -> CommentAnalysis:
        """Analyze comments for a single video."""
        instruction = self._build_comment_prompt(car_model)
        prompt = f"{instruction}\n\nComments:\n{comments}"
        
        try:
            response = self.client.generate(prompt)
            
            # Clean response
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            
            personas = [
                UserPersona(
                    name=p.get("name", "Unknown"),
                    description=p.get("description", ""),
                    age_group=p.get("age_group", "N/A"),
                    interests=p.get("interests", []),
                    motivations=p.get("motivations", []),
                    pain_points=p.get("pain_points", []),
                    content_preferences=p.get("content_preferences", [])
                )
                for p in data.get("personas", [])
            ]
            
            return CommentAnalysis(
                video_url=video_url,
                themes=data.get("themes", []),
                sentiment_breakdown=data.get("sentiment_breakdown", {}),
                recurring_topics=data.get("recurring_topics", []),
                keywords=data.get("keywords", []),
                personas=personas,
                raw_response=response
            )
        except json.JSONDecodeError as e:
            print(f"JSON parsing error for comments from {video_url}: {e}")
            return CommentAnalysis(
                video_url=video_url,
                themes=[],
                sentiment_breakdown={},
                recurring_topics=[],
                keywords=[],
                personas=[],
                raw_response=response
            )
    
    def analyze_all_comments(
        self, 
        comments_by_video: Dict[str, str], 
        car_model: "CarModel"
    ) -> Dict[str, CommentAnalysis]:
        """Analyze comments for multiple videos."""
        results = {}
        
        for video_url, comments in tqdm(comments_by_video.items(), desc="Analyzing comments", unit="video"):
            results[video_url] = self.analyze_comments(video_url, comments, car_model)
        
        return results


def analysis_to_dataframe(analyses: List[VideoAnalysis]) -> pd.DataFrame:
    """Convert list of VideoAnalysis to DataFrame."""
    rows = []
    
    for analysis in analyses:
        row = {
            "Video URL": analysis.video_url,
            "Overall Sentiment": analysis.overall_sentiment,
            "Sentiment Score": analysis.sentiment_score,
            "Key Strengths": ", ".join(analysis.key_strengths),
            "Key Weaknesses": ", ".join(analysis.key_weaknesses),
            "Renault Brand Sentiment": analysis.renault_brand_sentiment,
            "Competitor Mentions": ", ".join([c.competitor for c in analysis.competitor_mentions]),
            "Comparison Summary": " | ".join([c.comparison_summary for c in analysis.competitor_mentions]),
            "Trends": ", ".join(analysis.trends),
            "Battery Performance": analysis.battery_performance,
            "Noise Levels": analysis.noise_levels,
            "Competitor Perception": analysis.competitor_perception,
            "Chinese Brand Mentions": analysis.chinese_brand_mentions,
            "Final Verdict": analysis.final_verdict
        }
        rows.append(row)
    
    return pd.DataFrame(rows)
