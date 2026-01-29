import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Car,
  Search,
  Sparkles,
  Loader2,
  Video,
  Mic,
  Calendar,
  Globe,
  Subtitles,
  Info,
  Zap,
  Play,
  ChevronRight,
} from 'lucide-react';
import { api } from '../api';

interface PredefinedModel {
  company: string;
  model: string;
}

const carLogos: Record<string, string> = {
  scenic: '🚗',
  koleos: '🚙',
  torres: '🚐',
  sorento: '🚘',
  santafe: '🏎️',
};

export default function NewAnalysis() {
  const navigate = useNavigate();
  const [models, setModels] = useState<Record<string, PredefinedModel>>({});
  const [activeTab, setActiveTab] = useState<'predefined' | 'custom'>('predefined');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [customCompany, setCustomCompany] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [customQueries, setCustomQueries] = useState('');
  const [skipTranscription, setSkipTranscription] = useState(true);
  const [maxVideos, setMaxVideos] = useState(20);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [regionCode, setRegionCode] = useState('');
  const [useExistingSubtitles, setUseExistingSubtitles] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const countries = [
    { code: '', name: 'Global (All Countries)' },
    { code: 'US', name: 'United States' },
    { code: 'KR', name: 'South Korea' },
    { code: 'GB', name: 'United Kingdom' },
    { code: 'FR', name: 'France' },
    { code: 'DE', name: 'Germany' },
    { code: 'JP', name: 'Japan' },
    { code: 'CA', name: 'Canada' },
    { code: 'AU', name: 'Australia' },
  ];

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const data = await api.getModels();
      setModels(data);
      if (Object.keys(data).length > 0) {
        setSelectedModel(Object.keys(data)[0]);
      }
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let job;
      if (activeTab === 'predefined') {
        job = await api.analyzePredefined(
          selectedModel, 
          skipTranscription, 
          maxVideos,
          dateFrom || null,
          dateTo || null,
          regionCode || null,
          useExistingSubtitles
        );
      } else {
        const queries = customQueries
          ? customQueries.split('\n').filter((q) => q.trim())
          : null;
        job = await api.analyzeCustom(
          customCompany, 
          customModel, 
          queries, 
          skipTranscription, 
          maxVideos,
          dateFrom || null,
          dateTo || null,
          regionCode || null,
          useExistingSubtitles
        );
      }
      navigate(`/job/${job.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">New Analysis</h1>
        <p className="text-gray-500 mt-1">Start analyzing YouTube car review videos</p>
      </div>

      {/* Main Card */}
      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-gray-100">
          <button
            onClick={() => setActiveTab('predefined')}
            className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 text-sm font-medium transition-colors ${
              activeTab === 'predefined'
                ? 'text-primary-600 border-b-2 border-primary-500 bg-primary-50/50'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Zap size={18} />
            Quick Select
          </button>
          <button
            onClick={() => setActiveTab('custom')}
            className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 text-sm font-medium transition-colors ${
              activeTab === 'custom'
                ? 'text-primary-600 border-b-2 border-primary-500 bg-primary-50/50'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Search size={18} />
            Custom Search
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          {activeTab === 'predefined' ? (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select Car Model
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {Object.entries(models).map(([key, model]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setSelectedModel(key)}
                      className={`relative p-4 rounded-xl border-2 transition-all text-left group ${
                        selectedModel === key
                          ? 'border-primary-500 bg-primary-50 shadow-lg shadow-primary-500/10'
                          : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                      }`}
                    >
                      {selectedModel === key && (
                        <div className="absolute top-2 right-2">
                          <div className="w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          </div>
                        </div>
                      )}
                      <div className="text-2xl mb-2">{carLogos[key] || '🚗'}</div>
                      <div className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors">
                        {model.model}
                      </div>
                      <div className="text-sm text-gray-500">{model.company}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Car Company
                  </label>
                  <div className="relative">
                    <Car className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="text"
                      value={customCompany}
                      onChange={(e) => setCustomCompany(e.target.value)}
                      placeholder="e.g., 르노, 현대, 기아"
                      className="w-full pl-11 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                      required={activeTab === 'custom'}
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Car Model
                  </label>
                  <input
                    type="text"
                    value={customModel}
                    onChange={(e) => setCustomModel(e.target.value)}
                    placeholder="e.g., Scenic E-Tech"
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                    required={activeTab === 'custom'}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Custom Search Queries
                  <span className="text-gray-400 font-normal ml-1">(Optional)</span>
                </label>
                <textarea
                  value={customQueries}
                  onChange={(e) => setCustomQueries(e.target.value)}
                  placeholder="Enter one query per line, e.g.:&#10;르노 세닉 리뷰&#10;세닉 전기차 시승기"
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all resize-none"
                />
              </div>

              {/* Filters */}
              <div className="grid md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Date Range
                    <span className="text-gray-400 font-normal ml-1">(Optional)</span>
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="date"
                        value={dateFrom}
                        onChange={(e) => setDateFrom(e.target.value)}
                        className="w-full pl-9 pr-2 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 text-sm"
                      />
                    </div>
                    <div className="relative flex-1">
                      <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="date"
                        value={dateTo}
                        onChange={(e) => setDateTo(e.target.value)}
                        className="w-full pl-9 pr-2 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 text-sm"
                        min={dateFrom}
                      />
                    </div>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Country
                    <span className="text-gray-400 font-normal ml-1">(Optional)</span>
                  </label>
                  <div className="relative">
                    <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <select
                      value={regionCode}
                      onChange={(e) => setRegionCode(e.target.value)}
                      className="w-full pl-9 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all appearance-none"
                    >
                      {countries.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Options */}
          <div className="mt-8 pt-6 border-t border-gray-100">
            <h3 className="text-sm font-medium text-gray-700 mb-4 flex items-center gap-2">
              <Sparkles size={16} className="text-primary-500" />
              Analysis Options
            </h3>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                      <Video size={18} className="text-primary-500" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Max Videos</p>
                      <p className="text-xs text-gray-500">Videos to analyze</p>
                    </div>
                  </div>
                  <select
                    value={maxVideos}
                    onChange={(e) => setMaxVideos(Number(e.target.value))}
                    className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  >
                    {[5, 10, 20, 30, 50, 100, 150, 200].map((n) => (
                      <option key={n} value={n}>{n} videos</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                      <Mic size={18} className="text-violet-500" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Transcription</p>
                      <p className="text-xs text-gray-500">Audio to text</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSkipTranscription(!skipTranscription)}
                    className={`relative w-12 h-6 rounded-full transition-colors ${
                      !skipTranscription ? 'bg-primary-500' : 'bg-gray-300'
                    }`}
                  >
                    <span
                      className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform shadow ${
                        !skipTranscription ? 'translate-x-6' : ''
                      }`}
                    />
                  </button>
                </div>
              </div>

               <div className="p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                      <Subtitles size={18} className="text-blue-500" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Use Subtitles</p>
                      <p className="text-xs text-gray-500">Try YouTube captions first</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setUseExistingSubtitles(!useExistingSubtitles)}
                    className={`relative w-12 h-6 rounded-full transition-colors ${
                      useExistingSubtitles ? 'bg-primary-500' : 'bg-gray-300'
                    }`}
                  >
                    <span
                      className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform shadow ${
                        useExistingSubtitles ? 'translate-x-6' : ''
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>

            {!skipTranscription && (
              <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3">
                <Info size={18} className="text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800">Transcription Enabled</p>
                  <p className="text-xs text-amber-700 mt-1">
                    Audio transcription provides more detailed analysis but takes significantly longer.
                    This uses Whisper AI for speech-to-text.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Submit */}
          <div className="mt-6 flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Analysis typically takes 2-5 minutes
            </p>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl font-medium shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play size={18} />
                  Start Analysis
                  <ChevronRight size={16} />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
