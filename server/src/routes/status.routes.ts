import { Router, Request, Response } from 'express';
import { MQTTService } from '../services/mqtt.service';
import { DatabaseService } from '../services/database.service';

export function statusRoutes(mqttService: MQTTService, databaseService: DatabaseService): Router {
  const router = Router();

  router.get('/', async (req: Request, res: Response) => {
    try {
      const devices = await databaseService.getAllDevices();
      const onlineDevices = await databaseService.getOnlineDevices();

      res.json({
        success: true,
        mqtt: {
          connected: mqttService.isConnected()
        },
        database: {
          connected: databaseService.isConnected()
        },
        devices: {
          total: devices.length,
          online: onlineDevices.length,
          list: devices
        }
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to fetch status'
      });
    }
  });

  router.get('/devices', async (req: Request, res: Response) => {
    try {
      const devices = await databaseService.getAllDevices();
      res.json({
        success: true,
        count: devices.length,
        data: devices
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to fetch devices'
      });
    }
  });

  router.get('/devices/:deviceId', async (req: Request, res: Response) => {
    try {
      const { deviceId } = req.params;
      const device = await databaseService.getDeviceStatus(deviceId);

      if (device) {
        res.json({
          success: true,
          data: device
        });
      } else {
        res.status(404).json({
          success: false,
          error: 'Device not found'
        });
      }
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to fetch device status'
      });
    }
  });

  router.post('/devices/:deviceId/command', async (req: Request, res: Response) => {
    try {
      const { deviceId } = req.params;
      const { command } = req.body;

      if (!command) {
        return res.status(400).json({
          success: false,
          error: 'Command is required'
        });
      }

      mqttService.publish(`earthquake/command/${deviceId}`, { command });

      res.json({
        success: true,
        message: `Command '${command}' sent to device ${deviceId}`
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to send command'
      });
    }
  });

  return router;
}
