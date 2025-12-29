import { Users, FileText, Mic, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

const stats = [
  {
    name: 'Total Patients',
    value: '2,847',
    change: '+12%',
    changeType: 'positive' as const,
    icon: Users,
  },
  {
    name: 'Sessions Today',
    value: '24',
    change: '+8%',
    changeType: 'positive' as const,
    icon: Mic,
  },
  {
    name: 'Notes Generated',
    value: '156',
    change: '+23%',
    changeType: 'positive' as const,
    icon: FileText,
  },
  {
    name: 'Avg. Session Time',
    value: '12:34',
    change: '-5%',
    changeType: 'positive' as const,
    icon: Clock,
  },
];

export function StatsCards() {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <div
          key={stat.name}
          className="relative overflow-hidden rounded-xl bg-white px-4 py-5 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800 sm:px-6"
        >
          <dt>
            <div className="absolute rounded-lg bg-mdx-primary/10 p-3">
              <stat.icon className="h-6 w-6 text-mdx-primary" />
            </div>
            <p className="ml-16 truncate text-sm font-medium text-gray-500 dark:text-gray-400">
              {stat.name}
            </p>
          </dt>
          <dd className="ml-16 flex items-baseline">
            <p className="text-2xl font-semibold text-gray-900 dark:text-white">
              {stat.value}
            </p>
            <p
              className={cn(
                'ml-2 flex items-baseline text-sm font-semibold',
                stat.changeType === 'positive' ? 'text-green-600' : 'text-red-600'
              )}
            >
              {stat.change}
            </p>
          </dd>
        </div>
      ))}
    </div>
  );
}
