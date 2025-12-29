'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const data = [
  { name: 'Mon', sessions: 24, notes: 18 },
  { name: 'Tue', sessions: 32, notes: 28 },
  { name: 'Wed', sessions: 28, notes: 24 },
  { name: 'Thu', sessions: 35, notes: 32 },
  { name: 'Fri', sessions: 42, notes: 38 },
  { name: 'Sat', sessions: 12, notes: 10 },
  { name: 'Sun', sessions: 8, notes: 6 },
];

export function ActivityChart() {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Weekly Activity
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorSessions" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00A3E0" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#00A3E0" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorNotes" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00D4AA" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#00D4AA" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
            <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} />
            <YAxis stroke="#9CA3AF" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1F2937',
                border: 'none',
                borderRadius: '8px',
                color: '#F9FAFB',
              }}
            />
            <Area
              type="monotone"
              dataKey="sessions"
              stroke="#00A3E0"
              fillOpacity={1}
              fill="url(#colorSessions)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="notes"
              stroke="#00D4AA"
              fillOpacity={1}
              fill="url(#colorNotes)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-center gap-6 mt-4">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-mdx-primary" />
          <span className="text-sm text-gray-500 dark:text-gray-400">Sessions</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-mdx-accent" />
          <span className="text-sm text-gray-500 dark:text-gray-400">Notes</span>
        </div>
      </div>
    </div>
  );
}
