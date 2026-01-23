'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  FileText,
  Mic,
  BarChart3,
  Settings,
  Stethoscope,
  Activity,
  Glasses,
  DollarSign,
  Receipt,
  Shield,
  ClipboardList,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Worklist', href: '/dashboard/worklist', icon: ClipboardList },
  { name: 'Sessions', href: '/dashboard/sessions', icon: Mic },
  { name: 'Patients', href: '/dashboard/patients', icon: Users },
  { name: 'Encounters', href: '/dashboard/encounters', icon: Stethoscope },
  { name: 'Clinical Notes', href: '/dashboard/notes', icon: FileText },
  { name: 'Billing', href: '/dashboard/billing', icon: Receipt },
  { name: 'DNFB', href: '/dashboard/dnfb', icon: DollarSign },
  { name: 'Audit Log', href: '/dashboard/audit', icon: Shield },
  { name: 'Devices', href: '/dashboard/devices', icon: Glasses },
  { name: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="hidden lg:flex lg:flex-shrink-0">
      <div className="flex w-64 flex-col">
        <div className="flex min-h-0 flex-1 flex-col border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
          <div className="flex flex-1 flex-col overflow-y-auto pt-5 pb-4">
            <div className="flex flex-shrink-0 items-center px-4">
              <Activity className="h-8 w-8 text-mdx-primary" />
              <span className="ml-2 text-xl font-bold text-gray-900 dark:text-white">
                MDx Vision
              </span>
            </div>
            <nav className="mt-8 flex-1 space-y-1 px-2">
              {navigation.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                      isActive
                        ? 'bg-mdx-primary/10 text-mdx-primary'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white'
                    )}
                  >
                    <item.icon
                      className={cn(
                        'mr-3 h-5 w-5 flex-shrink-0',
                        isActive
                          ? 'text-mdx-primary'
                          : 'text-gray-400 group-hover:text-gray-500'
                      )}
                    />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex flex-shrink-0 border-t border-gray-200 p-4 dark:border-gray-800">
            <div className="flex items-center">
              <div className="h-9 w-9 rounded-full bg-mdx-primary/20 flex items-center justify-center">
                <span className="text-sm font-medium text-mdx-primary">RR</span>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                  Dr. Rodriguez
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Administrator
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
