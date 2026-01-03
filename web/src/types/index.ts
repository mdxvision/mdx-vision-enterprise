export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'ADMIN' | 'PROVIDER' | 'STAFF';
  specialties: string[];
  npiNumber?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Patient {
  id: string;
  mrn: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  gender: 'MALE' | 'FEMALE' | 'OTHER';
  email?: string;
  phone?: string;
  address?: Address;
  insuranceInfo?: InsuranceInfo;
  createdAt: string;
  updatedAt: string;
}

export interface Address {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

export interface InsuranceInfo {
  provider: string;
  policyNumber: string;
  groupNumber?: string;
}

export interface Encounter {
  id: string;
  patientId: string;
  providerId: string;
  type: EncounterType;
  status: EncounterStatus;
  scheduledAt?: string;
  startedAt?: string;
  endedAt?: string;
  chiefComplaint?: string;
  diagnoses: Diagnosis[];
  createdAt: string;
  updatedAt: string;
}

export type EncounterType =
  | 'INITIAL_CONSULTATION'
  | 'FOLLOW_UP'
  | 'PROCEDURE'
  | 'EMERGENCY'
  | 'TELEMEDICINE';

export type EncounterStatus =
  | 'SCHEDULED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED';

export interface Diagnosis {
  code: string;
  description: string;
  type: 'PRIMARY' | 'SECONDARY';
}

export interface Session {
  id: string;
  encounterId?: string;
  patientId: string;
  providerId: string;
  type: SessionType;
  status: SessionStatus;
  startTime: string;
  endTime?: string;
  durationSeconds?: number;
  transcriptions: Transcription[];
  clinicalNote?: ClinicalNote;
  createdAt: string;
  updatedAt: string;
}

export type SessionType =
  | 'CONSULTATION'
  | 'FOLLOW_UP'
  | 'PROCEDURE_NOTE'
  | 'DISCHARGE'
  | 'REFERRAL';

export type SessionStatus =
  | 'ACTIVE'
  | 'PAUSED'
  | 'COMPLETED'
  | 'CANCELLED';

export interface Transcription {
  id: string;
  sessionId: string;
  text: string;
  speaker: 'PROVIDER' | 'PATIENT' | 'UNKNOWN';
  confidence: number;
  startTime: number;
  endTime: number;
  createdAt: string;
}

export interface ClinicalNote {
  id: string;
  sessionId: string;
  encounterId?: string;
  type: NoteType;
  status: NoteStatus;
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  icdCodes: string[];
  cptCodes: string[];
  medications: Medication[];
  createdAt: string;
  updatedAt: string;
  approvedAt?: string;
  approvedBy?: string;
}

export type NoteType = 'SOAP' | 'PROCEDURE' | 'DISCHARGE' | 'REFERRAL' | 'MEDEVAC';

export type NoteStatus = 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'SIGNED';

export interface Medication {
  name: string;
  dosage: string;
  frequency: string;
  route: string;
  startDate?: string;
  endDate?: string;
}

export interface DrugInteraction {
  id: string;
  drug1: string;
  drug2: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  description: string;
  recommendation: string;
}

export interface DashboardStats {
  totalPatients: number;
  totalSessions: number;
  totalNotes: number;
  sessionsToday: number;
  avgSessionDuration: number;
  pendingReviews: number;
}

export interface PaginatedResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  page: number;
  size: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

// DNFB (Discharged Not Final Billed) Types
export type DNFBReason =
  | 'CODING_INCOMPLETE'
  | 'DOCUMENTATION_MISSING'
  | 'CHARGES_PENDING'
  | 'PRIOR_AUTH_MISSING'
  | 'PRIOR_AUTH_EXPIRED'
  | 'PRIOR_AUTH_DENIED'
  | 'INSURANCE_VERIFICATION'
  | 'CLINICAL_REVIEW'
  | 'PHYSICIAN_QUERY'
  | 'COMPLIANCE_HOLD'
  | 'SYSTEM_ERROR'
  | 'OTHER';

export type PriorAuthStatus =
  | 'NOT_REQUIRED'
  | 'PENDING'
  | 'APPROVED'
  | 'DENIED'
  | 'EXPIRED'
  | 'NOT_OBTAINED';

export type DNFBStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'ESCALATED';

export type AgingBucket = '0-3' | '4-7' | '8-14' | '15-30' | '31+';

export interface PriorAuthInfo {
  authNumber?: string;
  status: PriorAuthStatus;
  requestDate?: string;
  expirationDate?: string;
  denialReason?: string;
  payerName?: string;
  payerPhone?: string;
}

export interface DNFBAccount {
  dnfbId: string;
  patientId: string;
  patientName?: string;
  mrn?: string;
  accountNumber?: string;
  dischargeDate: string;
  reason: DNFBReason;
  status: DNFBStatus;
  priorAuth?: PriorAuthInfo;
  daysSinceDischarge: number;
  agingBucket: AgingBucket;
  estimatedCharges?: number;
  assignedTo?: string;
  notes?: string;
  createdAt: string;
  updatedAt?: string;
  resolvedAt?: string;
  resolvedBy?: string;
  claimId?: string;
}

export interface DNFBSummary {
  totalAccounts: number;
  totalAtRiskRevenue: number;
  byReason: Record<DNFBReason, { count: number; revenue: number }>;
  byAgingBucket: Record<AgingBucket, { count: number; revenue: number }>;
  priorAuthIssues: number;
  priorAuthAtRisk: number;
  avgDaysSinceDischarge: number;
}

export interface DNFBFilters {
  reason?: DNFBReason;
  status?: DNFBStatus;
  agingBucket?: AgingBucket;
  priorAuthStatus?: PriorAuthStatus;
  assignedTo?: string;
  minDays?: number;
  maxDays?: number;
}

// Billing Claim Types
export type ClaimStatus = 'DRAFT' | 'SUBMITTED' | 'ACCEPTED' | 'REJECTED' | 'PAID' | 'DENIED';

export interface DiagnosisCode {
  code: string;
  description: string;
  sequence: number;
  isPrincipal: boolean;
}

export interface ProcedureCode {
  code: string;
  description: string;
  modifiers: string[];
  units: number;
}

export interface ServiceLine {
  lineNumber: number;
  serviceDate: string;
  procedure: ProcedureCode;
  diagnosisPointers: number[];
  chargeAmount: number;
}

export interface BillingClaim {
  claimId: string;
  status: ClaimStatus;
  patientId: string;
  patientName?: string;
  mrn?: string;
  noteId?: string;
  serviceDate: string;
  diagnoses: DiagnosisCode[];
  serviceLines: ServiceLine[];
  totalCharges: number;
  paidAmount?: number;
  denialReason?: string;
  payerName?: string;
  createdAt: string;
  submittedAt?: string;
  paidAt?: string;
}

export interface BillingSummary {
  totalClaims: number;
  totalCharges: number;
  totalPaid: number;
  pendingAmount: number;
  byStatus: Record<ClaimStatus, { count: number; amount: number }>;
  denialRate: number;
  avgDaysToPayment: number;
}
