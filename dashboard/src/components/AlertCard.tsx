import React from 'react';

export interface EarthquakeAlert {
  device_id: string;
  timestamp: number;
  event: {
    magnitude: number;
    pga: number;
    pgv: number;
    cav: number;
    duration: number;
    alert_level: string;
    confirmed: boolean;
  };
  location: {
    lat: number;
    lon: number;
  };
}

interface AlertCardProps {
  alert: EarthquakeAlert;
}

const getAlertColor = (level: string): string => {
  switch (level.toUpperCase()) {
    case 'EXTREME':
      return '#FF0000';
    case 'SEVERE':
      return '#FF4500';
    case 'STRONG':
      return '#FFA500';
    case 'MODERATE':
      return '#FFD700';
    case 'LIGHT':
      return '#90EE90';
    default:
      return '#98FB98';
  }
};

export const AlertCard: React.FC<AlertCardProps> = ({ alert }) => {
  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleString();
  };

  const alertColor = getAlertColor(alert.event.alert_level);

  return (
    <div
      data-testid="alert-card"
      style={{
        border: `3px solid ${alertColor}`,
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '16px',
        backgroundColor: `${alertColor}15`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, color: alertColor }}>
          {alert.event.alert_level} - M{alert.event.magnitude.toFixed(1)}
        </h3>
        {alert.event.confirmed && (
          <span
            data-testid="confirmed-badge"
            style={{
              backgroundColor: '#4CAF50',
              color: 'white',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '12px',
            }}
          >
            CONFIRMED
          </span>
        )}
      </div>

      <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <div>
          <strong>PGA:</strong> {alert.event.pga.toFixed(4)} g
        </div>
        <div>
          <strong>PGV:</strong> {alert.event.pgv.toFixed(2)} cm/s
        </div>
        <div>
          <strong>CAV:</strong> {alert.event.cav.toFixed(4)} g·s
        </div>
        <div>
          <strong>Duration:</strong> {(alert.event.duration / 1000).toFixed(1)}s
        </div>
        <div>
          <strong>Location:</strong> {alert.location.lat.toFixed(4)}, {alert.location.lon.toFixed(4)}
        </div>
        <div>
          <strong>Device:</strong> {alert.device_id}
        </div>
      </div>

      <div style={{ marginTop: '12px', fontSize: '12px', color: '#666' }}>
        {formatDate(alert.timestamp)}
      </div>
    </div>
  );
};

export default AlertCard;
