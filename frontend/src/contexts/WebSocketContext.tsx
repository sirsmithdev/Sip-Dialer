import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import { useWebSocket, WSMessage, MessageHandler } from '@/hooks/use-websocket';
import { useAuth } from '@/hooks/use-auth';
import { sipSettingsApi } from '@/services/api';

// Dashboard stats type
export interface DashboardStats {
  active_campaigns: number;
  calls_today: number;
  calls_answered: number;
  answer_rate: number;
  total_contacts: number;
  completed_campaigns: number;
  avg_call_duration: number;
  sip_status: string;
  sip_extension?: string;
}

// SIP status type
export interface SIPStatus {
  status: string;
  extension?: string;
  server?: string;
  active_calls: number;
  error?: string;
  last_updated?: string;
}

// Campaign progress type
export interface CampaignProgress {
  campaign_id: string;
  campaign_name?: string;
  status: string;
  total_contacts: number;
  contacts_called: number;
  contacts_answered: number;
  contacts_completed: number;
  contacts_failed: number;
  contacts_pending: number;
  answer_rate: number;
  calls_per_minute: number;
}

// Call update type
export interface CallUpdate {
  call_id: string;
  campaign_id?: string;
  contact_id?: string;
  phone_number: string;
  status: string;
  direction: string;
  duration_seconds: number;
  amd_result?: string;
  ivr_node?: string;
  can_transfer: boolean;
  started_at?: string;
}

interface WebSocketContextValue {
  isConnected: boolean;
  error: string | null;
  sipStatus: SIPStatus | null;
  dashboardStats: DashboardStats | null;
  subscribe: (type: string, handler: MessageHandler) => () => void;
  send: (message: WSMessage) => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const { isConnected, error, subscribe, send, connect, disconnect } = useWebSocket({
    autoConnect: false, // We'll connect manually when user is authenticated
    reconnect: true,
    reconnectDelay: 3000,
    maxReconnectAttempts: 10,
  });

  const [sipStatus, setSipStatus] = useState<SIPStatus | null>(null);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);

  // Fetch initial SIP status from REST API
  const fetchInitialSipStatus = useCallback(async () => {
    try {
      const response = await sipSettingsApi.getDialerStatus();
      if (response.sip) {
        setSipStatus({
          status: response.sip.status,
          extension: response.sip.extension,
          server: response.sip.server,
          active_calls: response.sip.active_calls || 0,
          error: response.sip.error,
          last_updated: new Date().toISOString(),
        });
      }
    } catch (error) {
      // If fetching fails, SIP status remains unknown - this is expected
      // when the dialer isn't running or user lacks permissions
      console.debug('Could not fetch initial SIP status:', error);
    }
  }, []);

  // Connect/disconnect based on authentication
  useEffect(() => {
    if (user) {
      connect();
      // Fetch initial SIP status when connecting
      fetchInitialSipStatus();
    } else {
      disconnect();
      setSipStatus(null);
      setDashboardStats(null);
    }
  }, [user, connect, disconnect, fetchInitialSipStatus]);

  // Subscribe to SIP status updates
  useEffect(() => {
    const unsubscribe = subscribe('sip.status', (message) => {
      if (message.data) {
        setSipStatus(message.data as unknown as SIPStatus);
      }
    });

    return unsubscribe;
  }, [subscribe]);

  // Subscribe to dashboard stats updates
  useEffect(() => {
    const unsubscribe = subscribe('dashboard.stats', (message) => {
      if (message.data) {
        setDashboardStats(message.data as unknown as DashboardStats);
      }
    });

    return unsubscribe;
  }, [subscribe]);

  const value = useMemo(
    () => ({
      isConnected,
      error,
      sipStatus,
      dashboardStats,
      subscribe,
      send,
    }),
    [isConnected, error, sipStatus, dashboardStats, subscribe, send]
  );

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
}

// Hook for subscribing to campaign progress updates
export function useCampaignProgress(campaignId: string | null) {
  const { subscribe } = useWebSocketContext();
  const [progress, setProgress] = useState<CampaignProgress | null>(null);

  useEffect(() => {
    if (!campaignId) {
      setProgress(null);
      return;
    }

    const unsubscribe = subscribe('campaign.progress', (message) => {
      const data = message.data as unknown as CampaignProgress;
      if (data?.campaign_id === campaignId) {
        setProgress(data);
      }
    });

    return unsubscribe;
  }, [campaignId, subscribe]);

  return progress;
}

// Hook for subscribing to call updates
export function useCallUpdates(callback: (call: CallUpdate) => void) {
  const { subscribe } = useWebSocketContext();

  useEffect(() => {
    const unsubscribe = subscribe('call.update', (message) => {
      if (message.data) {
        callback(message.data as unknown as CallUpdate);
      }
    });

    return unsubscribe;
  }, [subscribe, callback]);
}

// Hook for SIP status
export function useSIPStatus() {
  const { sipStatus } = useWebSocketContext();
  return sipStatus;
}
