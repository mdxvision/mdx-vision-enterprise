import { Play, FileText, CheckCircle } from 'lucide-react';

const sessions = [
  {
    id: '1',
    patientName: 'John Smith',
    patientMrn: 'MRN-001234',
    type: 'Follow-up Visit',
    status: 'completed',
    duration: '15:42',
    createdAt: '2024-01-15T10:30:00Z',
  },
  {
    id: '2',
    patientName: 'Sarah Johnson',
    patientMrn: 'MRN-005678',
    type: 'Initial Consultation',
    status: 'completed',
    duration: '28:15',
    createdAt: '2024-01-15T09:00:00Z',
  },
  {
    id: '3',
    patientName: 'Michael Brown',
    patientMrn: 'MRN-009012',
    type: 'Procedure Note',
    status: 'in_progress',
    duration: '08:32',
    createdAt: '2024-01-15T11:15:00Z',
  },
  {
    id: '4',
    patientName: 'Emily Davis',
    patientMrn: 'MRN-003456',
    type: 'Follow-up Visit',
    status: 'completed',
    duration: '12:08',
    createdAt: '2024-01-14T16:45:00Z',
  },
];

export function RecentSessions() {
  return (
    <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
      <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Recent Sessions
        </h3>
      </div>
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {sessions.map((session) => (
          <div
            key={session.id}
            className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-mdx-primary/10">
                {session.status === 'completed' ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <Play className="h-5 w-5 text-mdx-primary" />
                )}
              </div>
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {session.patientName}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {session.patientMrn} - {session.type}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {session.duration}
              </span>
              <button className="p-2 text-gray-400 hover:text-mdx-primary transition-colors">
                <FileText className="h-5 w-5" />
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
        <a
          href="/dashboard/sessions"
          className="text-sm font-medium text-mdx-primary hover:text-mdx-primary/80"
        >
          View all sessions
        </a>
      </div>
    </div>
  );
}
