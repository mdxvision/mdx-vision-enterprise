/**
 * Session State Store - Manages active recording session
 */

import { create } from 'zustand';

interface Transcription {
  id: string;
  text: string;
  speakerLabel: string;
  isFinal: boolean;
  timestamp: number;
}

interface SessionState {
  // Session info
  sessionId: string | null;
  encounterId: string | null;
  patientId: string | null;
  patientName: string | null;
  
  // Recording state
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  
  // Transcriptions
  transcriptions: Transcription[];
  currentTranscript: string;
  
  // AI suggestions
  noteSuggestion: string | null;
  drugAlerts: any[];
  
  // Settings
  languageCode: string;
  translationTarget: string | null;
  transcriptionEnabled: boolean;
  aiSuggestionsEnabled: boolean;
  
  // Actions
  startSession: (data: {
    sessionId: string;
    encounterId?: string;
    patientId?: string;
    patientName?: string;
  }) => void;
  endSession: () => void;
  pauseSession: () => void;
  resumeSession: () => void;
  addTranscription: (transcription: Transcription) => void;
  setCurrentTranscript: (text: string) => void;
  setNoteSuggestion: (note: string) => void;
  addDrugAlert: (alert: any) => void;
  clearDrugAlerts: () => void;
  updateDuration: (seconds: number) => void;
  setSettings: (settings: Partial<Pick<SessionState, 'languageCode' | 'translationTarget' | 'transcriptionEnabled' | 'aiSuggestionsEnabled'>>) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  encounterId: null,
  patientId: null,
  patientName: null,
  isRecording: false,
  isPaused: false,
  duration: 0,
  transcriptions: [],
  currentTranscript: '',
  noteSuggestion: null,
  drugAlerts: [],
  languageCode: 'en-US',
  translationTarget: null,
  transcriptionEnabled: true,
  aiSuggestionsEnabled: true,
};

export const useSessionStore = create<SessionState>((set, get) => ({
  ...initialState,

  startSession: (data) => set({
    sessionId: data.sessionId,
    encounterId: data.encounterId || null,
    patientId: data.patientId || null,
    patientName: data.patientName || null,
    isRecording: true,
    isPaused: false,
    duration: 0,
    transcriptions: [],
    currentTranscript: '',
  }),

  endSession: () => set({
    isRecording: false,
    isPaused: false,
  }),

  pauseSession: () => set({ isPaused: true }),

  resumeSession: () => set({ isPaused: false }),

  addTranscription: (transcription) => set((state) => ({
    transcriptions: [...state.transcriptions, transcription],
  })),

  setCurrentTranscript: (text) => set({ currentTranscript: text }),

  setNoteSuggestion: (note) => set({ noteSuggestion: note }),

  addDrugAlert: (alert) => set((state) => ({
    drugAlerts: [...state.drugAlerts, alert],
  })),

  clearDrugAlerts: () => set({ drugAlerts: [] }),

  updateDuration: (seconds) => set({ duration: seconds }),

  setSettings: (settings) => set(settings),

  reset: () => set(initialState),
}));
