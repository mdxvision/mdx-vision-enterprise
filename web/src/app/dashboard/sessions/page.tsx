'use client';

import { useState } from 'react';
import { Plus, Search, Filter, Play, FileText, MoreVertical } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

const mockSessions = [
  {
    id: '1',
    patientName: 'John Smith',
    patientMrn: 'MRN-001234',
    type: 'FOLLOW_UP',
    status: 'COMPLETED',
    duration: '15:42',
    createdAt: '2024-01-15T10:30:00Z',
    hasNote: true,
  },
  {
    id: '2',
    patientName: 'Sarah Johnson',
    patientMrn: 'MRN-005678',
    type: 'CONSULTATION',
    status: 'COMPLETED',
    duration: '28:15',
    createdAt: '2024-01-15T09:00:00Z',
    hasNote: true,
  },
  {
    id: '3',
    patientName: 'Michael Brown',
    patientMrn: 'MRN-009012',
    type: 'PROCEDURE_NOTE',
    status: 'ACTIVE',
    duration: '08:32',
    createdAt: '2024-01-15T11:15:00Z',
    hasNote: false,
  },
];

const statusColors: Record<string, string> = {
  ACTIVE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  COMPLETED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  PAUSED: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  CANCELLED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
};

export default function SessionsPage() {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Sessions
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage recording sessions and transcriptions
          </p>
        </div>
        <Link
          href="/dashboard/sessions/new"
          className="inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Session
        </Link>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-800 dark:text-white"
          />
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
          <Filter className="h-4 w-4" />
          Filters
        </button>
      </div>

      <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">
                Patient
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">
                Duration
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">
                Date
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {mockSessions.map((session) => (
              <tr key={session.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {session.patientName}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {session.patientMrn}
                    </p>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-900 dark:text-white">
                    {session.type.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={cn(
                      'inline-flex rounded-full px-2 py-1 text-xs font-medium',
                      statusColors[session.status]
                    )}
                  >
                    {session.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {session.duration}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {new Date(session.createdAt).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <div className="flex items-center justify-end gap-2">
                    {session.status === 'ACTIVE' && (
                      <button className="p-2 text-gray-400 hover:text-mdx-primary transition-colors">
                        <Play className="h-4 w-4" />
                      </button>
                    )}
                    {session.hasNote && (
                      <button className="p-2 text-gray-400 hover:text-mdx-primary transition-colors">
                        <FileText className="h-4 w-4" />
                      </button>
                    )}
                    <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
