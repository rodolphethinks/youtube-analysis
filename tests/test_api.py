"""
Tests for the FastAPI backend API.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def client():
    """Create test client with mocked database."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_api_key"}):
        from backend.app import app
        return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns ok status."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data


class TestModelsEndpoint:
    """Tests for predefined models endpoint."""
    
    def test_get_models(self, client):
        """Test getting predefined models."""
        response = client.get("/api/models")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have predefined models
        assert "scenic" in data
        assert "koleos" in data
        
        # Each model should have company and model fields
        assert "company" in data["scenic"]
        assert "model" in data["scenic"]


class TestAnalyzeEndpoints:
    """Tests for analyze endpoints."""
    
    def test_analyze_predefined_invalid_model(self, client):
        """Test analyzing with invalid predefined model."""
        response = client.post("/api/analyze/predefined", json={
            "model_key": "nonexistent_model",
            "skip_transcription": True,
            "max_videos": 10
        })
        
        assert response.status_code == 400
        assert "Unknown model" in response.json()["detail"]
    
    @patch('backend.app.run_analysis_job')
    def test_analyze_predefined_valid_model(self, mock_job, client):
        """Test analyzing with valid predefined model."""
        response = client.post("/api/analyze/predefined", json={
            "model_key": "scenic",
            "skip_transcription": True,
            "max_videos": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["status"] == "pending"
        assert data["car_company"] == "르노"
    
    @patch('backend.app.run_analysis_job')
    def test_analyze_custom_model(self, mock_job, client):
        """Test analyzing with custom model."""
        response = client.post("/api/analyze/custom", json={
            "company": "Toyota",
            "model": "RAV4",
            "search_queries": ["Toyota RAV4 review"],
            "skip_transcription": True,
            "max_videos": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["car_company"] == "Toyota"
        assert data["car_model"] == "RAV4"
        assert data["status"] == "pending"


class TestJobsEndpoints:
    """Tests for jobs management endpoints."""
    
    @patch('backend.app.sqlite3.connect')
    def test_get_jobs_empty(self, mock_connect, client):
        """Test getting jobs when none exist."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        response = client.get("/api/jobs")
        
        assert response.status_code == 200
        assert response.json() == []
    
    @patch('backend.app.sqlite3.connect')
    def test_get_job_not_found(self, mock_connect, client):
        """Test getting non-existent job."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        response = client.get("/api/jobs/nonexistent123")
        
        assert response.status_code == 404


class TestDownloadEndpoint:
    """Tests for download endpoint."""
    
    def test_download_nonexistent_file(self, client):
        """Test downloading non-existent file."""
        response = client.get("/api/download/nonexistent_file.docx")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestInputValidation:
    """Tests for input validation."""
    
    def test_max_videos_validation(self, client):
        """Test max_videos validation."""
        # Below minimum
        response = client.post("/api/analyze/custom", json={
            "company": "Test",
            "model": "Model",
            "max_videos": 0  # Below minimum of 1
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_required_fields(self, client):
        """Test required fields validation."""
        response = client.post("/api/analyze/custom", json={
            "company": "Test"
            # Missing required 'model' field
        })
        
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
