'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

// API base URL - convert http to ws
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';
const WS_URL = API_URL.replace('http://', 'ws://').replace('https://', 'wss://');

export interface SyncEvent {
  type: string;
  data: any;
  timestamp: string;
}

export interface WorklistUpdateEvent {
  action: 'check_in' | 'status_change' | 'patient_loaded';
  patient: {
    patient_id: string;
    name: string;
    status: string;
    room?: string;
    [key: string]: any;
  };
}

interface UseSyncWebSocketOptions {
  onWorklistUpdate?: (event: WorklistUpdateEvent) => void;
  onPatientLoaded?: (patientId: string, patientName: string) => void;
  onMinervaResponse?: (response: string, patientId: string) => void;
  onAnyEvent?: (event: SyncEvent) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export function useSyncWebSocket(options: UseSyncWebSocketOptions = {}) {
  const {
    onWorklistUpdate,
    onPatientLoaded,
    onMinervaResponse,
    onAnyEvent,
    autoReconnect = true,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SyncEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(`${WS_URL}/ws/sync`);

      ws.onopen = () => {
        console.log('Sync WebSocket connected');
        setIsConnected(true);
      };

      ws.onclose = () => {
        console.log('Sync WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Auto-reconnect
        if (autoReconnect) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...');
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        console.error('Sync WebSocket error:', error);
      };

      ws.onmessage = (event) => {
        try {
          const data: SyncEvent = JSON.parse(event.data);
          setLastEvent(data);

          // Call generic handler
          onAnyEvent?.(data);

          // Call specific handlers based on event type
          switch (data.type) {
            case 'worklist_update':
              onWorklistUpdate?.(data.data as WorklistUpdateEvent);
              break;

            case 'patient_loaded':
              onPatientLoaded?.(data.data.patient_id, data.data.patient_name);
              break;

            case 'minerva_response':
              onMinervaResponse?.(data.data.response, data.data.patient_id);
              break;
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, [autoReconnect, reconnectInterval, onWorklistUpdate, onPatientLoaded, onMinervaResponse, onAnyEvent]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendEvent = useCallback((type: string, data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, data }));
    } else {
      console.warn('WebSocket not connected, cannot send event');
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastEvent,
    sendEvent,
    connect,
    disconnect,
  };
}
