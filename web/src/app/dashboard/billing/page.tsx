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
  LineChart,
  Line,
} from 'recharts';
import {
  Receipt,
  DollarSign,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Filter,
  RefreshCw,
  ChevronRight,
  Send,
  FileText,
  TrendingUp,
} from 'lucide-react';
import { billingApi } from '@/lib/api';
import type { BillingClaim, BillingSummary, ClaimStatus } from '@/types';

const STATUS_LABELS: Record<ClaimStatus, string> = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  ACCEPTED: 'Accepted',
  REJECTED: 'Rejected',
  PAID: 'Paid',
  DENIED: 'Denied',
};

const STATUS_COLORS: Record<ClaimStatus, string> = {
  DRAFT: '#9CA3AF',
  SUBMITTED: '#3B82F6',
  ACCEPTED: '#10B981',
  REJECTED: '#F59E0B',
  PAID: '#00D4AA',
  DENIED: '#EF4444',
};

// Mock data for demo
const mockSummary: BillingSummary = {
  totalClaims: 156,
  totalCharges: 4875000,
  totalPaid: 3892500,
  pendingAmount: 982500,
  byStatus: {
    DRAFT: { count: 12, amount: 245000 },
    SUBMITTED: { count: 28, amount: 687500 },
    ACCEPTED: { count: 8, amount: 175000 },
    REJECTED: { count: 5, amount: 125000 },
    PAID: { count: 98, amount: 3517500 },
    DENIED: { count: 5, amount: 125000 },
  },
  denialRate: 3.2,
  avgDaysToPayment: 18.5,
};

const mockClaims: BillingClaim[] = [
  {
    claimId: 'CLM-001',
    status: 'SUBMITTED',
    patientId: '12724066',
    patientName: 'SMARTS, NANCYS',
    mrn: 'MRN-12724066',
    serviceDate: '2025-12-28',
    diagnoses: [
      { code: 'J06.9', description: 'Acute upper respiratory infection', sequence: 1, isPrincipal: true },
    ],
    serviceLines: [
      {
        lineNumber: 1,
        serviceDate: '2025-12-28',
        procedure: { code: '99213', description: 'Office visit, established', modifiers: [], units: 1 },
        diagnosisPointers: [1],
        chargeAmount: 15000,
      },
    ],
    totalCharges: 15000,
    payerName: 'Blue Cross',
    createdAt: '2025-12-28T10:00:00Z',
    submittedAt: '2025-12-28T14:30:00Z',
  },
  {
    claimId: 'CLM-002',
    status: 'PAID',
    patientId: '12724067',
    patientName: 'JOHNSON, ROBERT',
    mrn: 'MRN-12724067',
    serviceDate: '2025-12-20',
    diagnoses: [
      { code: 'I10', description: 'Essential hypertension', sequence: 1, isPrincipal: true },
      { code: 'E11.9', description: 'Type 2 diabetes mellitus', sequence: 2, isPrincipal: false },
    ],
    serviceLines: [
      {
        lineNumber: 1,
        serviceDate: '2025-12-20',
        procedure: { code: '99214', description: 'Office visit, established - moderate', modifiers: ['-25'], units: 1 },
        diagnosisPointers: [1, 2],
        chargeAmount: 22500,
      },
      {
        lineNumber: 2,
        serviceDate: '2025-12-20',
        procedure: { code: '80053', description: 'Comprehensive metabolic panel', modifiers: [], units: 1 },
        diagnosisPointers: [2],
        chargeAmount: 8500,
      },
    ],
    totalCharges: 31000,
    paidAmount: 28500,
    payerName: 'Aetna',
    createdAt: '2025-12-20T11:00:00Z',
    submittedAt: '2025-12-20T16:00:00Z',
    paidAt: '2025-12-30T09:00:00Z',
  },
  {
    claimId: 'CLM-003',
    status: 'DENIED',
    patientId: '12724068',
    patientName: 'WILLIAMS, MARIA',
    mrn: 'MRN-12724068',
    serviceDate: '2025-12-15',
    diagnoses: [
      { code: 'M54.5', description: 'Low back pain', sequence: 1, isPrincipal: true },
    ],
    serviceLines: [
      {
        lineNumber: 1,
        serviceDate: '2025-12-15',
        procedure: { code: '72148', description: 'MRI lumbar spine w/o contrast', modifiers: [], units: 1 },
        diagnosisPointers: [1],
        chargeAmount: 125000,
      },
    ],
    totalCharges: 125000,
    denialReason: 'Prior authorization not obtained',
    payerName: 'United Healthcare',
    createdAt: '2025-12-15T14:00:00Z',
    submittedAt: '2025-12-15T17:00:00Z',
  },
  {
    claimId: 'CLM-004',
    status: 'DRAFT',
    patientId: '12724069',
    patientName: 'DAVIS, JAMES',
    mrn: 'MRN-12724069',
    serviceDate: '2025-12-31',
    diagnoses: [
      { code: 'R05.9', description: 'Cough, unspecified', sequence: 1, isPrincipal: true },
    ],
    serviceLines: [
      {
        lineNumber: 1,
        serviceDate: '2025-12-31',
        procedure: { code: '99212', description: 'Office visit, established - straightforward', modifiers: [], units: 1 },
        diagnosisPointers: [1],
        chargeAmount: 8500,
      },
    ],
    totalCharges: 8500,
    createdAt: '2025-12-31T10:00:00Z',
  },
  {
    claimId: 'CLM-005',
    status: 'ACCEPTED',
    patientId: '12724070',
    patientName: 'BROWN, PATRICIA',
    mrn: 'MRN-12724070',
    serviceDate: '2025-12-29',
    diagnoses: [
      { code: 'K21.0', description: 'GERD with esophagitis', sequence: 1, isPrincipal: true },
    ],
    serviceLines: [
      {
        lineNumber: 1,
        serviceDate: '2025-12-29',
        procedure: { code: '99213', description: 'Office visit, established', modifiers: [], units: 1 },
        diagnosisPointers: [1],
        chargeAmount: 15000,
      },
    ],
    totalCharges: 15000,
    payerName: 'Cigna',
    createdAt: '2025-12-29T09:00:00Z',
    submittedAt: '2025-12-29T12:00:00Z',
  },
];

const revenueData = [
  { month: 'Jul', charges: 385000, paid: 312000 },
  { month: 'Aug', charges: 425000, paid: 345000 },
  { month: 'Sep', charges: 398000, paid: 325000 },
  { month: 'Oct', charges: 456000, paid: 378000 },
  { month: 'Nov', charges: 512000, paid: 425000 },
  { month: 'Dec', charges: 487500, paid: 389250 },
];

export default function BillingPage() {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [claims, setClaims] = useState<BillingClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [summaryRes, claimsRes] = await Promise.all([
        billingApi.getSummary().catch(() => ({ data: mockSummary })),
        billingApi.getAll().catch(() => ({ data: mockClaims })),
      ]);
      setSummary(summaryRes.data);
      setClaims(Array.isArray(claimsRes.data) ? claimsRes.data : mockClaims);
    } catch {
      setSummary(mockSummary);
      setClaims(mockClaims);
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

  const getStatusChartData = () => {
    if (!summary) return [];
    return Object.entries(summary.byStatus)
      .filter(([, data]) => data.count > 0)
      .map(([status, data]) => ({
        name: STATUS_LABELS[status as ClaimStatus],
        value: data.count,
        amount: data.amount,
        color: STATUS_COLORS[status as ClaimStatus],
      }));
  };

  const getStatusIcon = (status: ClaimStatus) => {
    switch (status) {
      case 'PAID':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'DENIED':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'REJECTED':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'SUBMITTED':
        return <Send className="h-4 w-4 text-blue-500" />;
      case 'ACCEPTED':
        return <CheckCircle className="h-4 w-4 text-emerald-500" />;
      default:
        return <FileText className="h-4 w-4 text-gray-400" />;
    }
  };

  const filteredClaims = claims.filter((claim) => {
    if (selectedFilter === 'all') return true;
    if (selectedFilter === 'pending') return ['DRAFT', 'SUBMITTED', 'ACCEPTED'].includes(claim.status);
    if (selectedFilter === 'denied') return claim.status === 'DENIED';
    if (selectedFilter === 'paid') return claim.status === 'PAID';
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
            Billing Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Claims management and revenue tracking
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
            <div className="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
              <Receipt className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Total Claims</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-3">
            {summary?.totalClaims || 0}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {summary?.byStatus.SUBMITTED?.count || 0} pending submission
          </p>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
              <DollarSign className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Total Charges</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-3">
            {formatCurrency(summary?.totalCharges || 0)}
          </p>
          <p className="text-sm text-green-500 mt-1">
            {formatCurrency(summary?.totalPaid || 0)} collected
          </p>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-amber-100 p-2 dark:bg-amber-900/30">
              <Clock className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Pending A/R</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-3">
            {formatCurrency(summary?.pendingAmount || 0)}
          </p>
          <p className="text-sm text-amber-500 mt-1">
            Avg {summary?.avgDaysToPayment.toFixed(0)} days to payment
          </p>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-red-100 p-2 dark:bg-red-900/30">
              <TrendingUp className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Denial Rate</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-3">
            {summary?.denialRate.toFixed(1)}%
          </p>
          <p className="text-sm text-green-500 mt-1">
            Below 5% target
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Claims by Status
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={getStatusChartData()}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {getStatusChartData().map((entry, index) => (
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
            {getStatusChartData().map((item) => (
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
            Revenue Trend (6 Months)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                <XAxis dataKey="month" stroke="#9CA3AF" fontSize={12} />
                <YAxis
                  stroke="#9CA3AF"
                  fontSize={12}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB',
                  }}
                  formatter={(value: number) => [`$${(value / 100).toLocaleString()}`, '']}
                />
                <Line
                  type="monotone"
                  dataKey="charges"
                  name="Charges"
                  stroke="#3B82F6"
                  strokeWidth={3}
                  dot={{ fill: '#3B82F6', strokeWidth: 2 }}
                />
                <Line
                  type="monotone"
                  dataKey="paid"
                  name="Collected"
                  stroke="#00D4AA"
                  strokeWidth={3}
                  dot={{ fill: '#00D4AA', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-blue-500" />
              <span className="text-sm text-gray-500 dark:text-gray-400">Charges</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#00D4AA' }} />
              <span className="text-sm text-gray-500 dark:text-gray-400">Collected</span>
            </div>
          </div>
        </div>
      </div>

      {/* Claims Worklist */}
      <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
        <div className="border-b border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Claims Worklist
            </h3>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                value={selectedFilter}
                onChange={(e) => setSelectedFilter(e.target.value)}
                className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="all">All Claims</option>
                <option value="pending">Pending</option>
                <option value="paid">Paid</option>
                <option value="denied">Denied</option>
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
                  Claim ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Patient
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Service Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Charges
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Payer
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredClaims.map((claim) => (
                <tr
                  key={claim.claimId}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(claim.status)}
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          claim.status === 'PAID'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : claim.status === 'DENIED'
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                            : claim.status === 'SUBMITTED'
                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                            : claim.status === 'ACCEPTED'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400'
                        }`}
                      >
                        {STATUS_LABELS[claim.status]}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                    {claim.claimId}
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {claim.patientName}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {claim.mrn}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(claim.serviceDate).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {formatCurrency(claim.totalCharges)}
                      </p>
                      {claim.paidAmount && (
                        <p className="text-xs text-green-500">
                          Paid: {formatCurrency(claim.paidAmount)}
                        </p>
                      )}
                      {claim.denialReason && (
                        <p className="text-xs text-red-500 truncate max-w-[150px]">
                          {claim.denialReason}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {claim.payerName || '-'}
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
        {filteredClaims.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <CheckCircle className="h-12 w-12 mx-auto text-green-400 mb-2" />
            <p>No claims match the selected filter</p>
          </div>
        )}
      </div>

      {/* Denial Alert */}
      {summary && summary.byStatus.DENIED && summary.byStatus.DENIED.count > 0 && (
        <div className="rounded-xl bg-gradient-to-r from-red-500/10 to-amber-500/10 border border-red-200 dark:border-red-800 p-4">
          <div className="flex items-start gap-4">
            <div className="rounded-full bg-red-100 p-2 dark:bg-red-900/30">
              <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900 dark:text-white">
                Denied Claims Require Attention
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {summary.byStatus.DENIED.count} claims denied totaling{' '}
                <span className="font-semibold text-red-600">
                  {formatCurrency(summary.byStatus.DENIED.amount)}
                </span>
                . Review and appeal to recover revenue.
              </p>
            </div>
            <button
              onClick={() => setSelectedFilter('denied')}
              className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
            >
              View Denied Claims
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
