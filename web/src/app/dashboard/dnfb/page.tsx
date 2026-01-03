'use client';

import { useState, useEffect } from 'react';
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
} from 'recharts';
import {
  AlertTriangle,
  Clock,
  DollarSign,
  FileWarning,
  CheckCircle,
  XCircle,
  Filter,
  RefreshCw,
  ChevronRight,
} from 'lucide-react';
import { dnfbApi } from '@/lib/api';
import type { DNFBAccount, DNFBSummary, DNFBReason, AgingBucket } from '@/types';

const REASON_LABELS: Record<DNFBReason, string> = {
  CODING_INCOMPLETE: 'Coding Incomplete',
  DOCUMENTATION_MISSING: 'Documentation Missing',
  CHARGES_PENDING: 'Charges Pending',
  PRIOR_AUTH_MISSING: 'Prior Auth Missing',
  PRIOR_AUTH_EXPIRED: 'Prior Auth Expired',
  PRIOR_AUTH_DENIED: 'Prior Auth Denied',
  INSURANCE_VERIFICATION: 'Insurance Verification',
  CLINICAL_REVIEW: 'Clinical Review',
  PHYSICIAN_QUERY: 'Physician Query',
  COMPLIANCE_HOLD: 'Compliance Hold',
  SYSTEM_ERROR: 'System Error',
  OTHER: 'Other',
};

const REASON_COLORS: Record<string, string> = {
  CODING_INCOMPLETE: '#00A3E0',
  DOCUMENTATION_MISSING: '#FF6B6B',
  CHARGES_PENDING: '#FFB84D',
  PRIOR_AUTH_MISSING: '#9B59B6',
  PRIOR_AUTH_EXPIRED: '#E74C3C',
  PRIOR_AUTH_DENIED: '#C0392B',
  INSURANCE_VERIFICATION: '#3498DB',
  CLINICAL_REVIEW: '#00D4AA',
  PHYSICIAN_QUERY: '#F39C12',
  COMPLIANCE_HOLD: '#8E44AD',
  SYSTEM_ERROR: '#95A5A6',
  OTHER: '#7F8C8D',
};

const AGING_COLORS: Record<AgingBucket, string> = {
  '0-3': '#00D4AA',
  '4-7': '#00A3E0',
  '8-14': '#FFB84D',
  '15-30': '#FF6B6B',
  '31+': '#C0392B',
};

// Mock data for demo
const mockSummary: DNFBSummary = {
  totalAccounts: 47,
  totalAtRiskRevenue: 2847500,
  byReason: {
    CODING_INCOMPLETE: { count: 12, revenue: 725000 },
    DOCUMENTATION_MISSING: { count: 8, revenue: 485000 },
    CHARGES_PENDING: { count: 6, revenue: 362500 },
    PRIOR_AUTH_MISSING: { count: 7, revenue: 525000 },
    PRIOR_AUTH_EXPIRED: { count: 4, revenue: 275000 },
    PRIOR_AUTH_DENIED: { count: 3, revenue: 187500 },
    INSURANCE_VERIFICATION: { count: 2, revenue: 95000 },
    CLINICAL_REVIEW: { count: 2, revenue: 87500 },
    PHYSICIAN_QUERY: { count: 1, revenue: 52500 },
    COMPLIANCE_HOLD: { count: 1, revenue: 37500 },
    SYSTEM_ERROR: { count: 1, revenue: 15000 },
    OTHER: { count: 0, revenue: 0 },
  },
  byAgingBucket: {
    '0-3': { count: 8, revenue: 485000 },
    '4-7': { count: 12, revenue: 725000 },
    '8-14': { count: 15, revenue: 912500 },
    '15-30': { count: 8, revenue: 487500 },
    '31+': { count: 4, revenue: 237500 },
  },
  priorAuthIssues: 14,
  priorAuthAtRisk: 987500,
  avgDaysSinceDischarge: 11.2,
};

const mockAccounts: DNFBAccount[] = [
  {
    dnfbId: 'DNFB-001',
    patientId: '12724066',
    patientName: 'SMARTS, NANCYS',
    mrn: 'MRN-12724066',
    accountNumber: 'ACC-001234',
    dischargeDate: '2025-12-28',
    reason: 'PRIOR_AUTH_MISSING',
    status: 'OPEN',
    priorAuth: { status: 'NOT_OBTAINED', payerName: 'Blue Cross' },
    daysSinceDischarge: 4,
    agingBucket: '4-7',
    estimatedCharges: 75000,
    createdAt: '2025-12-28T10:00:00Z',
  },
  {
    dnfbId: 'DNFB-002',
    patientId: '12724067',
    patientName: 'JOHNSON, ROBERT',
    mrn: 'MRN-12724067',
    accountNumber: 'ACC-001235',
    dischargeDate: '2025-12-25',
    reason: 'CODING_INCOMPLETE',
    status: 'IN_PROGRESS',
    daysSinceDischarge: 7,
    agingBucket: '4-7',
    estimatedCharges: 125000,
    assignedTo: 'Sarah Chen',
    createdAt: '2025-12-25T14:30:00Z',
  },
  {
    dnfbId: 'DNFB-003',
    patientId: '12724068',
    patientName: 'WILLIAMS, MARIA',
    mrn: 'MRN-12724068',
    accountNumber: 'ACC-001236',
    dischargeDate: '2025-12-20',
    reason: 'DOCUMENTATION_MISSING',
    status: 'ESCALATED',
    daysSinceDischarge: 12,
    agingBucket: '8-14',
    estimatedCharges: 89500,
    assignedTo: 'Dr. Rodriguez',
    notes: 'Awaiting operative note from surgeon',
    createdAt: '2025-12-20T09:15:00Z',
  },
  {
    dnfbId: 'DNFB-004',
    patientId: '12724069',
    patientName: 'DAVIS, JAMES',
    mrn: 'MRN-12724069',
    accountNumber: 'ACC-001237',
    dischargeDate: '2025-12-15',
    reason: 'PRIOR_AUTH_EXPIRED',
    status: 'OPEN',
    priorAuth: {
      status: 'EXPIRED',
      authNumber: 'PA-789456',
      expirationDate: '2025-12-10',
      payerName: 'Aetna',
    },
    daysSinceDischarge: 17,
    agingBucket: '15-30',
    estimatedCharges: 156000,
    createdAt: '2025-12-15T16:45:00Z',
  },
  {
    dnfbId: 'DNFB-005',
    patientId: '12724070',
    patientName: 'BROWN, PATRICIA',
    mrn: 'MRN-12724070',
    accountNumber: 'ACC-001238',
    dischargeDate: '2025-11-25',
    reason: 'PRIOR_AUTH_DENIED',
    status: 'ESCALATED',
    priorAuth: {
      status: 'DENIED',
      authNumber: 'PA-789457',
      denialReason: 'Medical necessity not demonstrated',
      payerName: 'United Healthcare',
    },
    daysSinceDischarge: 37,
    agingBucket: '31+',
    estimatedCharges: 95000,
    assignedTo: 'Appeals Team',
    notes: 'Appeal submitted 12/20, awaiting response',
    createdAt: '2025-11-25T11:20:00Z',
  },
];

export default function DNFBPage() {
  const [summary, setSummary] = useState<DNFBSummary | null>(null);
  const [accounts, setAccounts] = useState<DNFBAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Try to load from API, fall back to mock data
      const [summaryRes, accountsRes] = await Promise.all([
        dnfbApi.getSummary().catch(() => ({ data: mockSummary })),
        dnfbApi.getAll().catch(() => ({ data: mockAccounts })),
      ]);
      setSummary(summaryRes.data);
      setAccounts(Array.isArray(accountsRes.data) ? accountsRes.data : mockAccounts);
    } catch {
      setSummary(mockSummary);
      setAccounts(mockAccounts);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount / 100);
  };

  const getReasonChartData = () => {
    if (!summary) return [];
    return Object.entries(summary.byReason)
      .filter(([, data]) => data.count > 0)
      .map(([reason, data]) => ({
        name: REASON_LABELS[reason as DNFBReason],
        value: data.count,
        revenue: data.revenue,
        color: REASON_COLORS[reason],
      }))
      .sort((a, b) => b.value - a.value);
  };

  const getAgingChartData = () => {
    if (!summary) return [];
    return Object.entries(summary.byAgingBucket).map(([bucket, data]) => ({
      bucket,
      count: data.count,
      revenue: data.revenue / 100,
      color: AGING_COLORS[bucket as AgingBucket],
    }));
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'RESOLVED':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'ESCALATED':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'IN_PROGRESS':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <FileWarning className="h-4 w-4 text-gray-400" />;
    }
  };

  const filteredAccounts = accounts.filter((account) => {
    if (selectedFilter === 'all') return true;
    if (selectedFilter === 'prior-auth') {
      return ['PRIOR_AUTH_MISSING', 'PRIOR_AUTH_EXPIRED', 'PRIOR_AUTH_DENIED'].includes(
        account.reason
      );
    }
    if (selectedFilter === 'escalated') return account.status === 'ESCALATED';
    if (selectedFilter === 'over-14') return account.daysSinceDischarge > 14;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-mdx-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            DNFB Management
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Discharged Not Final Billed - Revenue cycle worklist
          </p>
        </div>
        <button
          onClick={loadData}
          className="inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-red-100 p-2 dark:bg-red-900/30">
              <FileWarning className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Total DNFB Accounts</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-3">
            {summary?.totalAccounts || 0}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Avg {summary?.avgDaysSinceDischarge.toFixed(1)} days since discharge
          </p>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-amber-100 p-2 dark:bg-amber-900/30">
              <DollarSign className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">At-Risk Revenue</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-3">
            {formatCurrency(summary?.totalAtRiskRevenue || 0)}
          </p>
          <p className="text-sm text-red-500 mt-1">Unbilled charges pending</p>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-purple-100 p-2 dark:bg-purple-900/30">
              <AlertTriangle className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Prior Auth Issues</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-3">
            {summary?.priorAuthIssues || 0}
          </p>
          <p className="text-sm text-purple-500 mt-1">
            {formatCurrency(summary?.priorAuthAtRisk || 0)} at risk
          </p>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-red-100 p-2 dark:bg-red-900/30">
              <Clock className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Over 14 Days</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-3">
            {(summary?.byAgingBucket['15-30']?.count || 0) +
              (summary?.byAgingBucket['31+']?.count || 0)}
          </p>
          <p className="text-sm text-red-500 mt-1">Requires immediate attention</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            DNFB by Reason
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={getReasonChartData()}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {getReasonChartData().map((entry, index) => (
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
          <div className="flex flex-wrap justify-center gap-3 mt-4">
            {getReasonChartData()
              .slice(0, 5)
              .map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {item.name} ({item.value})
                  </span>
                </div>
              ))}
          </div>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            DNFB by Aging Bucket
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={getAgingChartData()}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                <XAxis dataKey="bucket" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB',
                  }}
                  formatter={(value: number, name: string) => [
                    name === 'revenue'
                      ? `$${value.toLocaleString()}`
                      : `${value} accounts`,
                    name === 'revenue' ? 'Revenue' : 'Count',
                  ]}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {getAgingChartData().map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-4 mt-4">
            {Object.entries(AGING_COLORS).map(([bucket, color]) => (
              <div key={bucket} className="flex items-center gap-2">
                <div
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {bucket} days
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Worklist */}
      <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
        <div className="border-b border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              DNFB Worklist
            </h3>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                value={selectedFilter}
                onChange={(e) => setSelectedFilter(e.target.value)}
                className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="all">All Accounts</option>
                <option value="prior-auth">Prior Auth Issues</option>
                <option value="escalated">Escalated</option>
                <option value="over-14">Over 14 Days</option>
              </select>
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Patient
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Reason
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Days
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Est. Charges
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Assigned To
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredAccounts.map((account) => (
                <tr
                  key={account.dnfbId}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(account.status)}
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          account.status === 'ESCALATED'
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                            : account.status === 'IN_PROGRESS'
                            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                            : account.status === 'RESOLVED'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400'
                        }`}
                      >
                        {account.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {account.patientName}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {account.mrn} | {account.accountNumber}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm text-gray-900 dark:text-white">
                        {REASON_LABELS[account.reason]}
                      </p>
                      {account.priorAuth && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {account.priorAuth.payerName} -{' '}
                          <span
                            className={
                              account.priorAuth.status === 'DENIED'
                                ? 'text-red-500'
                                : account.priorAuth.status === 'EXPIRED'
                                ? 'text-amber-500'
                                : ''
                            }
                          >
                            {account.priorAuth.status}
                          </span>
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-sm font-medium ${
                        account.daysSinceDischarge > 30
                          ? 'text-red-600'
                          : account.daysSinceDischarge > 14
                          ? 'text-amber-600'
                          : 'text-gray-900 dark:text-white'
                      }`}
                    >
                      {account.daysSinceDischarge}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                    {formatCurrency(account.estimatedCharges || 0)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {account.assignedTo || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <button className="inline-flex items-center gap-1 text-mdx-primary hover:text-mdx-primary/80 text-sm font-medium">
                      View <ChevronRight className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredAccounts.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <CheckCircle className="h-12 w-12 mx-auto text-green-400 mb-2" />
            <p>No accounts match the selected filter</p>
          </div>
        )}
      </div>

      {/* Prior Auth Alert Banner */}
      {summary && summary.priorAuthIssues > 0 && (
        <div className="rounded-xl bg-gradient-to-r from-purple-500/10 to-red-500/10 border border-purple-200 dark:border-purple-800 p-4">
          <div className="flex items-start gap-4">
            <div className="rounded-full bg-purple-100 p-2 dark:bg-purple-900/30">
              <XCircle className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900 dark:text-white">
                Prior Authorization Alert
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {summary.priorAuthIssues} accounts have prior authorization issues totaling{' '}
                <span className="font-semibold text-red-600">
                  {formatCurrency(summary.priorAuthAtRisk)}
                </span>{' '}
                in at-risk revenue. Review and resolve to prevent claim denials.
              </p>
            </div>
            <button
              onClick={() => setSelectedFilter('prior-auth')}
              className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 transition-colors"
            >
              View Prior Auth Issues
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
