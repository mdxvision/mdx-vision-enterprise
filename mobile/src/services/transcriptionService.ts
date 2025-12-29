/**
 * Transcription Service
 * Handles WebSocket connection for real-time transcription
 */

import { Platform } from 'react-native';
import LiveAudioStream from 'react-native-live-audio-stream';

interface TranscriptionData {
  text: string;
  speakerLabel?: string;
  isFinal: boolean;
  confidence?: number;
  offsetMs?: number;
}

type TranscriptionCallback = (data: TranscriptionData) => void;

export class TranscriptionService {
  private sessionId: string;
  private websocket: WebSocket | null = null;
  private isConnected = false;
  private isRecording = false;
  
  public onTranscription: TranscriptionCallback | null = null;
  public onError: ((error: Error) => void) | null = null;
  public onConnectionChange: ((connected: boolean) => void) | null = null;

  private readonly wsUrl: string;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
    // Use environment variable or config
    const baseUrl = __DEV__ 
      ? 'ws://localhost:8000' 
      : 'wss://api.mdx.vision';
    this.wsUrl = `${baseUrl}/v1/transcription/ws/${sessionId}`;
  }

  async connect(): Promise<void> {
    try {
      // Initialize audio stream
      await this.initializeAudioStream();

      // Connect WebSocket
      this.websocket = new WebSocket(this.wsUrl);

      this.websocket.onopen = () => {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.onConnectionChange?.(true);
        this.startRecording();
      };

      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'transcription' && this.onTranscription) {
            this.onTranscription({
              text: data.text,
              speakerLabel: data.speakerLabel,
              isFinal: data.isFinal,
              confidence: data.confidence,
              offsetMs: data.offsetMs,
            });
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };

      this.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.onError?.(new Error('WebSocket connection error'));
      };

      this.websocket.onclose = () => {
        console.log('WebSocket closed');
        this.isConnected = false;
        this.onConnectionChange?.(false);
        this.stopRecording();
      };

    } catch (error) {
      console.error('Connection error:', error);
      this.onError?.(error as Error);
    }
  }

  private async initializeAudioStream(): Promise<void> {
    const options = {
      sampleRate: 16000,  // AssemblyAI requires 16kHz
      channels: 1,        // Mono
      bitsPerSample: 16,
      audioSource: 6,     // VOICE_RECOGNITION on Android
    };

    LiveAudioStream.init(options);

    LiveAudioStream.on('data', (data: string) => {
      if (this.isRecording && this.websocket?.readyState === WebSocket.OPEN) {
        // Convert base64 to binary and send
        const binaryData = this.base64ToArrayBuffer(data);
        this.websocket.send(binaryData);
      }
    });
  }

  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }

  private startRecording(): void {
    if (!this.isRecording) {
      LiveAudioStream.start();
      this.isRecording = true;
      console.log('Audio recording started');
    }
  }

  private stopRecording(): void {
    if (this.isRecording) {
      LiveAudioStream.stop();
      this.isRecording = false;
      console.log('Audio recording stopped');
    }
  }

  pause(): void {
    this.stopRecording();
  }

  resume(): void {
    if (this.isConnected) {
      this.startRecording();
    }
  }

  async disconnect(): Promise<void> {
    this.stopRecording();
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
    this.isConnected = false;
  }
}
