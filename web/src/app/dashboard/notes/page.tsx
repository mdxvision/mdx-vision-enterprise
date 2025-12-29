'use client';

import { useState } from 'react';
import { Search, Filter, FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const mockNotes = [
  {
    id: '1',
    patientName: 'John Smith',
    patientMrn: 'MRN-001234',
    type: 'SOAP',
    status: 'APPROVED',
    createdAt: '2024-01-15T10:45:00Z',
    icdCodes: ['J06.9', 'R05.9'],
    cptCodes: ['99213'],
  },
  {
    id: '2',
    patientName: 'Sarah Johnson',
    patientMrn: 'MRN-005678',
    type: 'SOAP',
    status: 'PENDING_REVIEW',
    createdAt: '2024-01-15T09:30:00Z',
    icdCodes: ['E11.9', 'I10'],
    cptCodes: ['99214'],
  },
  {
    id: '3',
    patientName: 'Michael Brown',
    patientMrn: 'MRN-009012',
    type: 'PROCEDURE',
    status: 'DRAFT',
    createdAt: '2024-01-15T11:20:00Z',
    icdCodes: ['M54.5'],
    cptCodes: ['20610'],
  },
];

const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  DRAFT: { icon: FileText, color: 'text-gray-500', label: 'Draft' },
  PENDING_REVIEW: { icon: Clock, color: 'text-yellow-500', label: 'Pending Review' },
  APPROVED: { icon: CheckCircle, color: 'text-green-500', label: 'Approved' },
  SIGNED: { icon: CheckCircle, color: 'text-blue-500', label: 'Signed' },
};

export default function NotesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Clinical Notes
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Review and manage AI-generated clinical documentation
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-800 dark:text-white"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-800 dark:text-white"
        >
          <option value="ALL">All Status</option>
          <option value="DRAFT">Draft</option>
          <option value="PENDING_REVIEW">Pending Review</option>
          <option value="APPROVED">Approved</option>
          <option value="SIGNED">Signed</option>
        </select>
        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
          <Filter className="h-4 w-4" />
          More Filters
        </button>
      </div>

      <div className="space-y-4">
        {mockNotes.map((note) => {
          const status = statusConfig[note.status];
          const StatusIcon = status.icon;
          return (
            <div
              key={note.id}
              className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 hover:shadow-md transition-shadow dark:bg-gray-800 dark:ring-gray-800"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-mdx-primary/10">
                    <FileText className="h-5 w-5 text-mdx-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {note.patientName}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {note.patientMrn} - {note.type} Note
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {new Date(note.createdAt).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusIcon className={cn('h-5 w-5', status.color)} />
                  <span className={cn('text-sm font-medium', status.color)}>
                    {status.label}
                  </span>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {note.icdCodes.map((code) => (
                  <span
                    key={code}
                    className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-300"
                  >
                    ICD: {code}
                  </span>
                ))}
                {note.cptCodes.map((code) => (
                  <span
                    key={code}
                    className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-300"
                  >
                    CPT: {code}
                  </span>
                ))}
              </div>
              <div className="mt-4 flex gap-2">
                <button className="rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90 transition-colors">
                  View Note
                </button>
                {note.status === 'PENDING_REVIEW' && (
                  <button className="rounded-lg border border-green-500 px-4 py-2 text-sm font-medium text-green-600 hover:bg-green-50 transition-colors dark:hover:bg-green-900/20">
                    Approve
                  </button>
                )}
                <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-700">
                  Export PDF
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
