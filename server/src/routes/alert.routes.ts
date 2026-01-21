import { Router, Request, Response } from 'express';
import { AlertService } from '../services/alert.service';

export function alertRoutes(alertService: AlertService): Router {
  const router = Router();

  router.get('/', async (req: Request, res: Response) => {
    try {
      const limit = parseInt(req.query.limit as string) || 50;
      const alerts = await alertService.getRecentAlerts(limit);
      res.json({
        success: true,
        count: alerts.length,
        data: alerts
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to fetch alerts'
      });
    }
  });

  router.get('/device/:deviceId', async (req: Request, res: Response) => {
    try {
      const { deviceId } = req.params;
      const limit = parseInt(req.query.limit as string) || 20;
      const alerts = await alertService.getAlertsByDevice(deviceId, limit);
      res.json({
        success: true,
        count: alerts.length,
        data: alerts
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to fetch device alerts'
      });
    }
  });

  router.get('/stats', async (req: Request, res: Response) => {
    try {
      const stats = await alertService.getAlertStats();
      res.json({
        success: true,
        data: stats
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to fetch alert stats'
      });
    }
  });

  return router;
}
