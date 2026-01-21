import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { createServer } from 'http';
import { WebSocket, WebSocketServer } from 'ws';
import { MQTTService } from './services/mqtt.service';
import { AlertService } from './services/alert.service';
import { DatabaseService } from './services/database.service';
import { createLogger } from './utils/logger';
import { alertRoutes } from './routes/alert.routes';
import { statusRoutes } from './routes/status.routes';
import dotenv from 'dotenv';

dotenv.config();

const logger = createLogger('Main');
const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

app.use(helmet());
app.use(cors());
app.use(express.json());

const mqttService = new MQTTService(
  process.env.MQTT_BROKER || 'mqtt://broker.hivemq.com',
  logger
);

const databaseService = new DatabaseService(logger);
const alertService = new AlertService(databaseService, logger);

app.use('/api/alerts', alertRoutes(alertService));
app.use('/api/status', statusRoutes(mqttService, databaseService));

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    mqtt: mqttService.isConnected() ? 'connected' : 'disconnected'
  });
});

const clients: Set<WebSocket> = new Set();

wss.on('connection', (ws: WebSocket) => {
  logger.info('WebSocket client connected');
  clients.add(ws);

  ws.send(JSON.stringify({
    type: 'connection',
    message: 'Connected to earthquake monitoring system',
    timestamp: new Date().toISOString()
  }));

  ws.on('message', (message: string) => {
    try {
      const data = JSON.parse(message.toString());
      logger.debug('WebSocket message received', data);

      if (data.type === 'subscribe') {
        mqttService.subscribe(data.topic);
      }
    } catch (error) {
      logger.error('Failed to parse WebSocket message', error);
    }
  });

  ws.on('close', () => {
    logger.info('WebSocket client disconnected');
    clients.delete(ws);
  });

  ws.on('error', (error) => {
    logger.error('WebSocket error', error);
    clients.delete(ws);
  });
});

function broadcastToClients(data: object): void {
  const message = JSON.stringify(data);
  clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

mqttService.on('alert', async (alert) => {
  logger.info('Earthquake alert received', alert);

  await databaseService.saveAlert(alert);

  await alertService.processAlert(alert);

  broadcastToClients({
    type: 'earthquake_alert',
    data: alert,
    timestamp: new Date().toISOString()
  });
});

mqttService.on('data', (data) => {
  broadcastToClients({
    type: 'sensor_data',
    data: data,
    timestamp: new Date().toISOString()
  });
});

mqttService.on('status', async (status) => {
  logger.debug('Device status update', status);
  await databaseService.updateDeviceStatus(status);
});

async function start(): Promise<void> {
  try {
    await databaseService.connect();
    logger.info('Database connected');

    await mqttService.connect();
    logger.info('MQTT connected');

    mqttService.subscribe('earthquake/alert');
    mqttService.subscribe('earthquake/data');
    mqttService.subscribe('earthquake/status');

    const PORT = process.env.PORT || 3000;
    server.listen(PORT, () => {
      logger.info(`Server listening on port ${PORT}`);
    });
  } catch (error) {
    logger.error('Failed to start server', error);
    process.exit(1);
  }
}

process.on('SIGINT', async () => {
  logger.info('Shutting down...');
  await mqttService.disconnect();
  await databaseService.disconnect();
  process.exit(0);
});

start();

export { app, mqttService, alertService, databaseService };
