# Earthquake Alert System

A comprehensive earthquake detection and alert system using ESP32 microcontroller with MPU6050 accelerometer, powered by real-time signal processing algorithms and multi-channel notifications.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ESP32 SENSOR NETWORK                        │
│                                                                 │
│  [ESP32 + MPU6050] ──────────────────────────────────────────  │
│         │                                                       │
│    ┌────┴────┐                                                 │
│    │ STA/LTA │  ← Earthquake Detection Algorithm               │
│    │   PGA   │  ← Peak Ground Acceleration                     │
│    │   CAV   │  ← Cumulative Absolute Velocity                 │
│    └────┬────┘                                                 │
│         │                                                       │
└─────────┼───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    COMMUNICATION LAYER                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ MQTT Broker  │  │  WebSocket   │  │  REST API    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   NOTIFICATION SERVICES                         │
│                                                                 │
│  • Pushover    • Telegram    • Discord    • Local Buzzer/LED   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Real-time Earthquake Detection**: STA/LTA algorithm with configurable thresholds
- **Multi-axis Accelerometer Support**: 3-axis acceleration monitoring with MPU6050
- **Signal Processing**: Butterworth bandpass filter (0.1-25Hz) and Kalman filtering
- **Seismic Parameters**: PGA, PGV, CAV, Arias Intensity calculations
- **Multi-channel Alerts**: MQTT, Pushover, Telegram, Discord, local buzzer/LED
- **Offline Operation**: Event queuing with SPIFFS storage
- **Web Dashboard**: Real-time monitoring with React + WebSocket
- **ML Calibration**: Kaggle dataset integration for threshold optimization

## Hardware Requirements

### Components
- ESP32 DevKit V1 (or compatible)
- MPU6050 Accelerometer (GY-521 module)
- Active Buzzer (optional)
- LEDs (Red, Yellow, Green) (optional)
- 16x2 LCD with I2C adapter (optional)

### Wiring Diagram

```
MPU6050          ESP32
────────         ─────
VCC      ───►    3.3V
GND      ───►    GND
SDA      ───►    GPIO 21
SCL      ───►    GPIO 22
INT      ───►    GPIO 32 (optional)

Buzzer   ───►    GPIO 25
Red LED  ───►    GPIO 26
Yellow   ───►    GPIO 27
Green    ───►    GPIO 14
```

## Project Structure

```
earthquake_alert/
├── firmware/               # ESP32 Arduino/PlatformIO code
│   ├── src/
│   │   ├── main.cpp
│   │   ├── earthquake_detector.cpp
│   │   ├── alert_system.cpp
│   │   └── event_queue.cpp
│   ├── include/
│   │   ├── config.h
│   │   ├── earthquake_detector.h
│   │   ├── alert_system.h
│   │   └── event_queue.h
│   └── platformio.ini
├── server/                 # Node.js backend
│   ├── src/
│   │   ├── index.ts
│   │   ├── services/
│   │   │   ├── mqtt.service.ts
│   │   │   ├── alert.service.ts
│   │   │   └── database.service.ts
│   │   └── routes/
│   └── tests/
├── dashboard/              # React web dashboard
│   ├── src/components/
│   └── tests/e2e/
├── data-processing/        # Python ML pipeline
│   ├── scripts/
│   │   ├── feature_extraction.py
│   │   ├── data_loader.py
│   │   └── model_training.py
│   └── requirements.txt
└── docs/
```

## Installation

### 1. ESP32 Firmware

```bash
cd firmware

# Install PlatformIO CLI (if not installed)
pip install platformio

# Build and upload
pio run -t upload

# Monitor serial output
pio device monitor
```

### 2. Server Backend

```bash
cd server

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run development server
npm run dev

# Run tests
npm test
```

### 3. Web Dashboard

```bash
cd dashboard

# Install dependencies
npm install

# Run development server
npm run dev

# Run E2E tests
npm run test:e2e
```

### 4. Data Processing Pipeline

```bash
cd data-processing

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run feature extraction tests
pytest scripts/test_feature_extraction.py

# Train model (optional)
python scripts/model_training.py
```

## Configuration

### ESP32 Configuration (firmware/include/config.h)

```cpp
// WiFi
#define WIFI_SSID "your_ssid"
#define WIFI_PASSWORD "your_password"

// MQTT
#define MQTT_SERVER "broker.hivemq.com"
#define MQTT_PORT 1883

// Detection Parameters
#define SAMPLE_RATE_HZ 100
#define STA_WINDOW_SEC 1.0f
#define LTA_WINDOW_SEC 30.0f
#define STA_LTA_TRIGGER_THRESHOLD 5.0f

// Alert Thresholds (PGA in g)
#define PGA_THRESHOLD_LIGHT 0.03f
#define PGA_THRESHOLD_MODERATE 0.08f
#define PGA_THRESHOLD_STRONG 0.15f
```

### Server Environment (.env)

```bash
PORT=3000
MQTT_BROKER=mqtt://broker.hivemq.com

# Notification Services (optional)
PUSHOVER_TOKEN=your_token
PUSHOVER_USER=your_user
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_webhook_url
```

## Detection Algorithm

### STA/LTA (Short-Term Average / Long-Term Average)

The primary detection algorithm compares short-term signal amplitude to long-term background:

```
STA(t) = (1/N_sta) × Σ|a(t-i)|²  for i=0 to N_sta
LTA(t) = (1/N_lta) × Σ|a(t-i)|²  for i=0 to N_lta

Ratio(t) = STA(t) / LTA(t)

Trigger when: Ratio(t) > threshold_trigger (default: 5.0)
Detrigger when: Ratio(t) < threshold_detrigger (default: 2.0)
```

### Alert Level Thresholds

| Alert Level | PGA (g) | Modified Mercalli Intensity |
|-------------|---------|------------------------------|
| NEGLIGIBLE  | < 0.03  | I-IV                        |
| LIGHT       | 0.03    | V                           |
| MODERATE    | 0.08    | VI                          |
| STRONG      | 0.15    | VII                         |
| SEVERE      | 0.25    | VIII                        |
| EXTREME     | 0.45+   | IX+                         |

## API Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts` | GET | Get recent alerts |
| `/api/alerts/device/:id` | GET | Get alerts by device |
| `/api/alerts/stats` | GET | Get statistics |
| `/api/status` | GET | Get system status |
| `/api/status/devices` | GET | Get all devices |
| `/health` | GET | Health check |

### MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `earthquake/alert` | ESP32 → Server | Earthquake alert events |
| `earthquake/data` | ESP32 → Server | Raw sensor data |
| `earthquake/status` | ESP32 → Server | Device status updates |
| `earthquake/command/{id}` | Server → ESP32 | Device commands |

## Kaggle Dataset Integration

### Supported Datasets

1. **LANL Earthquake Prediction**
   - Lab acoustic signals with time-to-failure labels
   - URL: https://www.kaggle.com/c/LANL-Earthquake-Prediction

2. **Stanford STEAD**
   - Global seismic waveforms
   - URL: https://www.kaggle.com/datasets/isevilla/stanford-earthquake-dataset-stead

### Downloading Data

```python
from data_loader import download_kaggle_dataset

# Configure Kaggle API credentials first
# ~/.kaggle/kaggle.json

download_kaggle_dataset(
    'LANL-Earthquake-Prediction',
    'data/lanl'
)
```

### Feature Extraction

```python
from feature_extraction import FeatureExtractor

extractor = FeatureExtractor(sampling_rate=100)
features = extractor.fit_transform(X_train)

# Features include:
# - Statistical: mean, std, skewness, kurtosis, percentiles
# - Frequency: FFT coefficients, spectral centroid, rolloff
# - Seismic: PGA, PGV, CAV, Arias intensity
# - STA/LTA: max ratio, trigger count
```

## Edge Impulse ML Integration

This project integrates with Edge Impulse for embedded ML model training and deployment on ESP32.

### MCP Server Setup

The `mcp-edge-impulse/` directory contains a custom MCP (Model Context Protocol) server for Edge Impulse integration:

```bash
cd mcp-edge-impulse

# Install dependencies
pip install -r requirements.txt

# Set API key
export EDGE_IMPULSE_API_KEY=your_api_key
```

### Training Pipeline

1. **Data Upload**: Kaggle earthquake data is uploaded to Edge Impulse with proper train/test split (80%/20%)
2. **Impulse Design**: Configure input features (magnitude, depth, cdi, mmi, sig)
3. **Feature Generation**: Process raw data through DSP blocks
4. **Model Training**: 4-class neural network classifier for alert levels

### Alert Classification

| Class | Alert Level | Description |
|-------|-------------|-------------|
| green | Low | Minor earthquake, no damage expected |
| yellow | Moderate | Light shaking, minimal damage |
| orange | Significant | Moderate shaking, possible damage |
| red | Severe | Strong shaking, significant damage likely |

### Seismic Features

- **magnitude**: Earthquake magnitude (Mw scale)
- **depth**: Hypocenter depth in km
- **cdi**: Community Decimal Intensity (felt reports)
- **mmi**: Modified Mercalli Intensity
- **sig**: Significance score (0-1000)

### Model Deployment

Export trained model as C++ library for ESP32:

```bash
# From Edge Impulse Studio
# Deployment > Arduino library > Build
```

## Testing

### Unit Tests

```bash
# Server tests (Jest)
cd server && npm test

# Python tests (pytest)
cd data-processing && pytest

# Coverage report
npm test -- --coverage
```

### E2E Tests (Playwright)

```bash
cd dashboard

# Run all E2E tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui

# Run specific browser
npx playwright test --project=chromium
```

## Troubleshooting

### Common Issues

1. **MPU6050 not detected**
   - Check I2C wiring (SDA→21, SCL→22)
   - Verify I2C address (0x68 or 0x69)
   - Add pull-up resistors if needed

2. **WiFi connection fails**
   - Verify credentials in config.h
   - Check WiFi signal strength
   - ESP32 supports 2.4GHz only

3. **MQTT connection drops**
   - Implement reconnection logic (included)
   - Check firewall settings
   - Use QoS 1 for reliability

4. **False positives**
   - Increase STA/LTA threshold
   - Add minimum duration filter
   - Enable multi-axis correlation check

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`npm test`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Research based on industry-standard seismic detection algorithms
- USGS earthquake data and documentation
- Stanford STEAD dataset team
- LANL Earthquake Prediction competition

## References

1. Allen, R. (1978). Automatic earthquake recognition and timing from single traces.
2. USGS Earthquake Hazards Program: https://earthquake.usgs.gov
3. ESP32 Technical Reference Manual
4. MPU6050 Datasheet - InvenSense
