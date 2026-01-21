import winston from 'winston';

export function createLogger(service: string): winston.Logger {
  const format = winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.printf(({ level, message, timestamp, service, ...meta }) => {
      let msg = `${timestamp} [${service}] ${level}: ${message}`;
      if (Object.keys(meta).length > 0) {
        msg += ` ${JSON.stringify(meta)}`;
      }
      return msg;
    })
  );

  return winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    defaultMeta: { service },
    format,
    transports: [
      new winston.transports.Console({
        format: winston.format.combine(
          winston.format.colorize(),
          format
        )
      }),
      new winston.transports.File({
        filename: 'logs/error.log',
        level: 'error'
      }),
      new winston.transports.File({
        filename: 'logs/combined.log'
      })
    ]
  });
}
