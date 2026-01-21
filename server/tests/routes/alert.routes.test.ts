import express from 'express';
import request from 'supertest';
import { alertRoutes } from '../../src/routes/alert.routes';
import { AlertService } from '../../src/services/alert.service';
import { DatabaseService } from '../../src/services/database.service';
import winston from 'winston';

const mockLogger = winston.createLogger({
  silent: true
});

describe('Alert Routes', () => {
  let app: express.Application;
  let alertService: AlertService;
  let databaseService: DatabaseService;

  beforeEach(async () => {
    databaseService = new DatabaseService(mockLogger);
    await databaseService.connect();
    alertService = new AlertService(databaseService, mockLogger);

    app = express();
    app.use(express.json());
    app.use('/api/alerts', alertRoutes(alertService));
  });

  afterEach(async () => {
    await databaseService.disconnect();
  });

  describe('GET /api/alerts', () => {
    it('should return alerts with success response', async () => {
      const response = await request(app)
        .get('/api/alerts')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body).toHaveProperty('count');
      expect(response.body).toHaveProperty('data');
      expect(Array.isArray(response.body.data)).toBe(true);
    });

    it('should respect limit query parameter', async () => {
      for (let i = 0; i < 10; i++) {
        await databaseService.saveAlert({
          device_id: `ESP32_ROUTE_TEST_${i}`,
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

      const response = await request(app)
        .get('/api/alerts?limit=5')
        .expect(200);

      expect(response.body.count).toBeLessThanOrEqual(5);
    });
  });

  describe('GET /api/alerts/device/:deviceId', () => {
    it('should return alerts for specific device', async () => {
      const deviceId = 'ESP32_DEVICE_ROUTE_TEST';

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

      const response = await request(app)
        .get(`/api/alerts/device/${deviceId}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.every((a: any) => a.device_id === deviceId)).toBe(true);
    });
  });

  describe('GET /api/alerts/stats', () => {
    it('should return statistics', async () => {
      const response = await request(app)
        .get('/api/alerts/stats')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty('totalAlerts');
      expect(response.body.data).toHaveProperty('alertsLast24h');
    });
  });
});
