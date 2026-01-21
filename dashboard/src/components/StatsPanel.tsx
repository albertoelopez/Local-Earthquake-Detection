import React from 'react';

export interface AlertStats {
  totalAlerts: number;
  alertsLast24h: number;
  alertsLastWeek: number;
  alertsByLevel: Record<string, number>;
  averageMagnitude24h: number;
  maxPGA24h: number;
  activeDevices: number;
  totalDevices: number;
}

interface StatsPanelProps {
  stats: AlertStats;
}

const StatCard: React.FC<{
  title: string;
  value: string | number;
  color?: string;
  testId?: string;
}> = ({ title, value, color = '#333', testId }) => (
  <div
    data-testid={testId}
    style={{
      padding: '16px',
      backgroundColor: '#f5f5f5',
      borderRadius: '8px',
      textAlign: 'center',
    }}
  >
    <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>{title}</div>
    <div style={{ fontSize: '24px', fontWeight: 'bold', color }}>{value}</div>
  </div>
);

export const StatsPanel: React.FC<StatsPanelProps> = ({ stats }) => {
  return (
    <div data-testid="stats-panel" style={{ marginBottom: '24px' }}>
      <h2>Statistics</h2>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <StatCard
          testId="stat-total"
          title="Total Alerts"
          value={stats.totalAlerts}
        />
        <StatCard
          testId="stat-24h"
          title="Last 24 Hours"
          value={stats.alertsLast24h}
          color="#FF9800"
        />
        <StatCard
          testId="stat-week"
          title="Last 7 Days"
          value={stats.alertsLastWeek}
          color="#2196F3"
        />
        <StatCard
          testId="stat-avg-mag"
          title="Avg Magnitude (24h)"
          value={stats.averageMagnitude24h.toFixed(2)}
          color="#9C27B0"
        />
        <StatCard
          testId="stat-max-pga"
          title="Max PGA (24h)"
          value={`${stats.maxPGA24h.toFixed(4)} g`}
          color="#F44336"
        />
        <StatCard
          testId="stat-devices"
          title="Active Devices"
          value={`${stats.activeDevices}/${stats.totalDevices}`}
          color="#4CAF50"
        />
      </div>

      {Object.keys(stats.alertsByLevel).length > 0 && (
        <div>
          <h3>Alerts by Level (24h)</h3>
          <div
            style={{
              display: 'flex',
              gap: '8px',
              flexWrap: 'wrap',
            }}
          >
            {Object.entries(stats.alertsByLevel).map(([level, count]) => (
              <div
                key={level}
                data-testid={`level-${level.toLowerCase()}`}
                style={{
                  padding: '8px 16px',
                  borderRadius: '20px',
                  backgroundColor: getLevelColor(level),
                  color: 'white',
                  fontWeight: 'bold',
                }}
              >
                {level}: {count}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const getLevelColor = (level: string): string => {
  switch (level.toUpperCase()) {
    case 'EXTREME':
      return '#D32F2F';
    case 'SEVERE':
      return '#F57C00';
    case 'STRONG':
      return '#FFA000';
    case 'MODERATE':
      return '#FBC02D';
    case 'LIGHT':
      return '#7CB342';
    default:
      return '#9E9E9E';
  }
};

export default StatsPanel;
