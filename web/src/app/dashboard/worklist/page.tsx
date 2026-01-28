'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Clock,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  UserPlus,
  ChevronRight,
  Activity,
  Stethoscope,
  Calendar,
  MapPin,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useSyncWebSocket, WorklistUpdateEvent } from '@/hooks/useSyncWebSocket';

// API base URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

interface WorklistPatient {
  patient_id: string;
  name: string;
  date_of_birth: string;
  gender: string;
  mrn: string | null;
  room: string | null;
  appointment_time: string | null;
  appointment_type: string | null;
  chief_complaint: string | null;
  provider: string | null;
  status: string;
  checked_in_at: string | null;
  encounter_started_at: string | null;
  has_critical_alerts: boolean;
  priority: number;
  ehr?: string;
}

interface WorklistResponse {
  date: string;
  provider: string | null;
  location: string | null;
  patients: WorklistPatient[];
  total_scheduled: number;
  checked_in: number;
  in_progress: number;
  completed: number;
}

export default function WorklistPage() {
  const [worklist, setWorklist] = useState<WorklistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPatient, setSelectedPatient] = useState<WorklistPatient | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncEvent, setLastSyncEvent] = useState<string | null>(null);

  // Real-time sync with glasses
  const handleWorklistUpdate = useCallback((event: WorklistUpdateEvent) => {
    console.log('Real-time update:', event);
    setLastSyncEvent(`${event.action}: ${event.patient.name}`);

    // Update the patient in our local state
    setWorklist(prev => {
      if (!prev) return prev;

      const updatedPatients = prev.patients.map(p =>
        p.patient_id === event.patient.patient_id
          ? { ...p, ...event.patient }
          : p
      );

      // Recalculate stats
      const stats = {
        total_scheduled: updatedPatients.length,
        checked_in: updatedPatients.filter(p => ['checked_in', 'in_room', 'in_progress'].includes(p.status)).length,
        in_progress: updatedPatients.filter(p => p.status === 'in_progress').length,
        completed: updatedPatients.filter(p => p.status === 'completed').length,
      };

      return { ...prev, patients: updatedPatients, ...stats };
    });

    // Clear sync event indicator after 3 seconds
    setTimeout(() => setLastSyncEvent(null), 3000);
  }, []);

  const { isConnected: syncConnected } = useSyncWebSocket({
    onWorklistUpdate: handleWorklistUpdate,
  });

  useEffect(() => {
    fetchWorklist();
    // Auto-refresh every 60 seconds (longer now that we have real-time sync)
    const interval = setInterval(fetchWorklist, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchWorklist = async () => {
    try {
      setError(null);
      const response = await fetch(`${API_URL}/api/v1/worklist`);
      if (response.ok) {
        const data = await response.json();
        setWorklist(data);
      } else {
        setError('Failed to fetch worklist');
      }
    } catch (err) {
      console.error('Failed to fetch worklist:', err);
      setError('Connection error - is the EHR Proxy running?');
    } finally {
      setLoading(false);
    }
  };

  const checkInPatient = async (patientId: string, room?: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/worklist/check-in`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          room: room || null,
        }),
      });
      if (response.ok) {
        fetchWorklist();
      }
    } catch (err) {
      console.error('Failed to check in patient:', err);
    }
  };

  const updateStatus = async (patientId: string, newStatus: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/worklist/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          status: newStatus,
        }),
      });
      if (response.ok) {
        fetchWorklist();
      }
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      scheduled: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
      checked_in: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      in_room: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
      in_progress: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
      no_show: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    };
    const labels: Record<string, string> = {
      scheduled: 'Scheduled',
      checked_in: 'Checked In',
      in_room: 'In Room',
      in_progress: 'In Progress',
      completed: 'Completed',
      no_show: 'No Show',
    };
    return (
      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status] || styles.scheduled}`}>
        {labels[status] || status}
      </span>
    );
  };

  const getPriorityBadge = (priority: number) => {
    if (priority === 2) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700 dark:bg-red-900/30 dark:text-red-400">
          STAT
        </span>
      );
    }
    if (priority === 1) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-bold text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
          Urgent
        </span>
      );
    }
    return null;
  };

  const getEhrBadge = (ehr?: string) => {
    if (ehr === 'epic') {
      return (
        <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
          Epic
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
        Cerner
      </span>
    );
  };

  const formatTime = (time: string | null) => {
    if (!time) return '--:--';
    return time;
  };

  const formatAge = (dob: string) => {
    const birthDate = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return `${age}y`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="h-8 w-8 animate-spin text-mdx-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
        <p className="text-gray-600 dark:text-gray-400">{error}</p>
        <button
          onClick={fetchWorklist}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Today's Worklist
          </h1>
          <div className="mt-1 flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
            <span>{worklist?.date} • {worklist?.provider || 'Dr. Smith'} • {worklist?.location || 'Clinic A'}</span>
            <span className="flex items-center gap-1.5">
              {syncConnected ? (
                <>
                  <Wifi className="h-3.5 w-3.5 text-green-500" />
                  <span className="text-green-600 dark:text-green-400">Live sync</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-3.5 w-3.5 text-gray-400" />
                  <span>Offline</span>
                </>
              )}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastSyncEvent && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400 animate-pulse">
              <Activity className="h-3 w-3" />
              {lastSyncEvent}
            </span>
          )}
          <button
            onClick={fetchWorklist}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90">
            <UserPlus className="h-4 w-4" />
            Add Walk-in
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
              <Calendar className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {worklist?.total_scheduled || 0}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Scheduled</p>
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
                {worklist?.checked_in || 0}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Waiting</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
              <Stethoscope className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {worklist?.in_progress || 0}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">In Progress</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-100 p-2 dark:bg-emerald-900/30">
              <CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {worklist?.completed || 0}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
            </div>
          </div>
        </div>
      </div>

      {/* Patient List */}
      <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Patients ({worklist?.patients?.length || 0})
          </h2>
        </div>

        {!worklist?.patients?.length ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Users className="h-12 w-12 text-gray-300 dark:text-gray-600" />
            <p className="mt-4 text-gray-500 dark:text-gray-400">No patients scheduled</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {worklist.patients.map((patient, index) => (
              <div
                key={patient.patient_id}
                className={`flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors ${
                  selectedPatient?.patient_id === patient.patient_id ? 'bg-mdx-primary/5 dark:bg-mdx-primary/10' : ''
                }`}
                onClick={() => setSelectedPatient(patient)}
              >
                <div className="flex items-center gap-4">
                  {/* Index number */}
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                    patient.priority === 2 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                    patient.priority === 1 ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' :
                    'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                  }`}>
                    {index + 1}
                  </div>

                  {/* Patient Info */}
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                        {patient.name}
                      </h3>
                      {getPriorityBadge(patient.priority)}
                      {patient.has_critical_alerts && (
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                      )}
                      {getEhrBadge(patient.ehr)}
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                      <span>{formatAge(patient.date_of_birth)} {patient.gender?.charAt(0).toUpperCase()}</span>
                      <span>•</span>
                      <span>MRN: {patient.mrn || 'N/A'}</span>
                      {patient.room && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {patient.room}
                          </span>
                        </>
                      )}
                    </div>
                    {patient.chief_complaint && (
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                        CC: {patient.chief_complaint}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {/* Time */}
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatTime(patient.appointment_time)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {patient.appointment_type || 'Visit'}
                    </p>
                  </div>

                  {/* Status */}
                  <div className="w-24">
                    {getStatusBadge(patient.status)}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {patient.status === 'scheduled' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          checkInPatient(patient.patient_id);
                        }}
                        className="inline-flex items-center gap-1 rounded-lg bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50"
                      >
                        Check In
                      </button>
                    )}
                    {patient.status === 'checked_in' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          updateStatus(patient.patient_id, 'in_progress');
                        }}
                        className="inline-flex items-center gap-1 rounded-lg bg-green-100 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50"
                      >
                        Start Visit
                      </button>
                    )}
                    {patient.status === 'in_progress' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          updateStatus(patient.patient_id, 'completed');
                        }}
                        className="inline-flex items-center gap-1 rounded-lg bg-emerald-100 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:hover:bg-emerald-900/50"
                      >
                        Complete
                      </button>
                    )}
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Voice Commands Help */}
      <div className="rounded-xl bg-gradient-to-r from-mdx-primary/10 to-blue-500/10 p-6 dark:from-mdx-primary/20 dark:to-blue-500/20">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-white p-3 shadow-sm dark:bg-gray-800">
            <Activity className="h-6 w-6 text-mdx-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Voice Commands for Glasses
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Use these voice commands on your AR glasses to manage the worklist hands-free.
            </p>
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-sm">
                <p className="font-medium text-gray-900 dark:text-white">"Show worklist"</p>
                <p className="text-gray-500 dark:text-gray-400">View all patients</p>
              </div>
              <div className="text-sm">
                <p className="font-medium text-gray-900 dark:text-white">"Load 1"</p>
                <p className="text-gray-500 dark:text-gray-400">Load patient by #</p>
              </div>
              <div className="text-sm">
                <p className="font-medium text-gray-900 dark:text-white">"Who's next"</p>
                <p className="text-gray-500 dark:text-gray-400">Next waiting patient</p>
              </div>
              <div className="text-sm">
                <p className="font-medium text-gray-900 dark:text-white">"Check in 2"</p>
                <p className="text-gray-500 dark:text-gray-400">Check in patient #2</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
