"""
Tests for the analysis module.
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analysis import (
    Sentiment, VideoAnalysis, CommentAnalysis, UserPersona,
    CompetitorMention, GeminiClient, VideoAnalyzer, CommentAnalyzer,
    analysis_to_dataframe
)
from src.config import CarModel


class TestSentiment:
    """Tests for Sentiment enum."""
    
    def test_sentiment_values(self):
        """Test sentiment enum values."""
        assert Sentiment.POSITIVE.value == "Positive"
        assert Sentiment.NEUTRAL.value == "Neutral"
        assert Sentiment.NEGATIVE.value == "Negative"


class TestVideoAnalysis:
    """Tests for VideoAnalysis dataclass."""
    
    def test_video_analysis_creation(self):
        """Test VideoAnalysis creation."""
        analysis = VideoAnalysis(
            video_url="https://youtube.com/watch?v=test",
            overall_sentiment="Positive",
            sentiment_score=85,
            key_strengths=["Good design", "Fuel efficiency"],
            key_weaknesses=["High price"],
            brand_sentiment="Positive",
            renault_brand_sentiment="Not mentioned",
            competitor_mentions=[],
            trends=["EV trend"],
            battery_performance="Good",
            noise_levels="Quiet",
            competitor_perception="Hyundai Tucson",
            chinese_brand_mentions="None",
            final_verdict="Great car overall"
        )
        
        assert analysis.overall_sentiment == "Positive"
        assert analysis.sentiment_score == 85
        assert len(analysis.key_strengths) == 2
        assert analysis.brand_sentiment == "Positive"
        assert analysis.renault_brand_sentiment == "Not mentioned"


class TestCompetitorMention:
    """Tests for CompetitorMention dataclass."""
    
    def test_competitor_mention_creation(self):
        """Test CompetitorMention creation."""
        mention = CompetitorMention(
            competitor="Toyota RAV4",
            comparison_summary="Better interior but higher price"
        )
        
        assert mention.competitor == "Toyota RAV4"
        assert "interior" in mention.comparison_summary


class TestUserPersona:
    """Tests for UserPersona dataclass."""
    
    def test_user_persona_creation(self):
        """Test UserPersona creation."""
        persona = UserPersona(
            name="Tech Enthusiast Tom",
            description="Male, 30-40, interested in EVs",
            age_group="30-40",
            interests=["Electric vehicles", "Technology"],
            motivations=["Staying updated"],
            pain_points=["High prices"],
            content_preferences=["Detailed reviews"]
        )
        
        assert persona.name == "Tech Enthusiast Tom"
        assert len(persona.interests) == 2


class TestGeminiClient:
    """Tests for GeminiClient."""
    
    @patch('src.analysis.genai')
    def test_client_initialization(self, mock_genai):
        """Test Gemini client initialization."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        client = GeminiClient(api_key="test_key", model_name="gemini-2.0-flash")
        
        mock_genai.configure.assert_called_once_with(api_key="test_key")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")
    
    @patch('src.analysis.genai')
    def test_generate(self, mock_genai):
        """Test text generation."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        client = GeminiClient(api_key="test_key")
        result = client.generate("Test prompt")
        
        assert result == "Generated response"


class TestVideoAnalyzer:
    """Tests for VideoAnalyzer."""
    
    def test_analyze_transcript_valid_json(self):
        """Test analyzing transcript with valid JSON response."""
        mock_client = MagicMock()
        
        # Valid JSON response from Gemini
        valid_response = json.dumps({
            "sentiment_analysis": {"overall_sentiment": "Positive", "score": 75},
            "key_strengths": ["Design", "Performance"],
            "key_weaknesses": ["Price"],
            "brand_sentiment": "Positive",
            "renault_brand_sentiment": "Neutral",
            "competitor_mentions": [
                {"competitor": "Tesla Model Y", "comparison_summary": "More affordable"}
            ],
            "trends": ["EV adoption"],
            "battery_performance": "Good range",
            "noise_levels": "Quiet at highway speeds",
            "competitor_perception": "Tesla Model Y",
            "chinese_brand_mentions": "BYD mentioned positively",
            "final_verdict": "Recommended for families"
        })
        
        mock_client.generate.return_value = valid_response
        
        analyzer = VideoAnalyzer(mock_client)
        car_model = CarModel(company="Renault", model="Scenic")
        
        result = analyzer.analyze_transcript(
            "https://youtube.com/watch?v=test",
            "This is a test transcript...",
            car_model
        )
        
        assert result.overall_sentiment == "Positive"
        assert result.sentiment_score == 75
        assert len(result.key_strengths) == 2
        assert result.brand_sentiment == "Positive"
    
    def test_analyze_transcript_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_client = MagicMock()
        
        # JSON wrapped in markdown
        response = '''```json
{
    "sentiment_analysis": {"overall_sentiment": "Neutral", "score": 50},
    "key_strengths": [],
    "key_weaknesses": [],
    "brand_sentiment": "N/A",
    "renault_brand_sentiment": "Not mentioned",
    "competitor_mentions": [],
    "trends": [],
    "battery_performance": "N/A",
    "noise_levels": "N/A",
    "competitor_perception": "N/A",
    "chinese_brand_mentions": "N/A",
    "final_verdict": "No verdict"
}
```'''
        
        mock_client.generate.return_value = response
        
        analyzer = VideoAnalyzer(mock_client)
        car_model = CarModel(company="Test", model="Model")
        
        result = analyzer.analyze_transcript(
            "https://youtube.com/watch?v=test",
            "Test transcript",
            car_model
        )
        
        # Should successfully parse even with markdown wrapper
        assert result.overall_sentiment == "Neutral"
    
    def test_analyze_transcript_invalid_json(self):
        """Test handling of invalid JSON response."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "This is not valid JSON at all!"
        
        analyzer = VideoAnalyzer(mock_client)
        car_model = CarModel(company="Test", model="Model")
        
        result = analyzer.analyze_transcript(
            "https://youtube.com/watch?v=test",
            "Test transcript",
            car_model
        )
        
        # Should return fallback values
        assert result.overall_sentiment == "N/A"
        assert result.sentiment_score == 50
        assert result.key_strengths == []
    
    def test_prompt_contains_car_model(self):
        """Test that prompt includes the car model information."""
        mock_client = MagicMock()
        mock_client.generate.return_value = json.dumps({
            "sentiment_analysis": {"overall_sentiment": "N/A", "score": 50},
            "key_strengths": [], "key_weaknesses": [],
            "brand_sentiment": "N/A", "renault_brand_sentiment": "N/A",
            "competitor_mentions": [], "trends": [],
            "battery_performance": "N/A", "noise_levels": "N/A",
            "competitor_perception": "N/A", "chinese_brand_mentions": "N/A",
            "final_verdict": "N/A"
        })
        
        analyzer = VideoAnalyzer(mock_client)
        car_model = CarModel(company="Hyundai", model="Ioniq 5")
        
        analyzer.analyze_transcript(
            "https://youtube.com/watch?v=test",
            "Test transcript",
            car_model
        )
        
        # Check that the prompt contains car model info
        call_args = mock_client.generate.call_args[0][0]
        assert "Hyundai" in call_args
        assert "Ioniq 5" in call_args


class TestCommentAnalyzer:
    """Tests for CommentAnalyzer."""
    
    def test_analyze_comments_valid_json(self):
        """Test analyzing comments with valid JSON."""
        mock_client = MagicMock()
        
        valid_response = json.dumps({
            "themes": ["Design", "Price"],
            "sentiment_breakdown": {"positive": 60, "neutral": 30, "negative": 10},
            "recurring_topics": ["Interior", "Range"],
            "keywords": ["beautiful", "expensive"],
            "personas": [{
                "name": "EV Enthusiast",
                "description": "Early adopter",
                "age_group": "25-35",
                "interests": ["EVs"],
                "motivations": ["Environment"],
                "pain_points": ["Charging"],
                "content_preferences": ["Reviews"]
            }]
        })
        
        mock_client.generate.return_value = valid_response
        
        analyzer = CommentAnalyzer(mock_client)
        car_model = CarModel(company="Test", model="Model")
        
        result = analyzer.analyze_comments(
            "https://youtube.com/watch?v=test",
            "Comment 1\nComment 2\nComment 3",
            car_model
        )
        
        assert len(result.themes) == 2
        assert result.sentiment_breakdown["positive"] == 60
        assert len(result.personas) == 1


class TestAnalysisToDataframe:
    """Tests for analysis_to_dataframe function."""
    
    def test_empty_list(self):
        """Test with empty analysis list."""
        df = analysis_to_dataframe([])
        assert len(df) == 0
    
    def test_single_analysis(self):
        """Test converting single analysis to dataframe."""
        analyses = [
            VideoAnalysis(
                video_url="https://youtube.com/watch?v=test",
                overall_sentiment="Positive",
                sentiment_score=80,
                key_strengths=["Design", "Tech"],
                key_weaknesses=["Price"],
                brand_sentiment="Positive",
                renault_brand_sentiment="Neutral",
                competitor_mentions=[
                    CompetitorMention("Tesla", "More expensive")
                ],
                trends=["EV"],
                battery_performance="Good",
                noise_levels="Quiet",
                competitor_perception="Tesla",
                chinese_brand_mentions="None",
                final_verdict="Recommended"
            )
        ]
        
        df = analysis_to_dataframe(analyses)
        
        assert len(df) == 1
        assert df.iloc[0]["Overall Sentiment"] == "Positive"
        assert df.iloc[0]["Sentiment Score"] == 80
        assert "Design" in df.iloc[0]["Key Strengths"]
        assert df.iloc[0]["Brand Sentiment"] == "Positive"
    
    def test_multiple_analyses(self):
        """Test converting multiple analyses to dataframe."""
        analyses = [
            VideoAnalysis(
                video_url=f"https://youtube.com/watch?v=test{i}",
                overall_sentiment="Positive" if i % 2 == 0 else "Negative",
                sentiment_score=70 + i * 10,
                key_strengths=[],
                key_weaknesses=[],
                brand_sentiment="N/A",
                renault_brand_sentiment="N/A",
                competitor_mentions=[],
                trends=[],
                battery_performance="N/A",
                noise_levels="N/A",
                competitor_perception="N/A",
                chinese_brand_mentions="N/A",
                final_verdict="N/A"
            )
            for i in range(3)
        ]
        
        df = analysis_to_dataframe(analyses)
        
        assert len(df) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
