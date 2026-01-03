'use client';

import { useState, useEffect } from 'react';
import {
  Shield,
  Eye,
  FileText,
  AlertTriangle,
  Mic,
  Search,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  User,
  Clock,
  Activity
} from 'lucide-react';

interface AuditEntry {
  timestamp: string;
  event_type: string;
  action: string;
  patient_id?: string;
  patient_name?: string;
  status?: string;
  details?: string;
  user_id?: string;
  user_name?: string;
  ip_address?: string;
  device_type?: string;
  note_id?: string;
  note_type?: string;
  severity?: string;
  session_id?: string;
}

interface AuditStats {
  total_entries: number;
  phi_access_count: number;
  note_operations_count: number;
  safety_alerts_count: number;
  session_count: number;
  unique_patients: number;
  unique_users: number;
  entries_by_action: Record<string, number>;
  entries_by_hour: { hour: string; count: number }[];
}

const eventTypeConfig: Record<string, { label: string; icon: typeof Eye; color: string }> = {
  PHI_ACCESS: { label: 'PHI Access', icon: Eye, color: 'text-blue-600 bg-blue-100' },
  NOTE_OPERATION: { label: 'Note Operation', icon: FileText, color: 'text-purple-600 bg-purple-100' },
  SAFETY_ALERT: { label: 'Safety Alert', icon: AlertTriangle, color: 'text-red-600 bg-red-100' },
  SESSION: { label: 'Session', icon: Mic, color: 'text-green-600 bg-green-100' },
};

const actionLabels: Record<string, string> = {
  VIEW_PATIENT: 'View Patient',
  SEARCH_PATIENT: 'Search Patient',
  LOOKUP_MRN: 'Lookup MRN',
  VIEW_NOTES: 'View Notes',
  GENERATE_NOTE: 'Generate Note',
  GENERATE_DDX: 'Generate DDx',
  ANALYZE_IMAGE: 'Analyze Image',
  SAVE_NOTE: 'Save Note',
  PUSH_NOTE: 'Push to EHR',
  PUSH_VITAL: 'Push Vital',
  PUSH_ORDER: 'Push Order',
  PUSH_ALLERGY: 'Add Allergy',
  UPDATE_MEDICATION: 'Update Med',
  DISCONTINUE_MEDICATION: 'D/C Med',
  CREATE_CLAIM: 'Create Claim',
  UPDATE_CLAIM: 'Update Claim',
  SUBMIT_CLAIM: 'Submit Claim',
  VIEW_CLAIM: 'View Claim',
  VIEW_WORKLIST: 'View Worklist',
  CHECK_IN_PATIENT: 'Check In',
  START_TRANSCRIPTION: 'Start Recording',
  END_TRANSCRIPTION: 'End Recording',
  CRITICAL_ALERT: 'Critical Alert',
  DRUG_INTERACTION: 'Drug Interaction',
  SAFETY_CHECK_BLOCKED: 'Safety Block',
};

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalEntries, setTotalEntries] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  const pageSize = 25;

  useEffect(() => {
    fetchAuditLogs();
    fetchStats();
  }, [page, eventTypeFilter, actionFilter]);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (eventTypeFilter) params.append('event_type', eventTypeFilter);
      if (actionFilter) params.append('action', actionFilter);
      if (searchQuery) params.append('patient_id', searchQuery);

      const res = await fetch(`http://localhost:8002/api/v1/audit/logs?${params}`);
      if (res.ok) {
        const data = await res.json();
        setEntries(data.entries);
        setTotalEntries(data.total);
        setTotalPages(Math.ceil(data.total / pageSize));
      }
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8002/api/v1/audit/stats');
      if (res.ok) {
        setStats(await res.json());
      }
    } catch (error) {
      console.error('Failed to fetch audit stats:', error);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchAuditLogs();
  };

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleString();
  };

  const formatRelativeTime = (ts: string) => {
    const date = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Shield className="h-7 w-7 text-mdx-primary" />
            HIPAA Audit Logs
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Compliance tracking for all PHI access and clinical operations
          </p>
        </div>
        <button
          onClick={() => { fetchAuditLogs(); fetchStats(); }}
          className="flex items-center gap-2 px-4 py-2 bg-mdx-primary text-white rounded-lg hover:bg-mdx-primary/90"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <Eye className="h-8 w-8 text-blue-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">PHI Access</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.phi_access_count}</p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-purple-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Note Operations</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.note_operations_count}</p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <AlertTriangle className="h-8 w-8 text-red-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Safety Alerts</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.safety_alerts_count}</p>
              </div>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <User className="h-8 w-8 text-green-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Unique Patients</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.unique_patients}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <form onSubmit={handleSearch} className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by patient ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mdx-primary focus:border-transparent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
          />
        </form>
        <select
          value={eventTypeFilter}
          onChange={(e) => { setEventTypeFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mdx-primary focus:border-transparent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
        >
          <option value="">All Event Types</option>
          <option value="PHI_ACCESS">PHI Access</option>
          <option value="NOTE_OPERATION">Note Operations</option>
          <option value="SAFETY_ALERT">Safety Alerts</option>
          <option value="SESSION">Sessions</option>
        </select>
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mdx-primary focus:border-transparent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
        >
          <option value="">All Actions</option>
          <optgroup label="PHI Access">
            <option value="VIEW_PATIENT">View Patient</option>
            <option value="SEARCH_PATIENT">Search Patient</option>
            <option value="LOOKUP_MRN">Lookup MRN</option>
          </optgroup>
          <optgroup label="Notes">
            <option value="GENERATE_NOTE">Generate Note</option>
            <option value="SAVE_NOTE">Save Note</option>
            <option value="PUSH_NOTE">Push to EHR</option>
          </optgroup>
          <optgroup label="Safety">
            <option value="CRITICAL_ALERT">Critical Alert</option>
            <option value="DRUG_INTERACTION">Drug Interaction</option>
          </optgroup>
        </select>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Event Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Patient
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                    Loading audit logs...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    No audit log entries found
                  </td>
                </tr>
              ) : (
                entries.map((entry, idx) => {
                  const config = eventTypeConfig[entry.event_type] || {
                    label: entry.event_type,
                    icon: Activity,
                    color: 'text-gray-600 bg-gray-100'
                  };
                  const Icon = config.icon;

                  return (
                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <Clock className="h-4 w-4 text-gray-400 mr-2" />
                          <div>
                            <div className="text-sm text-gray-900 dark:text-white">
                              {formatRelativeTime(entry.timestamp)}
                            </div>
                            <div className="text-xs text-gray-500">
                              {formatTimestamp(entry.timestamp)}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
                          <Icon className="h-3 w-3 mr-1" />
                          {config.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {actionLabels[entry.action] || entry.action}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {entry.patient_id ? (
                          <div>
                            <div className="text-sm text-gray-900 dark:text-white">
                              {entry.patient_name || 'Unknown'}
                            </div>
                            <div className="text-xs text-gray-500">
                              ID: {entry.patient_id}
                            </div>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {entry.status === 'success' ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-green-600 bg-green-100">
                            Success
                          </span>
                        ) : entry.status === 'failure' ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-red-600 bg-red-100">
                            Failed
                          </span>
                        ) : (
                          <span className="text-sm text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">
                          {entry.details || entry.note_type || entry.severity || '-'}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="bg-gray-50 dark:bg-gray-900 px-4 py-3 flex items-center justify-between border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-700 dark:text-gray-300">
            Showing <span className="font-medium">{(page - 1) * pageSize + 1}</span> to{' '}
            <span className="font-medium">{Math.min(page * pageSize, totalEntries)}</span> of{' '}
            <span className="font-medium">{totalEntries}</span> entries
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
