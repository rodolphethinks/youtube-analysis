"""
YouTube Data API module for fetching video information and comments.
Handles all YouTube API interactions with proper error handling and rate limiting.
"""

import re
import time
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

if TYPE_CHECKING:
    from .config import CarModel, PipelineConfig


@dataclass
class VideoInfo:
    """Data class for video information."""
    video_id: str
    url: str
    title: str
    release_date: str
    channel_id: str
    channel_title: str
    views: int
    likes: int
    comments: int
    duration: str
    duration_formatted: str = ""
    
    def __post_init__(self):
        if not self.duration_formatted:
            self.duration_formatted = self._convert_duration(self.duration)
    
    @staticmethod
    def _convert_duration(duration: str) -> str:
        """Convert ISO 8601 duration to HH:MM:SS format."""
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return "00:00:00"
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        return f'{hours:02}:{minutes:02}:{seconds:02}'


@dataclass
class Comment:
    """Data class for video comments."""
    video_id: str
    author: str
    text: str
    likes: int
    published_at: str


class YouTubeClient:
    """Client for interacting with YouTube Data API."""
    
    def __init__(self, api_key: str):
        """Initialize YouTube client with API key."""
        self.api_key = api_key
        self._youtube = None
    
    @property
    def youtube(self):
        """Lazy initialization of YouTube API client."""
        if self._youtube is None:
            self._youtube = build("youtube", "v3", developerKey=self.api_key)
        return self._youtube
    
    def search_videos(
        self, 
        query: str, 
        max_results: int = 50, 
        published_after: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Search for videos matching query.
        
        Returns:
            Dictionary mapping video URLs to video IDs.
        """
        try:
            request = self.youtube.search().list(
                part="snippet",
                maxResults=max_results,
                q=query,
                type="video",
                publishedAfter=published_after,
            )
            response = request.execute()
            
            return {
                f"https://www.youtube.com/watch?v={item['id']['videoId']}": item['id']['videoId'] 
                for item in response.get('items', [])
            }
        except HttpError as e:
            print(f"Error searching for '{query}': {e}")
            return {}
    
    def get_video_details(self, video_id: str) -> Optional[VideoInfo]:
        """Fetch detailed information for a single video."""
        try:
            request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                return None
            
            video_info = response['items'][0]
            snippet = video_info['snippet']
            stats = video_info['statistics']
            content = video_info['contentDetails']
            
            return VideoInfo(
                video_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                title=snippet['title'],
                release_date=pd.to_datetime(snippet['publishedAt']).strftime('%Y-%m-%d %H:%M:%S'),
                channel_id=snippet.get('channelId', 'N/A'),
                channel_title=snippet.get('channelTitle', 'N/A'),
                views=int(stats.get('viewCount', 0)),
                likes=int(stats.get('likeCount', 0)),
                comments=int(stats.get('commentCount', 0)),
                duration=content.get('duration', 'PT0S'),
            )
        except HttpError as e:
            print(f"Error fetching details for video {video_id}: {e}")
            return None
    
    def get_video_comments(
        self, 
        video_id: str, 
        max_comments: int = 100
    ) -> List[Comment]:
        """Fetch top comments for a video."""
        comments = []
        
        try:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_comments, 100),
                order="relevance",
                textFormat="plainText"
            )
            response = request.execute()
            
            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append(Comment(
                    video_id=video_id,
                    author=snippet["authorDisplayName"],
                    text=snippet["textDisplay"],
                    likes=snippet["likeCount"],
                    published_at=pd.to_datetime(snippet["publishedAt"]).strftime('%Y-%m-%d %H:%M')
                ))
                
        except HttpError as e:
            print(f"Error fetching comments for video {video_id}: {e}")
        
        return comments


class VideoDiscovery:
    """Service for discovering and filtering relevant videos."""
    
    def __init__(self, youtube_client: "YouTubeClient", config: "PipelineConfig"):
        self.client = youtube_client
        self.config = config
    
    def discover_videos(self, car_model: "CarModel") -> pd.DataFrame:
        """
        Discover videos for a car model using multiple search queries.
        
        Returns:
            DataFrame with video details, filtered and sorted by relevance.
        """
        print(f"Searching for videos about {car_model.company} {car_model.model}...")
        
        # Collect unique video IDs from all search queries
        video_dict = {}
        for query in car_model.search_queries:
            results = self.client.search_videos(
                query=query,
                max_results=self.config.max_search_results,
                published_after=self.config.published_after
            )
            video_dict.update(results)
            time.sleep(0.1)  # Rate limiting
        
        print(f"Found {len(video_dict)} unique videos from search")
        
        # Fetch detailed information
        video_details = []
        for url, video_id in video_dict.items():
            details = self.client.get_video_details(video_id)
            if details:
                video_details.append({
                    'Video URL': details.url,
                    'Video ID': details.video_id,
                    'Title': details.title,
                    'Release Date': details.release_date,
                    'Channel ID': details.channel_id,
                    'Channel Title': details.channel_title,
                    'Views': details.views,
                    'Likes': details.likes,
                    'Comments': details.comments,
                    'Duration': details.duration_formatted
                })
            time.sleep(0.05)  # Rate limiting
        
        if not video_details:
            return pd.DataFrame()
        
        df = pd.DataFrame(video_details)
        
        # Filter by title relevance
        keywords = car_model.model.split() + car_model.company.split()
        keyword_pattern = '|'.join(keywords)
        df = df[df['Title'].str.contains(keyword_pattern, case=False, na=False)]
        
        # Sort by views and reset index
        df = df.sort_values(by='Views', ascending=False).reset_index(drop=True)
        
        print(f"Total relevant videos found: {len(df)}")
        return df
    
    def fetch_all_comments(self, video_df: pd.DataFrame) -> pd.DataFrame:
        """
        Fetch comments for all videos in the DataFrame.
        
        Returns:
            DataFrame with all comments.
        """
        all_comments = []
        
        for _, row in video_df.iterrows():
            video_id = row['Video ID']
            comments = self.client.get_video_comments(
                video_id=video_id,
                max_comments=self.config.max_comments_per_video
            )
            
            for comment in comments:
                all_comments.append({
                    'Video ID': comment.video_id,
                    'Author': comment.author,
                    'Comment': comment.text,
                    'Likes': comment.likes,
                    'Published At': comment.published_at
                })
            
            time.sleep(0.1)  # Rate limiting
        
        comments_df = pd.DataFrame(all_comments)
        print(f"Total comments collected: {len(comments_df)}")
        return comments_df


def extract_video_id_from_url(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL."""
    match = re.search(r'(https?://www\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(2)
    return None
