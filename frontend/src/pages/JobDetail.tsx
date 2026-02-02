import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Download,
  Video,
  FileText,
  FileSpreadsheet,
  ThumbsUp,
  ThumbsDown,
  Minus,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { api, Job, JobResult } from '../api';

function StatusBadge({ status }: { status: Job['status'] }) {
  const config: Record<Job['status'], { bg: string; text: string; icon: any; label: string }> = {
    pending: { bg: 'bg-amber-100', text: 'text-amber-700', icon: Clock, label: 'Pending' },
    running: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Loader2, label: 'Running' },
    completed: { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: CheckCircle2, label: 'Completed' },
    failed: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle, label: 'Failed' },
  };

  const { bg, text, icon: Icon, label } = config[status];

  return (
    <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${bg} ${text}`}>
      <Icon size={16} className={status === 'running' ? 'animate-spin' : ''} />
      {label}
    </span>
  );
}

function SentimentIcon({ sentiment }: { sentiment: string }) {
  const s = sentiment.toLowerCase();
  if (s === 'positive' || s.includes('긍정')) {
    return <ThumbsUp className="text-emerald-500" size={18} />;
  } else if (s === 'negative' || s.includes('부정')) {
    return <ThumbsDown className="text-red-500" size={18} />;
  } else {
    return <Minus className="text-gray-400" size={18} />;
  }
}

export default function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [results, setResults] = useState<JobResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  useEffect(() => {
    if (job && (job.status === 'pending' || job.status === 'running')) {
      const interval = setInterval(loadData, 3000);
      return () => clearInterval(interval);
    }
  }, [job?.status]);

  const loadData = async () => {
    try {
      const [jobData, resultsData] = await Promise.all([
        api.getJob(id!),
        api.getJobResults(id!),
      ]);
      setJob(jobData);
      setResults(resultsData);
      setError(null);
    } catch (err) {
      setError('Failed to load job details');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (filename: string) => {
    window.open(api.getDownloadUrl(filename), '_blank');
  };

  const sentimentStats = results.reduce(
    (acc, r) => {
      const s = r.sentiment.toLowerCase();
      if (s === 'positive' || s.includes('긍정')) acc.positive++;
      else if (s === 'negative' || s.includes('부정')) acc.negative++;
      else acc.neutral++;
      return acc;
    },
    { positive: 0, negative: 0, neutral: 0 }
  );

  const pieData = [
    { name: 'Positive', value: sentimentStats.positive, color: '#10b981' },
    { name: 'Neutral', value: sentimentStats.neutral, color: '#9ca3af' },
    { name: 'Negative', value: sentimentStats.negative, color: '#ef4444' },
  ].filter((d) => d.value > 0);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="w-12 h-12 animate-spin text-primary-500" />
        <p className="text-gray-500 mt-4">Loading analysis details...</p>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mb-4">
          <XCircle className="w-8 h-8 text-red-500" />
        </div>
        <p className="text-gray-900 font-medium">{error || 'Job not found'}</p>
        <Link
          to="/history"
          className="mt-4 px-5 py-2.5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
        >
          Back to History
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition-colors"
        >
          <ArrowLeft size={18} />
          Back
        </button>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold text-xl">
              {job.car_company.charAt(0)}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {job.car_company} {job.car_model}
              </h1>
              <p className="text-gray-500 mt-1">
                Started {new Date(job.created_at).toLocaleString()}
              </p>
            </div>
          </div>
          <StatusBadge status={job.status} />
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-violet-100 rounded-xl">
              <Video className="w-5 h-5 text-violet-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{job.videos_found}</p>
              <p className="text-sm text-gray-500">Videos Found</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-100 rounded-xl">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{job.videos_analyzed}</p>
              <p className="text-sm text-gray-500">Analyzed</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-100 rounded-xl">
              <ThumbsUp className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{sentimentStats.positive}</p>
              <p className="text-sm text-gray-500">Positive</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-100 rounded-xl">
              <ThumbsDown className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{sentimentStats.negative}</p>
              <p className="text-sm text-gray-500">Negative</p>
            </div>
          </div>
        </div>
      </div>

      {job.error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl">
          <p className="text-red-700 text-sm">{job.error}</p>
        </div>
      )}

      {/* Running State */}
      {(job.status === 'pending' || job.status === 'running') && (
        <div className="relative overflow-hidden rounded-2xl p-8 mb-6 text-center" style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
        }}>
          <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2"></div>
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2"></div>
          
          <div className="relative z-10">
            <Loader2 className="w-12 h-12 animate-spin text-white mx-auto" />
            <h3 className="text-xl font-semibold text-white mt-4">Analysis in Progress</h3>
            {job.progress_message ? (
              <p className="text-white/90 mt-2 font-medium">
                {job.progress_message}
              </p>
            ) : (
              <p className="text-white/70 mt-2">
                Processing videos, extracting insights, and generating reports...
              </p>
            )}
            {job.videos_transcribed > 0 && (
              <div className="mt-3 bg-white/20 rounded-lg px-4 py-2 inline-block">
                <span className="text-white font-semibold">{job.videos_transcribed}</span>
                <span className="text-white/70 ml-1">videos transcribed</span>
              </div>
            )}
            <div className="flex items-center justify-center gap-2 mt-4 text-sm text-white/60">
              <RefreshCw size={14} className="animate-spin" />
              Auto-refreshing every 3 seconds
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {job.status === 'completed' && results.length > 0 && (
        <>
          {/* Charts Row */}
          <div className="grid lg:grid-cols-2 gap-6 mb-6">
            {/* Sentiment Distribution */}
            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Sentiment Distribution</h3>
              <div className="flex items-center gap-8">
                <div className="relative w-40 h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={65}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-gray-900">{results.length}</p>
                      <p className="text-xs text-gray-500">Total</p>
                    </div>
                  </div>
                </div>
                
                <div className="flex-1 space-y-3">
                  {pieData.map((item) => (
                    <div key={item.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                        <span className="text-gray-600">{item.name}</span>
                      </div>
                      <span className="font-semibold text-gray-900">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Download Reports */}
            {job.report_filename && (
              <div className="bg-white rounded-2xl p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Download Reports</h3>
                <div className="space-y-3">
                  <button
                    onClick={() => handleDownload(job.report_filename!)}
                    className="w-full flex items-center gap-4 p-4 bg-blue-50 hover:bg-blue-100 rounded-xl transition-colors group"
                  >
                    <div className="p-3 bg-blue-500 rounded-xl text-white group-hover:scale-105 transition-transform">
                      <FileText size={20} />
                    </div>
                    <div className="text-left flex-1">
                      <p className="font-medium text-gray-900">Word Report</p>
                      <p className="text-sm text-gray-500">Detailed analysis document</p>
                    </div>
                    <Download size={18} className="text-gray-400" />
                  </button>
                  
                  <button
                    onClick={() => handleDownload(job.report_filename!.replace('.docx', '.csv'))}
                    className="w-full flex items-center gap-4 p-4 bg-emerald-50 hover:bg-emerald-100 rounded-xl transition-colors group"
                  >
                    <div className="p-3 bg-emerald-500 rounded-xl text-white group-hover:scale-105 transition-transform">
                      <FileSpreadsheet size={20} />
                    </div>
                    <div className="text-left flex-1">
                      <p className="font-medium text-gray-900">CSV Data</p>
                      <p className="text-sm text-gray-500">Raw data for analysis</p>
                    </div>
                    <Download size={18} className="text-gray-400" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Results Table */}
          <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">Video Analysis Results</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {results.map((result) => (
                <div key={result.id} className="p-5 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-400 to-red-600 flex items-center justify-center text-white shrink-0">
                      <Video size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <h4 className="font-medium text-gray-900 line-clamp-1">{result.video_title}</h4>
                          <p className="text-sm text-gray-500 mt-0.5">{result.channel_name}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <SentimentIcon sentiment={result.sentiment} />
                          <span className="text-sm font-medium capitalize">{result.sentiment}</span>
                        </div>
                      </div>
                      
                      {(result.strengths || result.weaknesses) && (
                        <div className="mt-3 grid md:grid-cols-2 gap-3">
                          {result.strengths && (
                            <div className="p-3 bg-emerald-50 rounded-xl">
                              <p className="text-xs font-medium text-emerald-700 mb-1">Strengths</p>
                              <p className="text-sm text-emerald-900 line-clamp-2">{result.strengths}</p>
                            </div>
                          )}
                          {result.weaknesses && (
                            <div className="p-3 bg-red-50 rounded-xl">
                              <p className="text-xs font-medium text-red-700 mb-1">Weaknesses</p>
                              <p className="text-sm text-red-900 line-clamp-2">{result.weaknesses}</p>
                            </div>
                          )}
                        </div>
                      )}
                      
                      <div className="mt-3">
                        <a
                          href={`https://youtube.com/watch?v=${result.video_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 font-medium"
                        >
                          Watch on YouTube
                          <ExternalLink size={14} />
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* No Results */}
      {job.status === 'completed' && results.length === 0 && (
        <div className="bg-white rounded-2xl shadow-sm p-12 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Video className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-900 font-medium">No analysis results available</p>
          <p className="text-gray-500 text-sm mt-1">The analysis completed but no results were generated</p>
        </div>
      )}
    </div>
  );
}
