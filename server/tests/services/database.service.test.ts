import { DatabaseService } from '../../src/services/database.service';
import { EarthquakeAlert, DeviceStatus } from '../../src/services/mqtt.service';
import winston from 'winston';

const mockLogger = winston.createLogger({
  silent: true
});

describe('DatabaseService', () => {
  let databaseService: DatabaseService;

  beforeEach(async () => {
    databaseService = new DatabaseService(mockLogger);
    await databaseService.connect();
  });

  afterEach(async () => {
    await databaseService.disconnect();
  });

  describe('connection', () => {
    it('should connect successfully', async () => {
      expect(databaseService.isConnected()).toBe(true);
    });

    it('should disconnect successfully', async () => {
      await databaseService.disconnect();
      expect(databaseService.isConnected()).toBe(false);
    });
  });

  describe('saveAlert', () => {
    it('should save an alert and return an ID', async () => {
      const alert: EarthquakeAlert = {
        device_id: 'ESP32_TEST',
        timestamp: Date.now(),
        event: {
          magnitude: 5.5,
          pga: 0.15,
          pgv: 10.5,
          cav: 0.2,
          duration: 15000,
          alert_level: 'MODERATE',
          confirmed: true
        },
        location: { lat: 37.7749, lon: -122.4194 }
      };

      const alertId = await databaseService.saveAlert(alert);
      expect(alertId).toBeDefined();
      expect(alertId).toMatch(/^alert_/);
    });

    it('should retrieve saved alerts', async () => {
      const alert: EarthquakeAlert = {
        device_id: 'ESP32_TEST',
        timestamp: Date.now(),
        event: {
          magnitude: 6.0,
          pga: 0.25,
          pgv: 15.0,
          cav: 0.3,
          duration: 20000,
          alert_level: 'STRONG',
          confirmed: true
        },
        location: { lat: 35.6762, lon: 139.6503 }
      };

      await databaseService.saveAlert(alert);
      const alerts = await databaseService.getRecentAlerts(10);

      expect(alerts.length).toBeGreaterThan(0);
      expect(alerts[0].device_id).toBe('ESP32_TEST');
      expect(alerts[0].event.magnitude).toBe(6.0);
    });
  });

  describe('getRecentAlerts', () => {
    it('should return empty array when no alerts exist', async () => {
      const freshService = new DatabaseService(mockLogger);
      await freshService.connect();

      const alerts = await freshService.getRecentAlerts(10);
      expect(alerts).toEqual([]);

      await freshService.disconnect();
    });

    it('should limit results to specified count', async () => {
      for (let i = 0; i < 5; i++) {
        await databaseService.saveAlert({
          device_id: `ESP32_${i}`,
          timestamp: Date.now(),
          event: {
            magnitude: 4.0 + i,
            pga: 0.1,
            pgv: 5.0,
            cav: 0.1,
            duration: 10000,
            alert_level: 'LIGHT',
            confirmed: true
          },
          location: { lat: 0, lon: 0 }
        });
      }

      const alerts = await databaseService.getRecentAlerts(3);
      expect(alerts.length).toBe(3);
    });
  });

  describe('getAlertsByDevice', () => {
    it('should filter alerts by device ID', async () => {
      await databaseService.saveAlert({
        device_id: 'DEVICE_A',
        timestamp: Date.now(),
        event: {
          magnitude: 5.0,
          pga: 0.1,
          pgv: 5.0,
          cav: 0.1,
          duration: 10000,
          alert_level: 'MODERATE',
          confirmed: true
        },
        location: { lat: 0, lon: 0 }
      });

      await databaseService.saveAlert({
        device_id: 'DEVICE_B',
        timestamp: Date.now(),
        event: {
          magnitude: 4.0,
          pga: 0.05,
          pgv: 3.0,
          cav: 0.05,
          duration: 8000,
          alert_level: 'LIGHT',
          confirmed: true
        },
        location: { lat: 0, lon: 0 }
      });

      const deviceAAlerts = await databaseService.getAlertsByDevice('DEVICE_A', 10);
      expect(deviceAAlerts.every(a => a.device_id === 'DEVICE_A')).toBe(true);
    });
  });

  describe('updateDeviceStatus', () => {
    it('should update device status', async () => {
      const status: DeviceStatus = {
        device_id: 'ESP32_STATUS_TEST',
        status: 'online',
        timestamp: Date.now()
      };

      await databaseService.updateDeviceStatus(status);
      const device = await databaseService.getDeviceStatus('ESP32_STATUS_TEST');

      expect(device).toBeDefined();
      expect(device?.status).toBe('online');
    });

    it('should update existing device status', async () => {
      const device_id = 'ESP32_UPDATE_TEST';

      await databaseService.updateDeviceStatus({
        device_id,
        status: 'online',
        timestamp: Date.now()
      });

      await databaseService.updateDeviceStatus({
        device_id,
        status: 'monitoring',
        timestamp: Date.now()
      });

      const device = await databaseService.getDeviceStatus(device_id);
      expect(device?.status).toBe('monitoring');
    });
  });

  describe('getAllDevices', () => {
    it('should return all devices', async () => {
      await databaseService.updateDeviceStatus({
        device_id: 'DEVICE_1',
        status: 'online',
        timestamp: Date.now()
      });

      await databaseService.updateDeviceStatus({
        device_id: 'DEVICE_2',
        status: 'online',
        timestamp: Date.now()
      });

      const devices = await databaseService.getAllDevices();
      expect(devices.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('getOnlineDevices', () => {
    it('should return only devices seen in last 5 minutes', async () => {
      await databaseService.updateDeviceStatus({
        device_id: 'RECENT_DEVICE',
        status: 'online',
        timestamp: Date.now()
      });

      const onlineDevices = await databaseService.getOnlineDevices();
      expect(onlineDevices.some(d => d.device_id === 'RECENT_DEVICE')).toBe(true);
    });
  });

  describe('getAlertStats', () => {
    it('should return statistics object', async () => {
      await databaseService.saveAlert({
        device_id: 'STATS_TEST',
        timestamp: Date.now(),
        event: {
          magnitude: 5.5,
          pga: 0.15,
          pgv: 10.0,
          cav: 0.2,
          duration: 15000,
          alert_level: 'MODERATE',
          confirmed: true
        },
        location: { lat: 0, lon: 0 }
      });

      const stats = await databaseService.getAlertStats();

      expect(stats).toHaveProperty('totalAlerts');
      expect(stats).toHaveProperty('alertsLast24h');
      expect(stats).toHaveProperty('alertsLastWeek');
      expect(stats).toHaveProperty('alertsByLevel');
      expect(stats).toHaveProperty('averageMagnitude24h');
      expect(stats).toHaveProperty('maxPGA24h');
      expect(stats).toHaveProperty('activeDevices');
      expect(stats).toHaveProperty('totalDevices');
    });
  });
});
