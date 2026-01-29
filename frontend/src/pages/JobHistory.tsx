import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Video,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Trash2,
  ArrowRight,
  Search,
  Filter,
  Eye,
  ExternalLink,
  MoreHorizontal,
} from 'lucide-react';
import { api, Job } from '../api';

function StatusBadge({ status }: { status: Job['status'] }) {
  const config: Record<Job['status'], { bg: string; text: string; dot: string }> = {
    pending: { bg: 'bg-amber-50', text: 'text-amber-600', dot: 'bg-amber-400' },
    running: { bg: 'bg-blue-50', text: 'text-blue-600', dot: 'bg-blue-400 animate-pulse' },
    completed: { bg: 'bg-emerald-50', text: 'text-emerald-600', dot: 'bg-emerald-400' },
    failed: { bg: 'bg-red-50', text: 'text-red-600', dot: 'bg-red-400' },
  };

  const { bg, text, dot } = config[status];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${bg} ${text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`}></span>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export default function JobHistory() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadJobs = async () => {
    try {
      const data = await api.getJobs();
      setJobs(data);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (jobId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this analysis?')) return;
    
    try {
      await api.deleteJob(jobId);
      setJobs(jobs.filter((j) => j.id !== jobId));
    } catch (error) {
      console.error('Failed to delete job:', error);
    }
  };

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.car_company.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.car_model.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || job.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">History</h1>
          <p className="text-gray-500 mt-1">View and manage your past analyses</p>
        </div>
        <Link
          to="/new"
          className="inline-flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl font-medium shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 transition-all active:scale-[0.98]"
        >
          New Analysis
          <ArrowRight size={16} />
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-sm p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              type="text"
              placeholder="Search by car model or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-11 pr-4 py-3 bg-gray-50 border-0 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:bg-white transition-all"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter size={18} className="text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-3 bg-gray-50 border-0 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:bg-white transition-all text-sm"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="running">Running</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Jobs List */}
      {loading ? (
        <div className="bg-white rounded-2xl shadow-sm p-12 text-center">
          <Loader2 className="w-10 h-10 animate-spin text-primary-400 mx-auto" />
          <p className="text-gray-500 mt-4">Loading history...</p>
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm p-12 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Video className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-900 font-medium">
            {searchQuery || statusFilter !== 'all'
              ? 'No analyses match your filters'
              : 'No analyses yet'}
          </p>
          <p className="text-gray-500 text-sm mt-1">
            {searchQuery || statusFilter !== 'all'
              ? 'Try adjusting your search or filters'
              : 'Start your first analysis to see it here'}
          </p>
          {!searchQuery && statusFilter === 'all' && (
            <Link
              to="/new"
              className="inline-flex items-center gap-2 mt-6 px-5 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl font-medium shadow-lg shadow-primary-500/25 hover:shadow-xl transition-all"
            >
              Start your first analysis
              <ArrowRight size={16} />
            </Link>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
          <div className="divide-y divide-gray-100">
            {filteredJobs.map((job) => (
              <Link
                key={job.id}
                to={`/job/${job.id}`}
                className="flex items-center gap-4 p-5 hover:bg-gray-50 transition-all group"
              >
                {/* Avatar */}
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold text-lg shrink-0">
                  {job.car_company.charAt(0)}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900 truncate group-hover:text-primary-600 transition-colors">
                      {job.car_company} {job.car_model}
                    </p>
                    <ExternalLink size={14} className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {new Date(job.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>

                {/* Status */}
                <div className="hidden md:block">
                  <StatusBadge status={job.status} />
                </div>

                {/* Videos */}
                <div className="hidden lg:flex items-center gap-2 text-sm text-gray-500 shrink-0">
                  <Eye size={16} />
                  <span className="font-medium">{job.videos_found}</span>
                  <span>videos</span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={(e) => handleDelete(job.id, e)}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
