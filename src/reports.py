"""
Report generation module for creating analysis outputs.
Generates Word documents, Excel files, and summary reports.
"""

import json
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from pathlib import Path
from datetime import datetime

import pandas as pd

if TYPE_CHECKING:
    from .config import CarModel, PipelineConfig
    from .analysis import VideoAnalysis, CommentAnalysis

from .analysis import GeminiClient, analysis_to_dataframe


class ReportGenerator:
    """Generate comprehensive analysis reports."""
    
    def __init__(
        self, 
        gemini_client: GeminiClient, 
        output_dir: str = "output"
    ):
        self.client = gemini_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_summary_report(
        self, 
        analysis_df: pd.DataFrame,
        car_model: "CarModel"
    ) -> str:
        """Generate a comprehensive summary report using AI."""
        columns = [
            'Overall Sentiment', 'Key Strengths', 'Key Weaknesses',
            'Competitor Mentions', 'Comparison Summary', 'Trends',
            'Battery Performance', 'Noise Levels', 'Competitor Perception',
            'Chinese Brand Mentions', 'Final Verdict'
        ]
        
        extracted_data = {
            col: analysis_df[col].dropna().tolist() 
            for col in columns if col in analysis_df.columns
        }
        
        prompt = f'''You are an expert automotive market analyst. Given the following data extracted from YouTube video reviews about the {car_model.company} {car_model.model}, provide a comprehensive analysis report.

Identify the most common themes, significant insights, and key takeaways for each aspect.

Data:
{json.dumps(extracted_data, indent=2, ensure_ascii=False)}

Provide the analysis in the following structured format:

## Executive Summary
[2-3 sentence overview of the overall reception]

## Overall Sentiment Analysis
- Distribution of positive/neutral/negative reviews
- Key drivers of sentiment

## Key Strengths
- Top mentioned positive aspects with frequency
- Analysis of what resonates with reviewers

## Key Weaknesses
- Top mentioned concerns with frequency
- Areas for improvement

## Competitive Landscape
- Main competitors mentioned
- How the {car_model.model} compares

## Market Trends
- Emerging themes in the reviews
- Consumer preferences indicated

## Technical Aspects
- Battery performance feedback
- Noise level observations
- Other technical notes

## Recommendations
- For potential buyers
- For the manufacturer

## Conclusion
[Final summary and outlook]
'''
        
        response = self.client.generate(prompt)
        return response
    
    def save_to_word(
        self, 
        report_text: str, 
        filename: str,
        car_model: "CarModel"
    ) -> Path:
        """Save report to Word document."""
        try:
            from docx import Document
            from docx.shared import Pt, Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            print("python-docx not installed. Saving as text file instead.")
            return self.save_to_text(report_text, filename.replace('.docx', '.txt'))
        
        doc = Document()
        
        # Title
        title = doc.add_heading(
            f'{car_model.company} {car_model.model} - Video Analysis Report', 
            level=0
        )
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Date
        date_para = doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()  # Spacer
        
        # Process report sections
        for section in report_text.split('\n\n'):
            section = section.strip()
            if not section:
                continue
            
            if section.startswith('## '):
                # Main heading
                doc.add_heading(section[3:], level=1)
            elif section.startswith('### '):
                # Subheading
                doc.add_heading(section[4:], level=2)
            elif section.startswith('- '):
                # Bullet points
                for line in section.split('\n'):
                    if line.strip().startswith('- '):
                        doc.add_paragraph(line.strip()[2:], style='List Bullet')
            else:
                doc.add_paragraph(section)
        
        output_path = self.output_dir / filename
        doc.save(str(output_path))
        print(f"Report saved to: {output_path}")
        return output_path
    
    def save_to_text(self, report_text: str, filename: str) -> Path:
        """Save report to text file."""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"Report saved to: {output_path}")
        return output_path
    
    def save_to_excel(
        self,
        videos_df: pd.DataFrame,
        analysis_df: pd.DataFrame,
        comments_df: Optional[pd.DataFrame] = None,
        filename: str = "analysis.xlsx",
        car_model: Optional["CarModel"] = None
    ) -> Path:
        """Save analysis data to Excel with multiple sheets."""
        output_path = self.output_dir / filename
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Merge video details with analysis
            if 'Video URL' in videos_df.columns and 'Video URL' in analysis_df.columns:
                merged_df = analysis_df.merge(
                    videos_df, 
                    on='Video URL', 
                    how='inner',
                    suffixes=('', '_video')
                )
                
                # Clean up title for Excel
                if 'Title' in merged_df.columns:
                    merged_df['Title'] = merged_df['Title'].str.replace('"', "'", regex=False)
                
                # Sort by views
                if 'Views' in merged_df.columns:
                    merged_df = merged_df.sort_values('Views', ascending=False)
                
                merged_df.to_excel(writer, sheet_name='Analysis', index=False)
            else:
                analysis_df.to_excel(writer, sheet_name='Analysis', index=False)
            
            # Video details sheet
            videos_df.to_excel(writer, sheet_name='Videos', index=False)
            
            # Comments sheet (if available)
            if comments_df is not None and not comments_df.empty:
                comments_df.to_excel(writer, sheet_name='Comments', index=False)
        
        print(f"Excel file saved to: {output_path}")
        return output_path
    
    def save_comments_csv(
        self,
        comments_df: pd.DataFrame,
        filename: str = "comments.csv"
    ) -> Path:
        """Save comments to CSV."""
        output_path = self.output_dir / filename
        comments_df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"Comments saved to: {output_path}")
        return output_path


class MultiModelReportGenerator:
    """Generate comparison reports for multiple car models."""
    
    def __init__(self, gemini_client: GeminiClient, output_dir: str = "output"):
        self.client = gemini_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_comparison_excel(
        self,
        model_analyses: Dict[str, pd.DataFrame],
        filename: str = "comparison.xlsx"
    ) -> Path:
        """Generate comparison Excel with multiple sheets."""
        output_path = self.output_dir / filename
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for model_name, df in model_analyses.items():
                sheet_name = model_name[:31]  # Excel sheet name limit
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"Comparison saved to: {output_path}")
        return output_path
    
    def generate_sentiment_comparison(
        self,
        model_analyses: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Generate sentiment comparison across models."""
        sentiment_data = []
        
        for model_name, df in model_analyses.items():
            if 'Overall Sentiment' in df.columns:
                counts = df['Overall Sentiment'].value_counts()
                sentiment_data.append({
                    'Model': model_name,
                    'Positive': counts.get('Positive', 0),
                    'Neutral': counts.get('Neutral', 0),
                    'Negative': counts.get('Negative', 0),
                    'Total': len(df)
                })
        
        return pd.DataFrame(sentiment_data)
    
    def visualize_sentiment(
        self,
        sentiment_df: pd.DataFrame,
        filename: str = "sentiment_comparison.png"
    ) -> Optional[Path]:
        """Create sentiment distribution visualization."""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError:
            print("matplotlib/seaborn not installed. Skipping visualization.")
            return None
        
        plt.figure(figsize=(12, 8))
        
        sentiment_df_plot = sentiment_df.set_index('Model')[['Positive', 'Neutral', 'Negative']]
        colors = sns.color_palette("coolwarm", 3)
        
        sentiment_df_plot.plot(kind='bar', width=0.8, color=colors, edgecolor='black')
        
        plt.title('Overall Sentiment Distribution Comparison', fontsize=16, fontweight='bold')
        plt.xlabel('Car Model', fontsize=14)
        plt.ylabel('Number of Reviews', fontsize=12)
        plt.xticks(rotation=45, ha='right', fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.legend(title='Sentiment', fontsize=10, title_fontsize=12)
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Visualization saved to: {output_path}")
        return output_path
