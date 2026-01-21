import mqtt, { MqttClient, IClientOptions } from 'mqtt';
import { EventEmitter } from 'events';
import { Logger } from 'winston';

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

export interface SensorData {
  device_id: string;
  timestamp: number;
  acceleration: {
    x: number;
    y: number;
    z: number;
  };
}

export interface DeviceStatus {
  device_id: string;
  status: string;
  timestamp: number;
}

export class MQTTService extends EventEmitter {
  private client: MqttClient | null = null;
  private brokerUrl: string;
  private logger: Logger;
  private connected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 10;

  constructor(brokerUrl: string, logger: Logger) {
    super();
    this.brokerUrl = brokerUrl;
    this.logger = logger;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const options: IClientOptions = {
        clientId: `earthquake-server-${Date.now()}`,
        clean: true,
        connectTimeout: 10000,
        reconnectPeriod: 5000,
      };

      this.client = mqtt.connect(this.brokerUrl, options);

      this.client.on('connect', () => {
        this.connected = true;
        this.reconnectAttempts = 0;
        this.logger.info('Connected to MQTT broker');
        resolve();
      });

      this.client.on('error', (error) => {
        this.logger.error('MQTT error', error);
        if (!this.connected) {
          reject(error);
        }
      });

      this.client.on('close', () => {
        this.connected = false;
        this.logger.warn('MQTT connection closed');
      });

      this.client.on('reconnect', () => {
        this.reconnectAttempts++;
        this.logger.info(`MQTT reconnecting (attempt ${this.reconnectAttempts})`);

        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.logger.error('Max reconnection attempts reached');
          this.client?.end();
        }
      });

      this.client.on('message', (topic: string, payload: Buffer) => {
        this.handleMessage(topic, payload);
      });
    });
  }

  private handleMessage(topic: string, payload: Buffer): void {
    try {
      const data = JSON.parse(payload.toString());

      if (topic.includes('/alert')) {
        this.emit('alert', data as EarthquakeAlert);
      } else if (topic.includes('/data')) {
        this.emit('data', data as SensorData);
      } else if (topic.includes('/status')) {
        this.emit('status', data as DeviceStatus);
      }
    } catch (error) {
      this.logger.error('Failed to parse MQTT message', { topic, error });
    }
  }

  subscribe(topic: string): void {
    if (this.client && this.connected) {
      this.client.subscribe(topic, { qos: 1 }, (error) => {
        if (error) {
          this.logger.error(`Failed to subscribe to ${topic}`, error);
        } else {
          this.logger.info(`Subscribed to ${topic}`);
        }
      });
    }
  }

  publish(topic: string, message: object, qos: 0 | 1 | 2 = 1): void {
    if (this.client && this.connected) {
      this.client.publish(topic, JSON.stringify(message), { qos }, (error) => {
        if (error) {
          this.logger.error(`Failed to publish to ${topic}`, error);
        }
      });
    }
  }

  async disconnect(): Promise<void> {
    return new Promise((resolve) => {
      if (this.client) {
        this.client.end(false, {}, () => {
          this.connected = false;
          this.logger.info('MQTT disconnected');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }

  isConnected(): boolean {
    return this.connected;
  }
}
