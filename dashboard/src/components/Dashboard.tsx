import React, { useState, useEffect, useCallback } from 'react';
import { AlertCard, EarthquakeAlert } from './AlertCard';
import { StatsPanel, AlertStats } from './StatsPanel';

interface DashboardProps {
  serverUrl?: string;
  wsUrl?: string;
}

export const Dashboard: React.FC<DashboardProps> = ({
  serverUrl = 'http://localhost:3000',
  wsUrl = 'ws://localhost:3000',
}) => {
  const [alerts, setAlerts] = useState<EarthquakeAlert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAlerts = useCallback(async () => {
    try {
      const response = await fetch(`${serverUrl}/api/alerts?limit=50`);
      const data = await response.json();
      if (data.success) {
        setAlerts(data.data);
      }
    } catch (err) {
      setError('Failed to fetch alerts');
    }
  }, [serverUrl]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${serverUrl}/api/alerts/stats`);
      const data = await response.json();
      if (data.success) {
        setStats(data.data);
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, [serverUrl]);

  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      await Promise.all([fetchAlerts(), fetchStats()]);
      setLoading(false);
    };

    loadInitialData();
  }, [fetchAlerts, fetchStats]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        ws?.send(JSON.stringify({ type: 'subscribe', topic: 'earthquake/alert' }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === 'earthquake_alert') {
            setAlerts((prev) => [message.data, ...prev].slice(0, 50));

            if (message.data.event.alert_level === 'SEVERE' ||
                message.data.event.alert_level === 'EXTREME') {
              if (Notification.permission === 'granted') {
                new Notification('Earthquake Alert!', {
                  body: `Magnitude ${message.data.event.magnitude.toFixed(1)} - ${message.data.event.alert_level}`,
                });
              }
            }

            fetchStats();
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        reconnectTimeout = setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
        setConnected(false);
      };
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [wsUrl, fetchStats]);

  useEffect(() => {
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  if (loading) {
    return (
      <div data-testid="loading" style={{ padding: '20px', textAlign: 'center' }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0 }}>Earthquake Monitoring Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
          <span
            data-testid="connection-status"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 8px',
              borderRadius: '4px',
              backgroundColor: connected ? '#E8F5E9' : '#FFEBEE',
              color: connected ? '#2E7D32' : '#C62828',
            }}
          >
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: connected ? '#4CAF50' : '#F44336',
              }}
            />
            {connected ? 'Connected' : 'Disconnected'}
          </span>
          {error && (
            <span data-testid="error-message" style={{ color: '#C62828' }}>
              {error}
            </span>
          )}
        </div>
      </header>

      {stats && <StatsPanel stats={stats} />}

      <section>
        <h2>Recent Alerts ({alerts.length})</h2>
        {alerts.length === 0 ? (
          <p data-testid="no-alerts">No earthquake alerts recorded yet.</p>
        ) : (
          <div data-testid="alerts-list">
            {alerts.map((alert, index) => (
              <AlertCard key={`${alert.device_id}-${alert.timestamp}-${index}`} alert={alert} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default Dashboard;
