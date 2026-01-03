'use client';

import { useState } from 'react';
import {
  Stethoscope,
  Clock,
  User,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Play,
  Pause,
  Search
} from 'lucide-react';

interface Encounter {
  id: string;
  patientName: string;
  patientId: string;
  chiefComplaint: string;
  status: 'in_progress' | 'completed' | 'pending_note' | 'cancelled';
  startTime: string;
  duration?: string;
  provider: string;
  room?: string;
  noteStatus: 'draft' | 'signed' | 'none';
}

const mockEncounters: Encounter[] = [
  {
    id: 'enc-001',
    patientName: 'John Smith',
    patientId: '12724066',
    chiefComplaint: 'Chest pain, shortness of breath',
    status: 'in_progress',
    startTime: '09:15 AM',
    duration: '32 min',
    provider: 'Dr. Rodriguez',
    room: 'Room 3',
    noteStatus: 'draft'
  },
  {
    id: 'enc-002',
    patientName: 'Mary Johnson',
    patientId: '12724067',
    chiefComplaint: 'Follow-up for diabetes management',
    status: 'completed',
    startTime: '08:30 AM',
    duration: '25 min',
    provider: 'Dr. Rodriguez',
    room: 'Room 1',
    noteStatus: 'signed'
  },
  {
    id: 'enc-003',
    patientName: 'Robert Williams',
    patientId: '12724068',
    chiefComplaint: 'Hypertension check',
    status: 'pending_note',
    startTime: '10:00 AM',
    duration: '18 min',
    provider: 'Dr. Rodriguez',
    room: 'Room 2',
    noteStatus: 'draft'
  },
  {
    id: 'enc-004',
    patientName: 'Sarah Davis',
    patientId: '12724069',
    chiefComplaint: 'Annual physical',
    status: 'completed',
    startTime: '07:45 AM',
    duration: '45 min',
    provider: 'Dr. Rodriguez',
    room: 'Room 1',
    noteStatus: 'signed'
  },
];

const statusConfig = {
  in_progress: { label: 'In Progress', icon: Play, color: 'text-blue-600 bg-blue-100' },
  completed: { label: 'Completed', icon: CheckCircle, color: 'text-green-600 bg-green-100' },
  pending_note: { label: 'Pending Note', icon: AlertCircle, color: 'text-yellow-600 bg-yellow-100' },
  cancelled: { label: 'Cancelled', icon: XCircle, color: 'text-red-600 bg-red-100' },
};

export default function EncountersPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredEncounters = mockEncounters.filter(enc => {
    const matchesSearch = enc.patientName.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         enc.chiefComplaint.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || enc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const stats = {
    total: mockEncounters.length,
    inProgress: mockEncounters.filter(e => e.status === 'in_progress').length,
    pendingNotes: mockEncounters.filter(e => e.status === 'pending_note').length,
    completed: mockEncounters.filter(e => e.status === 'completed').length,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Encounters
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage patient encounters and documentation
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <Stethoscope className="h-8 w-8 text-mdx-primary" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Today's Encounters</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <Play className="h-8 w-8 text-blue-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">In Progress</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.inProgress}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <AlertCircle className="h-8 w-8 text-yellow-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Pending Notes</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.pendingNotes}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <CheckCircle className="h-8 w-8 text-green-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Completed</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.completed}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by patient or complaint..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mdx-primary focus:border-transparent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mdx-primary focus:border-transparent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
        >
          <option value="all">All Status</option>
          <option value="in_progress">In Progress</option>
          <option value="pending_note">Pending Note</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Encounters List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Patient
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Chief Complaint
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Room
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Note
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {filteredEncounters.map((encounter) => {
                const status = statusConfig[encounter.status];
                const StatusIcon = status.icon;
                return (
                  <tr key={encounter.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="h-10 w-10 rounded-full bg-mdx-primary/10 flex items-center justify-center">
                          <User className="h-5 w-5 text-mdx-primary" />
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {encounter.patientName}
                          </div>
                          <div className="text-sm text-gray-500">
                            ID: {encounter.patientId}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 dark:text-white max-w-xs truncate">
                        {encounter.chiefComplaint}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${status.color}`}>
                        <StatusIcon className="h-3 w-3 mr-1" />
                        {status.label}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 dark:text-white">{encounter.startTime}</div>
                      <div className="text-sm text-gray-500">{encounter.duration}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {encounter.room || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {encounter.noteStatus === 'signed' ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-green-600 bg-green-100">
                          <FileText className="h-3 w-3 mr-1" />
                          Signed
                        </span>
                      ) : encounter.noteStatus === 'draft' ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-yellow-600 bg-yellow-100">
                          <FileText className="h-3 w-3 mr-1" />
                          Draft
                        </span>
                      ) : (
                        <span className="text-sm text-gray-500">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button className="text-mdx-primary hover:text-mdx-primary/80 mr-3">
                        View
                      </button>
                      {encounter.status === 'in_progress' && (
                        <button className="text-red-600 hover:text-red-800">
                          End
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
