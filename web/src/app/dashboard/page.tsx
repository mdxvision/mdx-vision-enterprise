import { StatsCards } from '@/components/dashboard/StatsCards';
import { RecentSessions } from '@/components/dashboard/RecentSessions';
import { ActivityChart } from '@/components/dashboard/ActivityChart';
import { QuickActions } from '@/components/dashboard/QuickActions';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Overview of your clinical documentation activity
        </p>
      </div>

      <StatsCards />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ActivityChart />
        <QuickActions />
      </div>

      <RecentSessions />
    </div>
  );
}
