'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';

const sessionData = [
  { month: 'Jan', sessions: 245, notes: 198 },
  { month: 'Feb', sessions: 312, notes: 287 },
  { month: 'Mar', sessions: 289, notes: 245 },
  { month: 'Apr', sessions: 356, notes: 312 },
  { month: 'May', sessions: 398, notes: 356 },
  { month: 'Jun', sessions: 425, notes: 389 },
];

const encounterTypes = [
  { name: 'Follow-up', value: 45, color: '#00A3E0' },
  { name: 'Initial', value: 25, color: '#00D4AA' },
  { name: 'Procedure', value: 15, color: '#003366' },
  { name: 'Emergency', value: 10, color: '#FF6B6B' },
  { name: 'Telemedicine', value: 5, color: '#9B59B6' },
];

const efficiencyData = [
  { day: 'Mon', avgTime: 12.5, target: 15 },
  { day: 'Tue', avgTime: 11.2, target: 15 },
  { day: 'Wed', avgTime: 13.8, target: 15 },
  { day: 'Thu', avgTime: 10.5, target: 15 },
  { day: 'Fri', avgTime: 14.2, target: 15 },
];

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Analytics
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Performance metrics and usage statistics
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Sessions & Notes Trend
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sessionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                <XAxis dataKey="month" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB',
                  }}
                />
                <Bar dataKey="sessions" fill="#00A3E0" radius={[4, 4, 0, 0]} />
                <Bar dataKey="notes" fill="#00D4AA" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Encounter Types Distribution
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={encounterTypes}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {encounterTypes.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-4">
            {encounterTypes.map((type) => (
              <div key={type.name} className="flex items-center gap-2">
                <div
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: type.color }}
                />
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {type.name} ({type.value}%)
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800 lg:col-span-2">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Documentation Efficiency (Avg. Minutes per Note)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={efficiencyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                <XAxis dataKey="day" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="avgTime"
                  stroke="#00A3E0"
                  strokeWidth={3}
                  dot={{ fill: '#00A3E0', strokeWidth: 2 }}
                />
                <Line
                  type="monotone"
                  dataKey="target"
                  stroke="#FF6B6B"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-mdx-primary" />
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Actual Time
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-red-400" />
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Target (15 min)
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <p className="text-sm text-gray-500 dark:text-gray-400">Total Sessions (MTD)</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">2,156</p>
          <p className="text-sm text-green-600 mt-1">+18% from last month</p>
        </div>
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <p className="text-sm text-gray-500 dark:text-gray-400">Notes Generated</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">1,892</p>
          <p className="text-sm text-green-600 mt-1">87.8% completion rate</p>
        </div>
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <p className="text-sm text-gray-500 dark:text-gray-400">Avg. Session Duration</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">12:34</p>
          <p className="text-sm text-green-600 mt-1">-2 min from last month</p>
        </div>
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <p className="text-sm text-gray-500 dark:text-gray-400">Time Saved (Est.)</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">156 hrs</p>
          <p className="text-sm text-mdx-primary mt-1">vs manual documentation</p>
        </div>
      </div>
    </div>
  );
}
