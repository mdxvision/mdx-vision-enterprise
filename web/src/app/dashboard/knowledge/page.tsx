'use client';

import { useState, useEffect } from 'react';
import {
  BookOpen,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Play,
  Pause,
  Trash2,
  ChevronRight,
  Filter,
  Calendar,
  FileText,
  CheckSquare,
  Square,
  ThumbsUp,
  ThumbsDown,
  Database,
  Zap,
  Settings
} from 'lucide-react';

interface PendingUpdate {
  update_id: string;
  title: string;
  source: string;
  source_url: string | null;
  pmid: string | null;
  abstract_preview: string;
  specialty: string | null;
  status: string;
  priority: string;
  discovered_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  checklist_progress: {
    total: number;
    completed: number;
    required_total: number;
    required_completed: number;
    ready_for_approval: boolean;
  };
}

interface Schedule {
  schedule_id: string;
  name: string;
  source_type: string;
  query_or_feed: string;
  specialty: string | null;
  enabled: boolean;
  frequency_hours: number;
  last_run: string | null;
  next_run: string | null;
}

interface ChecklistItem {
  item_id: string;
  update_id: string;
  description: string;
  category: string;
  required: boolean;
  completed: boolean;
  completed_by: string | null;
  completed_at: string | null;
  notes: string | null;
}

interface DashboardStats {
  total_pending: number;
  status_breakdown: Record<string, number>;
  priority_breakdown: Record<string, number>;
  specialty_breakdown: Record<string, number>;
  schedules_active: number;
  schedules_total: number;
  next_scheduled_runs: { schedule_id: string; name: string; next_run: string }[];
  recent_history: { timestamp: string; schedule_name: string; updates_found: number; status: string }[];
}

const priorityConfig: Record<string, { label: string; color: string }> = {
  critical: { label: 'Critical', color: 'text-red-600 bg-red-100' },
  high: { label: 'High', color: 'text-orange-600 bg-orange-100' },
  medium: { label: 'Medium', color: 'text-yellow-600 bg-yellow-100' },
  low: { label: 'Low', color: 'text-green-600 bg-green-100' },
};

const statusConfig: Record<string, { label: string; color: string }> = {
  pending: { label: 'Pending Review', color: 'text-blue-600 bg-blue-100' },
  approved: { label: 'Approved', color: 'text-green-600 bg-green-100' },
  ingested: { label: 'Ingested', color: 'text-purple-600 bg-purple-100' },
  rejected: { label: 'Rejected', color: 'text-red-600 bg-red-100' },
  failed: { label: 'Failed', color: 'text-gray-600 bg-gray-100' },
};

export default function KnowledgeUpdatesPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [updates, setUpdates] = useState<PendingUpdate[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'pending' | 'schedules' | 'history'>('pending');
  const [statusFilter, setStatusFilter] = useState('pending');
  const [selectedUpdate, setSelectedUpdate] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [checklistLoading, setChecklistLoading] = useState(false);
  const [reviewerName, setReviewerName] = useState('');

  useEffect(() => {
    fetchDashboard();
    fetchUpdates();
    fetchSchedules();
  }, []);

  useEffect(() => {
    fetchUpdates();
  }, [statusFilter]);

  const fetchDashboard = async () => {
    try {
      const res = await fetch('http://localhost:8002/api/v1/updates/dashboard');
      if (res.ok) {
        setStats(await res.json());
      }
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    }
  };

  const fetchUpdates = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);

      const res = await fetch(`http://localhost:8002/api/v1/updates/pending?${params}`);
      if (res.ok) {
        const data = await res.json();
        setUpdates(data.updates);
      }
    } catch (error) {
      console.error('Failed to fetch updates:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSchedules = async () => {
    try {
      const res = await fetch('http://localhost:8002/api/v1/updates/schedules');
      if (res.ok) {
        const data = await res.json();
        setSchedules(data.schedules);
      }
    } catch (error) {
      console.error('Failed to fetch schedules:', error);
    }
  };

  const fetchChecklist = async (updateId: string) => {
    setChecklistLoading(true);
    try {
      const res = await fetch(`http://localhost:8002/api/v1/updates/checklist/${updateId}`);
      if (res.ok) {
        const data = await res.json();
        setChecklist(data.checklist);
      }
    } catch (error) {
      console.error('Failed to fetch checklist:', error);
    } finally {
      setChecklistLoading(false);
    }
  };

  const selectUpdate = (updateId: string) => {
    setSelectedUpdate(updateId);
    fetchChecklist(updateId);
  };

  const toggleChecklistItem = async (itemId: string, completed: boolean) => {
    if (!selectedUpdate || !reviewerName) {
      alert('Please enter your name as reviewer');
      return;
    }

    try {
      const endpoint = completed
        ? `http://localhost:8002/api/v1/updates/checklist/${selectedUpdate}/${itemId}/uncomplete`
        : `http://localhost:8002/api/v1/updates/checklist/${selectedUpdate}/${itemId}/complete`;

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed_by: reviewerName }),
      });

      if (res.ok) {
        fetchChecklist(selectedUpdate);
        fetchUpdates();
      }
    } catch (error) {
      console.error('Failed to toggle checklist item:', error);
    }
  };

  const approveUpdate = async (updateId: string) => {
    if (!reviewerName) {
      alert('Please enter your name as reviewer');
      return;
    }

    try {
      const res = await fetch(`http://localhost:8002/api/v1/updates/${updateId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewed_by: reviewerName }),
      });

      if (res.ok) {
        fetchUpdates();
        fetchDashboard();
        setSelectedUpdate(null);
      } else {
        const data = await res.json();
        alert(data.detail || 'Failed to approve');
      }
    } catch (error) {
      console.error('Failed to approve update:', error);
    }
  };

  const rejectUpdate = async (updateId: string) => {
    if (!reviewerName) {
      alert('Please enter your name as reviewer');
      return;
    }

    const notes = prompt('Rejection reason:');
    if (!notes) return;

    try {
      const res = await fetch(`http://localhost:8002/api/v1/updates/${updateId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewed_by: reviewerName, review_notes: notes }),
      });

      if (res.ok) {
        fetchUpdates();
        fetchDashboard();
        setSelectedUpdate(null);
      }
    } catch (error) {
      console.error('Failed to reject update:', error);
    }
  };

  const ingestUpdate = async (updateId: string) => {
    try {
      const res = await fetch(`http://localhost:8002/api/v1/updates/${updateId}/ingest`, {
        method: 'POST',
      });

      if (res.ok) {
        fetchUpdates();
        fetchDashboard();
        alert('Update ingested successfully!');
      } else {
        const data = await res.json();
        alert(data.detail || 'Failed to ingest');
      }
    } catch (error) {
      console.error('Failed to ingest update:', error);
    }
  };

  const runSchedule = async (scheduleId: string) => {
    try {
      const res = await fetch(`http://localhost:8002/api/v1/updates/schedules/${scheduleId}/run`, {
        method: 'POST',
      });

      if (res.ok) {
        const data = await res.json();
        alert(`Found ${data.updates_found} new updates`);
        fetchUpdates();
        fetchDashboard();
        fetchSchedules();
      }
    } catch (error) {
      console.error('Failed to run schedule:', error);
    }
  };

  const toggleSchedule = async (scheduleId: string, enabled: boolean) => {
    try {
      const res = await fetch(`http://localhost:8002/api/v1/updates/schedules/${scheduleId}/toggle?enabled=${!enabled}`, {
        method: 'POST',
      });

      if (res.ok) {
        fetchSchedules();
      }
    } catch (error) {
      console.error('Failed to toggle schedule:', error);
    }
  };

  const runDueSchedules = async () => {
    try {
      const res = await fetch('http://localhost:8002/api/v1/updates/run-due', {
        method: 'POST',
      });

      if (res.ok) {
        const data = await res.json();
        alert(`Ran ${data.schedules_run} schedules`);
        fetchUpdates();
        fetchDashboard();
        fetchSchedules();
      }
    } catch (error) {
      console.error('Failed to run due schedules:', error);
    }
  };

  const ingestAllApproved = async () => {
    try {
      const res = await fetch('http://localhost:8002/api/v1/updates/ingest-all-approved', {
        method: 'POST',
      });

      if (res.ok) {
        const data = await res.json();
        alert(`Ingested ${data.processed} updates`);
        fetchUpdates();
        fetchDashboard();
      }
    } catch (error) {
      console.error('Failed to ingest all approved:', error);
    }
  };

  const formatRelativeTime = (ts: string) => {
    const date = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (diff < 0) {
      const futureMins = Math.abs(Math.floor(diff / 60000));
      const futureHours = Math.abs(Math.floor(diff / 3600000));
      if (futureMins < 60) return `in ${futureMins}m`;
      return `in ${futureHours}h`;
    }

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  const selectedUpdateData = updates.find(u => u.update_id === selectedUpdate);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BookOpen className="h-7 w-7 text-mdx-primary" />
            Knowledge Base Updates
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage scheduled updates and review pending guidelines
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={runDueSchedules}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            <Zap className="h-4 w-4" />
            Run Due Schedules
          </button>
          <button
            onClick={() => { fetchDashboard(); fetchUpdates(); fetchSchedules(); }}
            className="flex items-center gap-2 px-4 py-2 bg-mdx-primary text-white rounded-lg hover:bg-mdx-primary/90"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-blue-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Pending Review</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.status_breakdown.pending || 0}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <CheckCircle className="h-8 w-8 text-green-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Approved</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.status_breakdown.approved || 0}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <Database className="h-8 w-8 text-purple-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Ingested</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.status_breakdown.ingested || 0}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <Clock className="h-8 w-8 text-orange-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Active Schedules</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.schedules_active} / {stats.schedules_total}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reviewer Name Input */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Reviewer Name (required for checklist actions)
        </label>
        <input
          type="text"
          placeholder="Dr. Smith"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
          className="w-full max-w-xs px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mdx-primary focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-6">
          <button
            onClick={() => setActiveTab('pending')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'pending'
                ? 'border-mdx-primary text-mdx-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Pending Updates ({stats?.status_breakdown.pending || 0})
          </button>
          <button
            onClick={() => setActiveTab('schedules')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'schedules'
                ? 'border-mdx-primary text-mdx-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Schedules ({schedules.length})
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'history'
                ? 'border-mdx-primary text-mdx-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Run History
          </button>
        </nav>
      </div>

      {/* Pending Updates Tab */}
      {activeTab === 'pending' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Updates List */}
          <div className="space-y-4">
            <div className="flex gap-4 items-center">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mdx-primary dark:bg-gray-800 dark:border-gray-700 dark:text-white"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="ingested">Ingested</option>
                <option value="rejected">Rejected</option>
              </select>
              {statusFilter === 'approved' && (
                <button
                  onClick={ingestAllApproved}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm"
                >
                  Ingest All Approved
                </button>
              )}
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 divide-y divide-gray-200 dark:divide-gray-700">
              {loading ? (
                <div className="p-8 text-center text-gray-500">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                  Loading updates...
                </div>
              ) : updates.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  No updates found
                </div>
              ) : (
                updates.map((update) => (
                  <div
                    key={update.update_id}
                    onClick={() => selectUpdate(update.update_id)}
                    className={`p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                      selectedUpdate === update.update_id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {update.title}
                        </h3>
                        <p className="text-xs text-gray-500 mt-1">
                          {update.source} {update.pmid && `• PMID: ${update.pmid}`}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1 ml-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${priorityConfig[update.priority]?.color || 'text-gray-600 bg-gray-100'}`}>
                          {priorityConfig[update.priority]?.label || update.priority}
                        </span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusConfig[update.status]?.color || 'text-gray-600 bg-gray-100'}`}>
                          {statusConfig[update.status]?.label || update.status}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatRelativeTime(update.discovered_at)}
                      </span>
                      <span className="flex items-center gap-1">
                        <CheckSquare className="h-3 w-3" />
                        {update.checklist_progress.required_completed}/{update.checklist_progress.required_total} required
                      </span>
                      {update.checklist_progress.ready_for_approval && (
                        <span className="text-green-600 font-medium">Ready for approval</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Checklist Panel */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            {selectedUpdate && selectedUpdateData ? (
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                <div className="p-4">
                  <h3 className="font-medium text-gray-900 dark:text-white">
                    {selectedUpdateData.title}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {selectedUpdateData.abstract_preview}
                  </p>
                  {selectedUpdateData.source_url && (
                    <a
                      href={selectedUpdateData.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-mdx-primary hover:underline mt-2 inline-block"
                    >
                      View source
                    </a>
                  )}
                </div>

                <div className="p-4">
                  <h4 className="font-medium text-gray-900 dark:text-white mb-3">
                    Review Checklist
                  </h4>
                  {checklistLoading ? (
                    <div className="text-center py-4">
                      <RefreshCw className="h-5 w-5 animate-spin mx-auto" />
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {checklist.map((item) => (
                        <div
                          key={item.item_id}
                          onClick={() => toggleChecklistItem(item.item_id, item.completed)}
                          className={`flex items-start gap-3 p-2 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                            item.completed ? 'bg-green-50 dark:bg-green-900/20' : ''
                          }`}
                        >
                          {item.completed ? (
                            <CheckSquare className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                          ) : (
                            <Square className="h-5 w-5 text-gray-400 flex-shrink-0 mt-0.5" />
                          )}
                          <div className="flex-1">
                            <p className={`text-sm ${item.completed ? 'text-green-700 dark:text-green-400' : 'text-gray-700 dark:text-gray-300'}`}>
                              {item.description}
                              {item.required && <span className="text-red-500 ml-1">*</span>}
                            </p>
                            {item.completed && item.completed_by && (
                              <p className="text-xs text-gray-500 mt-0.5">
                                by {item.completed_by}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="p-4 flex gap-2">
                  {selectedUpdateData.status === 'pending' && (
                    <>
                      <button
                        onClick={() => approveUpdate(selectedUpdate)}
                        disabled={!selectedUpdateData.checklist_progress.ready_for_approval}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ThumbsUp className="h-4 w-4" />
                        Approve
                      </button>
                      <button
                        onClick={() => rejectUpdate(selectedUpdate)}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                      >
                        <ThumbsDown className="h-4 w-4" />
                        Reject
                      </button>
                    </>
                  )}
                  {selectedUpdateData.status === 'approved' && (
                    <button
                      onClick={() => ingestUpdate(selectedUpdate)}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                    >
                      <Database className="h-4 w-4" />
                      Ingest Now
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-gray-500">
                <CheckSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Select an update to view its checklist</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Schedules Tab */}
      {activeTab === 'schedules' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Schedule</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Frequency</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Run</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Next Run</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {schedules.map((schedule) => (
                  <tr key={schedule.schedule_id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {schedule.name}
                      </div>
                      {schedule.specialty && (
                        <div className="text-xs text-gray-500">{schedule.specialty}</div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 dark:text-white">{schedule.source_type}</div>
                      <div className="text-xs text-gray-500 truncate max-w-xs">{schedule.query_or_feed}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                      Every {schedule.frequency_hours}h
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {schedule.last_run ? formatRelativeTime(schedule.last_run) : 'Never'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {schedule.next_run ? formatRelativeTime(schedule.next_run) : '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        schedule.enabled ? 'text-green-600 bg-green-100' : 'text-gray-600 bg-gray-100'
                      }`}>
                        {schedule.enabled ? 'Active' : 'Paused'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => runSchedule(schedule.schedule_id)}
                          className="p-1 text-blue-600 hover:bg-blue-100 rounded"
                          title="Run now"
                        >
                          <Play className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => toggleSchedule(schedule.schedule_id, schedule.enabled)}
                          className={`p-1 rounded ${schedule.enabled ? 'text-orange-600 hover:bg-orange-100' : 'text-green-600 hover:bg-green-100'}`}
                          title={schedule.enabled ? 'Pause' : 'Resume'}
                        >
                          {schedule.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && stats && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Schedule</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Updates Found</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {stats.recent_history.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                      No run history yet
                    </td>
                  </tr>
                ) : (
                  stats.recent_history.slice().reverse().map((entry, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                        {formatRelativeTime(entry.timestamp)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                        {entry.schedule_name}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                        {entry.updates_found}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          entry.status === 'success' ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100'
                        }`}>
                          {entry.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
