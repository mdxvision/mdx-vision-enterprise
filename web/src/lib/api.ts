import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (token) {
    config.headers.Authorization = 'Bearer ' + token;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const sessionsApi = {
  getAll: () => api.get('/sessions'),
  getById: (id: string) => api.get('/sessions/' + id),
  create: (data: CreateSessionRequest) => api.post('/sessions', data),
  update: (id: string, data: UpdateSessionRequest) => api.put('/sessions/' + id, data),
  delete: (id: string) => api.delete('/sessions/' + id),
  getTranscriptions: (id: string) => api.get('/sessions/' + id + '/transcriptions'),
  generateNote: (id: string) => api.post('/sessions/' + id + '/generate-note'),
};

export const patientsApi = {
  getAll: (params?: PatientSearchParams) => api.get('/patients', { params }),
  getById: (id: string) => api.get('/patients/' + id),
  create: (data: CreatePatientRequest) => api.post('/patients', data),
  update: (id: string, data: UpdatePatientRequest) => api.put('/patients/' + id, data),
  searchByMrn: (mrn: string) => api.get('/patients/search', { params: { mrn } }),
};

export const encountersApi = {
  getAll: (params?: EncounterSearchParams) => api.get('/encounters', { params }),
  getById: (id: string) => api.get('/encounters/' + id),
  create: (data: CreateEncounterRequest) => api.post('/encounters', data),
  getByPatient: (patientId: string) => api.get('/patients/' + patientId + '/encounters'),
};

export const notesApi = {
  getAll: (params?: NoteSearchParams) => api.get('/notes', { params }),
  getById: (id: string) => api.get('/notes/' + id),
  update: (id: string, data: UpdateNoteRequest) => api.put('/notes/' + id, data),
  approve: (id: string) => api.post('/notes/' + id + '/approve'),
  exportPdf: (id: string) => api.get('/notes/' + id + '/export/pdf', { responseType: 'blob' }),
};

export const analyticsApi = {
  getDashboardStats: () => api.get('/analytics/dashboard'),
  getSessionMetrics: (params?: DateRangeParams) => api.get('/analytics/sessions', { params }),
  getProviderStats: (providerId: string) => api.get('/analytics/providers/' + providerId),
};

interface CreateSessionRequest {
  patientId: string;
  encounterId?: string;
  type: string;
}

interface UpdateSessionRequest {
  status?: string;
  endTime?: string;
}

interface CreatePatientRequest {
  mrn: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  gender: string;
  email?: string;
  phone?: string;
}

interface UpdatePatientRequest extends Partial<CreatePatientRequest> {}

interface CreateEncounterRequest {
  patientId: string;
  type: string;
  scheduledAt?: string;
  chiefComplaint?: string;
}

interface UpdateNoteRequest {
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
}

interface PatientSearchParams {
  search?: string;
  page?: number;
  size?: number;
}

interface EncounterSearchParams {
  patientId?: string;
  status?: string;
  page?: number;
  size?: number;
}

interface NoteSearchParams {
  sessionId?: string;
  status?: string;
  page?: number;
  size?: number;
}

interface DateRangeParams {
  startDate?: string;
  endDate?: string;
}

interface DNFBSearchParams {
  reason?: string;
  status?: string;
  agingBucket?: string;
  priorAuthStatus?: string;
  assignedTo?: string;
  minDays?: number;
  maxDays?: number;
  page?: number;
  size?: number;
}

interface DNFBUpdateRequest {
  status?: string;
  reason?: string;
  assignedTo?: string;
  notes?: string;
}

interface DNFBResolveRequest {
  claimId?: string;
  notes?: string;
}

interface PriorAuthUpdateRequest {
  status: string;
  authNumber?: string;
  expirationDate?: string;
  denialReason?: string;
}

export const dnfbApi = {
  getAll: (params?: DNFBSearchParams) => api.get('/dnfb', { params }),
  getById: (id: string) => api.get('/dnfb/' + id),
  getSummary: () => api.get('/dnfb/summary'),
  update: (id: string, data: DNFBUpdateRequest) => api.put('/dnfb/' + id, data),
  resolve: (id: string, data?: DNFBResolveRequest) => api.post('/dnfb/' + id + '/resolve', data),
  updatePriorAuth: (id: string, data: PriorAuthUpdateRequest) =>
    api.post('/dnfb/' + id + '/prior-auth', data),
  getByPatient: (patientId: string) => api.get('/patients/' + patientId + '/dnfb'),
  getPriorAuthIssues: () => api.get('/dnfb', {
    params: { priorAuthStatus: 'PENDING,DENIED,EXPIRED,NOT_OBTAINED' }
  }),
};

interface BillingSearchParams {
  status?: string;
  patientId?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  size?: number;
}

interface ClaimUpdateRequest {
  diagnoses?: object[];
  serviceLines?: object[];
}

export const billingApi = {
  getAll: (params?: BillingSearchParams) => api.get('/billing/claims', { params }),
  getById: (id: string) => api.get('/billing/claims/' + id),
  getSummary: () => api.get('/billing/summary'),
  create: (data: object) => api.post('/billing/claims', data),
  update: (id: string, data: ClaimUpdateRequest) => api.put('/billing/claims/' + id, data),
  submit: (id: string) => api.post('/billing/claims/' + id + '/submit'),
  getByPatient: (patientId: string) => api.get('/patients/' + patientId + '/claims'),
  searchICD10: (query: string) => api.get('/billing/codes/icd10/search', { params: { q: query } }),
  searchCPT: (query: string) => api.get('/billing/codes/cpt/search', { params: { q: query } }),
};

export default api;
