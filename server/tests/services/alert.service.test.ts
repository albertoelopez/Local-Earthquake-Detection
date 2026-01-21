import { AlertService } from '../../src/services/alert.service';
import { DatabaseService } from '../../src/services/database.service';
import { EarthquakeAlert } from '../../src/services/mqtt.service';
import winston from 'winston';

const mockLogger = winston.createLogger({
  silent: true
});

describe('AlertService', () => {
  let alertService: AlertService;
  let databaseService: DatabaseService;

  beforeEach(async () => {
    databaseService = new DatabaseService(mockLogger);
    await databaseService.connect();
    alertService = new AlertService(databaseService, mockLogger);
  });

  afterEach(async () => {
    await databaseService.disconnect();
  });

  describe('processAlert', () => {
    it('should save alert to database', async () => {
      const alert: EarthquakeAlert = {
        device_id: 'ESP32_PROCESS_TEST',
        timestamp: Date.now(),
        event: {
          magnitude: 4.5,
          pga: 0.08,
          pgv: 5.0,
          cav: 0.1,
          duration: 10000,
          alert_level: 'LIGHT',
          confirmed: true
        },
        location: { lat: 37.7749, lon: -122.4194 }
      };

      await alertService.processAlert(alert);

      const alerts = await alertService.getRecentAlerts(10);
      expect(alerts.some(a => a.device_id === 'ESP32_PROCESS_TEST')).toBe(true);
    });

    it('should process confirmed earthquake alerts', async () => {
      const alert: EarthquakeAlert = {
        device_id: 'ESP32_CONFIRMED_TEST',
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

      await expect(alertService.processAlert(alert)).resolves.not.toThrow();
    });

    it('should handle unconfirmed alerts', async () => {
      const alert: EarthquakeAlert = {
        device_id: 'ESP32_UNCONFIRMED_TEST',
        timestamp: Date.now(),
        event: {
          magnitude: 3.0,
          pga: 0.02,
          pgv: 2.0,
          cav: 0.02,
          duration: 3000,
          alert_level: 'NEGLIGIBLE',
          confirmed: false
        },
        location: { lat: 0, lon: 0 }
      };

      await expect(alertService.processAlert(alert)).resolves.not.toThrow();
    });
  });

  describe('getRecentAlerts', () => {
    it('should return recent alerts with default limit', async () => {
      const alerts = await alertService.getRecentAlerts();
      expect(Array.isArray(alerts)).toBe(true);
    });

    it('should respect custom limit', async () => {
      for (let i = 0; i < 10; i++) {
        await databaseService.saveAlert({
          device_id: `ESP32_LIMIT_TEST_${i}`,
          timestamp: Date.now(),
          event: {
            magnitude: 4.0,
            pga: 0.05,
            pgv: 3.0,
            cav: 0.05,
            duration: 5000,
            alert_level: 'LIGHT',
            confirmed: true
          },
          location: { lat: 0, lon: 0 }
        });
      }

      const alerts = await alertService.getRecentAlerts(5);
      expect(alerts.length).toBeLessThanOrEqual(5);
    });
  });

  describe('getAlertsByDevice', () => {
    it('should return alerts for specific device', async () => {
      const deviceId = 'ESP32_SPECIFIC_DEVICE';

      await databaseService.saveAlert({
        device_id: deviceId,
        timestamp: Date.now(),
        event: {
          magnitude: 5.0,
          pga: 0.1,
          pgv: 7.0,
          cav: 0.15,
          duration: 12000,
          alert_level: 'MODERATE',
          confirmed: true
        },
        location: { lat: 0, lon: 0 }
      });

      const alerts = await alertService.getAlertsByDevice(deviceId);
      expect(alerts.every(a => a.device_id === deviceId)).toBe(true);
    });
  });

  describe('getAlertStats', () => {
    it('should return statistics', async () => {
      const stats = await alertService.getAlertStats();

      expect(stats).toBeDefined();
      expect(typeof stats).toBe('object');
    });
  });
});
