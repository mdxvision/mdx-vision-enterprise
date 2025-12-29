import { Mic, UserPlus, FileText, Upload } from 'lucide-react';
import Link from 'next/link';

const actions = [
  {
    name: 'Start Session',
    description: 'Begin a new recording session',
    href: '/dashboard/sessions/new',
    icon: Mic,
    color: 'bg-mdx-primary',
  },
  {
    name: 'Add Patient',
    description: 'Register a new patient',
    href: '/dashboard/patients/new',
    icon: UserPlus,
    color: 'bg-green-500',
  },
  {
    name: 'View Notes',
    description: 'Browse clinical notes',
    href: '/dashboard/notes',
    icon: FileText,
    color: 'bg-purple-500',
  },
  {
    name: 'Import Data',
    description: 'Import from EHR system',
    href: '/dashboard/settings/import',
    icon: Upload,
    color: 'bg-orange-500',
  },
];

export function QuickActions() {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Quick Actions
      </h3>
      <div className="grid grid-cols-2 gap-4">
        {actions.map((action) => (
          <Link
            key={action.name}
            href={action.href}
            className="group flex flex-col items-center rounded-lg border border-gray-200 p-4 hover:border-mdx-primary hover:shadow-md transition-all dark:border-gray-700 dark:hover:border-mdx-primary"
          >
            <div
              className={action.color + ' rounded-full p-3 text-white mb-3 group-hover:scale-110 transition-transform'}
            >
              <action.icon className="h-6 w-6" />
            </div>
            <span className="font-medium text-gray-900 dark:text-white text-center">
              {action.name}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400 text-center mt-1">
              {action.description}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
