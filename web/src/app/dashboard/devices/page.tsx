'use client';

import { useState, useEffect } from 'react';
import {
  Glasses,
  Plus,
  QrCode,
  Trash2,
  Shield,
  Smartphone,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Copy,
  X,
} from 'lucide-react';

// API base URL - same as EHR proxy
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

interface Device {
  device_id: string;
  device_name: string;
  device_type: string;
  paired_at: string;
  last_seen: string | null;
  is_active: boolean;
  is_wiped: boolean;
  has_active_session: boolean;
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPairModal, setShowPairModal] = useState(false);
  const [showTotpModal, setShowTotpModal] = useState(false);
  const [pairingQr, setPairingQr] = useState<string | null>(null);
  const [totpQr, setTotpQr] = useState<string | null>(null);
  const [totpSecret, setTotpSecret] = useState<string | null>(null);
  const [clinicianId] = useState('test-clinician-001'); // Would come from auth context

  // Fetch devices on mount
  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/v1/auth/clinician/${clinicianId}/devices`);
      if (response.ok) {
        const data = await response.json();
        setDevices(data.devices || []);
      }
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const generatePairingQr = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/clinician/${clinicianId}/pairing-qr`, {
        method: 'POST',
      });
      if (response.ok) {
        const data = await response.json();
        setPairingQr(data.qr_code);
        setShowPairModal(true);
      }
    } catch (error) {
      console.error('Failed to generate pairing QR:', error);
    }
  };

  const generateTotpQr = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/clinician/${clinicianId}/totp-qr`, {
        method: 'POST',
      });
      if (response.ok) {
        const data = await response.json();
        setTotpQr(data.qr_code);
        setTotpSecret(data.secret);
        setShowTotpModal(true);
      }
    } catch (error) {
      console.error('Failed to generate TOTP QR:', error);
    }
  };

  const wipeDevice = async (deviceId: string) => {
    if (!confirm('Are you sure you want to wipe this device? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/device/wipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: deviceId,
          admin_token: 'mdx-admin-secret-change-in-prod', // Would use real auth
        }),
      });

      if (response.ok) {
        fetchDevices(); // Refresh list
      }
    } catch (error) {
      console.error('Failed to wipe device:', error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const getRelativeTime = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Device Management
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage your AR glasses and authentication settings
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={generateTotpQr}
            className="inline-flex items-center gap-2 rounded-lg border border-mdx-primary px-4 py-2 text-sm font-medium text-mdx-primary hover:bg-mdx-primary/10 transition-colors"
          >
            <Smartphone className="h-4 w-4" />
            Setup Authenticator
          </button>
          <button
            onClick={generatePairingQr}
            className="inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Pair New Device
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
              <Glasses className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {devices.length}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Devices</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
              <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {devices.filter(d => d.has_active_session).length}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Active Sessions</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-yellow-100 p-2 dark:bg-yellow-900/30">
              <Clock className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {devices.filter(d => d.is_active && !d.has_active_session).length}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Idle Devices</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-red-100 p-2 dark:bg-red-900/30">
              <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {devices.filter(d => d.is_wiped).length}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Wiped</p>
            </div>
          </div>
        </div>
      </div>

      {/* Devices List */}
      <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Paired Devices
          </h2>
          <button
            onClick={fetchDevices}
            className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : devices.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Glasses className="h-12 w-12 text-gray-300 dark:text-gray-600" />
            <p className="mt-4 text-gray-500 dark:text-gray-400">No devices paired yet</p>
            <button
              onClick={generatePairingQr}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90"
            >
              <Plus className="h-4 w-4" />
              Pair Your First Device
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {devices.map((device) => (
              <div
                key={device.device_id}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50"
              >
                <div className="flex items-center gap-4">
                  <div className={`rounded-lg p-3 ${
                    device.is_wiped
                      ? 'bg-red-100 dark:bg-red-900/30'
                      : device.has_active_session
                        ? 'bg-green-100 dark:bg-green-900/30'
                        : 'bg-gray-100 dark:bg-gray-700'
                  }`}>
                    <Glasses className={`h-6 w-6 ${
                      device.is_wiped
                        ? 'text-red-600 dark:text-red-400'
                        : device.has_active_session
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-gray-600 dark:text-gray-400'
                    }`} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900 dark:text-white">
                        {device.device_name}
                      </h3>
                      {device.is_wiped && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
                          <XCircle className="h-3 w-3" />
                          Wiped
                        </span>
                      )}
                      {!device.is_wiped && device.has_active_session && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                          <CheckCircle className="h-3 w-3" />
                          Active
                        </span>
                      )}
                      {!device.is_wiped && !device.has_active_session && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          <Clock className="h-3 w-3" />
                          Locked
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <span>{device.device_type}</span>
                      <span>•</span>
                      <span>Paired {formatDate(device.paired_at)}</span>
                      <span>•</span>
                      <span>Last seen {getRelativeTime(device.last_seen)}</span>
                    </div>
                    <p className="mt-1 text-xs text-gray-400 dark:text-gray-500 font-mono">
                      ID: {device.device_id.slice(0, 8)}...
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {!device.is_wiped && (
                    <button
                      onClick={() => wipeDevice(device.device_id)}
                      className="inline-flex items-center gap-2 rounded-lg border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
                    >
                      <Trash2 className="h-4 w-4" />
                      Wipe
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Security Info */}
      <div className="rounded-xl bg-gradient-to-r from-mdx-primary/10 to-blue-500/10 p-6 dark:from-mdx-primary/20 dark:to-blue-500/20">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-white p-3 shadow-sm dark:bg-gray-800">
            <Shield className="h-6 w-6 text-mdx-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Multi-Layer Security
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Your AR glasses are protected with TOTP authentication, proximity lock, and remote wipe.
              If your glasses are lost or stolen, use the Wipe button to immediately revoke access.
            </p>
            <div className="mt-4 flex flex-wrap gap-4">
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <QrCode className="h-4 w-4 text-mdx-primary" />
                QR Code Pairing
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <Smartphone className="h-4 w-4 text-mdx-primary" />
                TOTP Authentication
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <AlertTriangle className="h-4 w-4 text-mdx-primary" />
                Proximity Auto-Lock
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <Trash2 className="h-4 w-4 text-mdx-primary" />
                Remote Wipe
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Pairing QR Modal */}
      {showPairModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Pair New Device
              </h3>
              <button
                onClick={() => setShowPairModal(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Put on your AR glasses and say "pair device", then scan this QR code.
              </p>

              {pairingQr && (
                <div className="inline-block rounded-lg bg-white p-4 shadow-inner">
                  <img
                    src={`data:image/png;base64,${pairingQr}`}
                    alt="Pairing QR Code"
                    className="h-48 w-48"
                  />
                </div>
              )}

              <p className="mt-4 text-xs text-gray-400 dark:text-gray-500">
                This QR code expires in 5 minutes
              </p>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowPairModal(false)}
                className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TOTP Setup Modal */}
      {showTotpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Setup Authenticator App
              </h3>
              <button
                onClick={() => setShowTotpModal(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Scan this QR code with Google Authenticator, Authy, or any TOTP app.
              </p>

              {totpQr && (
                <div className="inline-block rounded-lg bg-white p-4 shadow-inner">
                  <img
                    src={`data:image/png;base64,${totpQr}`}
                    alt="TOTP QR Code"
                    className="h-48 w-48"
                  />
                </div>
              )}

              {totpSecret && (
                <div className="mt-4">
                  <p className="text-xs text-gray-400 dark:text-gray-500 mb-2">
                    Or enter this code manually:
                  </p>
                  <div className="inline-flex items-center gap-2 rounded-lg bg-gray-100 px-3 py-2 font-mono text-sm dark:bg-gray-700">
                    <span className="text-gray-900 dark:text-white">{totpSecret}</span>
                    <button
                      onClick={() => copyToClipboard(totpSecret)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}

              <p className="mt-4 text-xs text-gray-400 dark:text-gray-500">
                After setup, say the 6-digit code to unlock your glasses
              </p>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowTotpModal(false)}
                className="rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
