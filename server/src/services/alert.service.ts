import { Logger } from 'winston';
import { DatabaseService } from './database.service';
import { EarthquakeAlert } from './mqtt.service';
import https from 'https';

interface NotificationConfig {
  pushover?: {
    token: string;
    user: string;
  };
  telegram?: {
    botToken: string;
    chatId: string;
  };
  discord?: {
    webhookUrl: string;
  };
  email?: {
    smtpHost: string;
    smtpPort: number;
    user: string;
    password: string;
    recipients: string[];
  };
}

export class AlertService {
  private database: DatabaseService;
  private logger: Logger;
  private config: NotificationConfig;

  constructor(database: DatabaseService, logger: Logger) {
    this.database = database;
    this.logger = logger;
    this.config = this.loadConfig();
  }

  private loadConfig(): NotificationConfig {
    return {
      pushover: process.env.PUSHOVER_TOKEN ? {
        token: process.env.PUSHOVER_TOKEN,
        user: process.env.PUSHOVER_USER || ''
      } : undefined,
      telegram: process.env.TELEGRAM_BOT_TOKEN ? {
        botToken: process.env.TELEGRAM_BOT_TOKEN,
        chatId: process.env.TELEGRAM_CHAT_ID || ''
      } : undefined,
      discord: process.env.DISCORD_WEBHOOK_URL ? {
        webhookUrl: process.env.DISCORD_WEBHOOK_URL
      } : undefined
    };
  }

  async processAlert(alert: EarthquakeAlert): Promise<void> {
    this.logger.info('Processing earthquake alert', {
      device: alert.device_id,
      magnitude: alert.event.magnitude,
      alertLevel: alert.event.alert_level
    });

    const shouldNotify = this.shouldSendNotification(alert);

    if (shouldNotify) {
      await this.sendNotifications(alert);
    }

    await this.database.saveAlert(alert);
  }

  private shouldSendNotification(alert: EarthquakeAlert): boolean {
    const highAlertLevels = ['STRONG', 'SEVERE', 'EXTREME'];
    return alert.event.confirmed && highAlertLevels.includes(alert.event.alert_level);
  }

  private async sendNotifications(alert: EarthquakeAlert): Promise<void> {
    const message = this.formatAlertMessage(alert);

    const promises: Promise<void>[] = [];

    if (this.config.pushover) {
      promises.push(this.sendPushover(alert, message));
    }

    if (this.config.telegram) {
      promises.push(this.sendTelegram(message));
    }

    if (this.config.discord) {
      promises.push(this.sendDiscord(alert, message));
    }

    await Promise.allSettled(promises);
  }

  private formatAlertMessage(alert: EarthquakeAlert): string {
    return `🚨 EARTHQUAKE ALERT!

📍 Location: ${alert.location.lat.toFixed(4)}, ${alert.location.lon.toFixed(4)}
📊 Magnitude: ${alert.event.magnitude.toFixed(2)}
⚡ PGA: ${alert.event.pga.toFixed(4)} g
📈 CAV: ${alert.event.cav.toFixed(4)} g·s
⏱️ Duration: ${(alert.event.duration / 1000).toFixed(1)} seconds
🎚️ Alert Level: ${alert.event.alert_level}
🔧 Device: ${alert.device_id}
🕐 Time: ${new Date(alert.timestamp).toISOString()}`;
  }

  private async sendPushover(alert: EarthquakeAlert, message: string): Promise<void> {
    if (!this.config.pushover) return;

    const priority = alert.event.alert_level === 'EXTREME' ? 2 : 1;

    const payload = new URLSearchParams({
      token: this.config.pushover.token,
      user: this.config.pushover.user,
      title: `Earthquake Alert - ${alert.event.alert_level}`,
      message: message,
      priority: priority.toString(),
      sound: 'siren'
    });

    return new Promise((resolve, reject) => {
      const req = https.request({
        hostname: 'api.pushover.net',
        port: 443,
        path: '/1/messages.json',
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Content-Length': payload.toString().length
        }
      }, (res) => {
        if (res.statusCode === 200) {
          this.logger.info('Pushover notification sent');
          resolve();
        } else {
          this.logger.error('Pushover notification failed', { statusCode: res.statusCode });
          reject(new Error(`Pushover failed: ${res.statusCode}`));
        }
      });

      req.on('error', (error) => {
        this.logger.error('Pushover request error', error);
        reject(error);
      });

      req.write(payload.toString());
      req.end();
    });
  }

  private async sendTelegram(message: string): Promise<void> {
    if (!this.config.telegram) return;

    const payload = JSON.stringify({
      chat_id: this.config.telegram.chatId,
      text: message,
      parse_mode: 'HTML'
    });

    return new Promise((resolve, reject) => {
      const req = https.request({
        hostname: 'api.telegram.org',
        port: 443,
        path: `/bot${this.config.telegram!.botToken}/sendMessage`,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload)
        }
      }, (res) => {
        if (res.statusCode === 200) {
          this.logger.info('Telegram notification sent');
          resolve();
        } else {
          this.logger.error('Telegram notification failed', { statusCode: res.statusCode });
          reject(new Error(`Telegram failed: ${res.statusCode}`));
        }
      });

      req.on('error', (error) => {
        this.logger.error('Telegram request error', error);
        reject(error);
      });

      req.write(payload);
      req.end();
    });
  }

  private async sendDiscord(alert: EarthquakeAlert, message: string): Promise<void> {
    if (!this.config.discord) return;

    const webhookUrl = new URL(this.config.discord.webhookUrl);

    const color = alert.event.alert_level === 'EXTREME' ? 0xFF0000 :
                  alert.event.alert_level === 'SEVERE' ? 0xFF4500 : 0xFFA500;

    const payload = JSON.stringify({
      username: 'Earthquake Alert Bot',
      embeds: [{
        title: `🚨 Earthquake Alert - ${alert.event.alert_level}`,
        description: message,
        color: color,
        fields: [
          { name: 'Magnitude', value: alert.event.magnitude.toFixed(2), inline: true },
          { name: 'PGA', value: `${alert.event.pga.toFixed(4)} g`, inline: true },
          { name: 'Duration', value: `${(alert.event.duration / 1000).toFixed(1)}s`, inline: true }
        ],
        timestamp: new Date(alert.timestamp).toISOString()
      }]
    });

    return new Promise((resolve, reject) => {
      const req = https.request({
        hostname: webhookUrl.hostname,
        port: 443,
        path: webhookUrl.pathname,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload)
        }
      }, (res) => {
        if (res.statusCode === 204 || res.statusCode === 200) {
          this.logger.info('Discord notification sent');
          resolve();
        } else {
          this.logger.error('Discord notification failed', { statusCode: res.statusCode });
          reject(new Error(`Discord failed: ${res.statusCode}`));
        }
      });

      req.on('error', (error) => {
        this.logger.error('Discord request error', error);
        reject(error);
      });

      req.write(payload);
      req.end();
    });
  }

  async getRecentAlerts(limit: number = 50): Promise<EarthquakeAlert[]> {
    return this.database.getRecentAlerts(limit);
  }

  async getAlertsByDevice(deviceId: string, limit: number = 20): Promise<EarthquakeAlert[]> {
    return this.database.getAlertsByDevice(deviceId, limit);
  }

  async getAlertStats(): Promise<object> {
    return this.database.getAlertStats();
  }
}
