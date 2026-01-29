import axios from 'axios';

const API_BASE = '/api';

export interface Job {
  id: string;
  car_company: string;
  car_model: string;
  search_query: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at: string | null;
  videos_found: number;
  comments_collected: number;
  videos_analyzed: number;
  error: string | null;
  report_filename: string | null;
}

export interface JobResult {
  id: number;
  job_id: string;
  video_id: string;
  video_title: string;
  channel_name: string;
  sentiment: string;
  strengths: string;
  weaknesses: string;
  summary: string;
}

export interface AnalysisResult {
  video_url: string;
  title: string;
  channel: string;
  views: number;
  sentiment: string;
  sentiment_score: number;
  strengths: string[];
  weaknesses: string[];
  competitors: string[];
  verdict: string;
}

export interface PredefinedModel {
  company: string;
  model: string;
}

export const api = {
  // Get predefined models
  getModels: async (): Promise<Record<string, PredefinedModel>> => {
    const res = await axios.get(`${API_BASE}/models`);
    return res.data;
  },

  // Start analysis with predefined model
  analyzePredefined: async (
    modelKey: string,
    skipTranscription: boolean = true,
    maxVideos: number = 20
  ): Promise<Job> => {
    const res = await axios.post(`${API_BASE}/analyze/predefined`, {
      model_key: modelKey,
      skip_transcription: skipTranscription,
      max_videos: maxVideos,
    });
    return res.data;
  },

  // Start analysis with custom model
  analyzeCustom: async (
    company: string,
    model: string,
    queries: string[] | null,
    skipTranscription: boolean = true,
    maxVideos: number = 20
  ): Promise<Job> => {
    const res = await axios.post(`${API_BASE}/analyze/custom`, {
      company,
      model,
      search_queries: queries,
      skip_transcription: skipTranscription,
      max_videos: maxVideos,
    });
    return res.data;
  },

  // Get all jobs
  getJobs: async (): Promise<Job[]> => {
    const res = await axios.get(`${API_BASE}/jobs`);
    return res.data;
  },

  // Get single job
  getJob: async (jobId: string): Promise<Job> => {
    const res = await axios.get(`${API_BASE}/jobs/${jobId}`);
    return res.data;
  },

  // Get job results
  getJobResults: async (jobId: string): Promise<AnalysisResult[]> => {
    const res = await axios.get(`${API_BASE}/jobs/${jobId}/results`);
    return res.data;
  },

  // Delete job
  deleteJob: async (jobId: string): Promise<void> => {
    await axios.delete(`${API_BASE}/jobs/${jobId}`);
  },

  // Get download URL
  getDownloadUrl: (filename: string): string => {
    return `${API_BASE}/download/${filename}`;
  },
};
