import { Logger } from 'winston';
import { EarthquakeAlert, DeviceStatus } from './mqtt.service';

interface StoredAlert extends EarthquakeAlert {
  _id: string;
  createdAt: Date;
}

interface StoredDevice {
  device_id: string;
  status: string;
  lastSeen: Date;
  location?: {
    lat: number;
    lon: number;
  };
}

export class DatabaseService {
  private logger: Logger;
  private alerts: StoredAlert[] = [];
  private devices: Map<string, StoredDevice> = new Map();
  private connected: boolean = false;

  constructor(logger: Logger) {
    this.logger = logger;
  }

  async connect(): Promise<void> {
    this.connected = true;
    this.logger.info('Database service initialized (in-memory mode)');
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    this.logger.info('Database service disconnected');
  }

  isConnected(): boolean {
    return this.connected;
  }

  async saveAlert(alert: EarthquakeAlert): Promise<string> {
    const storedAlert: StoredAlert = {
      ...alert,
      _id: `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date()
    };

    this.alerts.unshift(storedAlert);

    if (this.alerts.length > 1000) {
      this.alerts = this.alerts.slice(0, 1000);
    }

    this.logger.debug('Alert saved', { id: storedAlert._id });
    return storedAlert._id;
  }

  async getRecentAlerts(limit: number = 50): Promise<EarthquakeAlert[]> {
    return this.alerts.slice(0, limit);
  }

  async getAlertsByDevice(deviceId: string, limit: number = 20): Promise<EarthquakeAlert[]> {
    return this.alerts
      .filter(alert => alert.device_id === deviceId)
      .slice(0, limit);
  }

  async getAlertById(alertId: string): Promise<StoredAlert | null> {
    return this.alerts.find(alert => alert._id === alertId) || null;
  }

  async updateDeviceStatus(status: DeviceStatus): Promise<void> {
    const device = this.devices.get(status.device_id);

    if (device) {
      device.status = status.status;
      device.lastSeen = new Date(status.timestamp);
    } else {
      this.devices.set(status.device_id, {
        device_id: status.device_id,
        status: status.status,
        lastSeen: new Date(status.timestamp)
      });
    }

    this.logger.debug('Device status updated', { deviceId: status.device_id, status: status.status });
  }

  async getDeviceStatus(deviceId: string): Promise<StoredDevice | null> {
    return this.devices.get(deviceId) || null;
  }

  async getAllDevices(): Promise<StoredDevice[]> {
    return Array.from(this.devices.values());
  }

  async getOnlineDevices(): Promise<StoredDevice[]> {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    return Array.from(this.devices.values())
      .filter(device => device.lastSeen > fiveMinutesAgo);
  }

  async getAlertStats(): Promise<object> {
    const now = new Date();
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    const alertsLast24h = this.alerts.filter(a => a.createdAt > oneDayAgo);
    const alertsLastWeek = this.alerts.filter(a => a.createdAt > oneWeekAgo);

    const alertsByLevel: Record<string, number> = {};
    alertsLast24h.forEach(alert => {
      const level = alert.event.alert_level;
      alertsByLevel[level] = (alertsByLevel[level] || 0) + 1;
    });

    const avgMagnitude = alertsLast24h.length > 0
      ? alertsLast24h.reduce((sum, a) => sum + a.event.magnitude, 0) / alertsLast24h.length
      : 0;

    const maxPGA = alertsLast24h.length > 0
      ? Math.max(...alertsLast24h.map(a => a.event.pga))
      : 0;

    return {
      totalAlerts: this.alerts.length,
      alertsLast24h: alertsLast24h.length,
      alertsLastWeek: alertsLastWeek.length,
      alertsByLevel,
      averageMagnitude24h: avgMagnitude,
      maxPGA24h: maxPGA,
      activeDevices: (await this.getOnlineDevices()).length,
      totalDevices: this.devices.size
    };
  }

  async clearOldAlerts(olderThanDays: number = 30): Promise<number> {
    const cutoffDate = new Date(Date.now() - olderThanDays * 24 * 60 * 60 * 1000);
    const initialCount = this.alerts.length;
    this.alerts = this.alerts.filter(alert => alert.createdAt > cutoffDate);
    return initialCount - this.alerts.length;
  }
}
