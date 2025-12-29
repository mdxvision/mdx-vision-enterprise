/**
 * Navigation Types for MDx Vision
 */

export type RootStackParamList = {
  Login: undefined;
  MainTabs: undefined;
  PatientDetail: { patientId: string };
  SessionRecording: { sessionId: string; patientId?: string; patientName?: string };
  Notes: { encounterId: string };
};

export type MainTabParamList = {
  Home: undefined;
  Patients: undefined;
  Session: undefined;
  Settings: undefined;
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
