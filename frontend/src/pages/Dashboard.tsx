import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Video,
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowRight,
  Play,
  Eye,
  MessageSquare,
  BarChart3,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { api, Job } from '../api';

const weeklyData = [
  { day: 'M', value: 30 },
  { day: 'T', value: 45 },
  { day: 'W', value: 35 },
  { day: 'T', value: 60 },
  { day: 'F', value: 48 },
  { day: 'S', value: 38 },
  { day: 'S', value: 55 },
];

function GradientStatCard({
  title,
  value,
}: {
  title: string;
  value: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl p-6 text-white" style={{
      background: 'linear-gradient(135deg, #ff6b9d 0%, #ffa07a 50%, #ffd93d 100%)'
    }}>
      <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2"></div>
      <div className="absolute bottom-0 left-1/4 w-24 h-24 bg-white/5 rounded-full translate-y-1/2"></div>
      
      <svg className="absolute bottom-0 left-0 right-0 opacity-20" viewBox="0 0 400 60" preserveAspectRatio="none">
        <path d="M0,30 Q100,60 200,30 T400,30 V60 H0 Z" fill="white"/>
      </svg>
      
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <span className="text-white/80 font-medium">{title}</span>
          <button className="p-1 hover:bg-white/10 rounded transition-colors">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <circle cx="4" cy="10" r="2"/>
              <circle cx="10" cy="10" r="2"/>
              <circle cx="16" cy="10" r="2"/>
            </svg>
          </button>
        </div>
        
        <div className="text-4xl font-bold mb-4">{value}</div>
        
        <div className="flex items-end gap-1 h-12 mb-4">
          {[40, 60, 45, 80, 55, 70, 90, 65, 85, 75].map((h, i) => (
            <div
              key={i}
              className="flex-1 bg-white/30 rounded-sm transition-all hover:bg-white/50"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
        
        <div className="flex items-center gap-6 text-sm">
          <div>
            <span className="text-white/60">Positive</span>
            <div className="font-semibold">%60</div>
          </div>
          <div>
            <span className="text-white/60">Neutral</span>
            <div className="font-semibold">%25</div>
          </div>
          <div>
            <span className="text-white/60">Negative</span>
            <div className="font-semibold">%15</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DonutStatCard({
  title,
  value,
  data,
}: {
  title: string;
  value: string;
  data: { name: string; value: number; color: string }[];
}) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <span className="text-gray-500 font-medium">{title}</span>
        <button className="p-1 hover:bg-gray-100 rounded transition-colors text-gray-400">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <circle cx="4" cy="10" r="2"/>
            <circle cx="10" cy="10" r="2"/>
            <circle cx="16" cy="10" r="2"/>
          </svg>
        </button>
      </div>
      
      <div className="text-3xl font-bold text-gray-900 mb-4">{value}</div>
      
      <div className="flex items-center gap-6">
        <div className="relative w-28 h-28">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={32}
                outerRadius={45}
                paddingAngle={2}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-400" />
          </div>
        </div>
        
        <div className="flex-1 space-y-2">
          {data.map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }}></div>
              <span className="text-sm text-gray-500">{item.name}</span>
              <span className="text-sm font-semibold text-gray-700 ml-auto">%{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MiniStatCard({
  title,
  value,
  icon: Icon,
  color,
  trend,
}: {
  title: string;
  value: string | number;
  icon: any;
  color: string;
  trend?: { value: string; up: boolean };
}) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500 mt-1">{title}</p>
        </div>
        <div className={`p-3 rounded-xl ${color}`}>
          <Icon size={20} />
        </div>
      </div>
      {trend && (
        <div className="mt-3 flex items-center gap-1">
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            trend.up ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
          }`}>
            {trend.up ? '↑' : '↓'} {trend.value}
          </span>
        </div>
      )}
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  value,
}: {
  title: string;
  subtitle?: string;
  value?: string;
}) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-gray-900">{title}</h3>
          {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
      </div>
      
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={weeklyData}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff6b9d" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#ff6b9d" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis 
              dataKey="day" 
              axisLine={false} 
              tickLine={false}
              tick={{ fill: '#9ca3af', fontSize: 12 }}
            />
            <Tooltip 
              contentStyle={{ 
                background: '#1a1a2e', 
                border: 'none', 
                borderRadius: '8px',
                color: 'white'
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#ff6b9d"
              strokeWidth={2}
              fill="url(#colorValue)"
              dot={{ fill: '#ff6b9d', strokeWidth: 0, r: 0 }}
              activeDot={{ fill: '#ff6b9d', strokeWidth: 2, stroke: 'white', r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      
      {value && (
        <div className="mt-4 flex items-center gap-3">
          <CheckCircle2 className="text-primary-500" size={18} />
          <span className="text-sm text-gray-500">Completed Analyses</span>
          <span className="ml-auto text-lg font-bold text-gray-900">{value}</span>
        </div>
      )}
    </div>
  );
}

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

function ActivityItem({ job }: { job: Job }) {
  return (
    <Link
      to={`/job/${job.id}`}
      className="flex items-center gap-4 p-4 rounded-xl hover:bg-gray-50 transition-all group"
    >
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-semibold shrink-0">
        {job.car_company.charAt(0)}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium text-gray-900 truncate group-hover:text-primary-600 transition-colors">
            {job.car_company} {job.car_model}
          </p>
          <ExternalLink size={14} className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <p className="text-sm text-gray-500 truncate">Job #{job.id}</p>
      </div>
      
      <div className="text-right shrink-0">
        <StatusBadge status={job.status} />
      </div>
      
      <div className="flex items-center gap-2 text-sm text-gray-500 shrink-0">
        <Eye size={14} />
        <span>{job.videos_found}</span>
        {job.status === 'completed' && (
          <span className="flex items-center gap-1 text-emerald-500">
            <TrendingUp size={14} />
          </span>
        )}
      </div>
    </Link>
  );
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 10000);
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

  const stats = {
    totalAnalyses: jobs.length,
    totalVideos: jobs.reduce((sum, j) => sum + (j.videos_found || 0), 0),
    completed: jobs.filter((j) => j.status === 'completed').length,
    successRate: jobs.length > 0 
      ? Math.round((jobs.filter((j) => j.status === 'completed').length / jobs.length) * 100)
      : 0,
  };

  const recentJobs = jobs.slice(0, 5);

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">YouTube video intelligence dashboard</p>
        </div>
        <Link
          to="/new"
          className="inline-flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl font-medium shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 transition-all active:scale-[0.98]"
        >
          <Play size={18} />
          New Analysis
        </Link>
      </div>

      {/* Main Stats Grid */}
      <div className="grid lg:grid-cols-3 gap-6 mb-6">
        <GradientStatCard
          title="Total Videos Analyzed"
          value={stats.totalVideos.toLocaleString()}
        />
        
        <DonutStatCard
          title="Analysis Distribution"
          value={`${stats.totalAnalyses}`}
          data={[
            { name: 'Completed', value: stats.successRate, color: '#ff6b9d' },
            { name: 'Other', value: 100 - stats.successRate, color: '#ffd93d' },
          ]}
        />
        
        <div className="grid grid-cols-2 gap-4">
          <MiniStatCard
            title="Comments"
            value="3.2k"
            icon={MessageSquare}
            color="bg-rose-100 text-rose-500"
          />
          <MiniStatCard
            title="Success Rate"
            value={`${stats.successRate}%`}
            icon={TrendingUp}
            color="bg-emerald-100 text-emerald-500"
            trend={{ value: '12%', up: true }}
          />
        </div>
      </div>

      {/* Secondary Row */}
      <div className="grid lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div className="flex items-center gap-4">
              <button className="text-sm font-medium text-gray-900 pb-2 border-b-2 border-primary-500">
                Recent Activity
              </button>
              <button className="text-sm font-medium text-gray-400 hover:text-gray-600 pb-2">
                All Jobs
              </button>
            </div>
          </div>
          
          {loading ? (
            <div className="p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400 mx-auto" />
            </div>
          ) : recentJobs.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Video className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-gray-500 mb-4">No analyses yet</p>
              <Link
                to="/new"
                className="inline-flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium"
              >
                Start your first analysis
                <ArrowRight size={16} />
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {recentJobs.map((job) => (
                <ActivityItem key={job.id} job={job} />
              ))}
            </div>
          )}
          
          {recentJobs.length > 0 && (
            <Link
              to="/history"
              className="flex items-center justify-center gap-2 p-4 text-sm font-medium text-primary-600 hover:text-primary-700 hover:bg-primary-50 transition-colors"
            >
              View All History
              <ArrowRight size={16} />
            </Link>
          )}
        </div>

        <div className="space-y-6">
          <ChartCard
            title="Weekly Stats"
            subtitle="Current Week"
            value={stats.completed.toString()}
          />
          
          <MiniStatCard
            title="Analyses Run"
            value={stats.totalAnalyses}
            icon={BarChart3}
            color="bg-violet-100 text-violet-500"
            trend={{ value: '8%', up: true }}
          />
        </div>
      </div>
    </div>
  );
}
