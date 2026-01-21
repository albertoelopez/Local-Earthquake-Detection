# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

### ESP32 Firmware (PlatformIO)
```bash
cd firmware
pio run                    # Build
pio run -t upload          # Build and upload to ESP32
pio device monitor         # Serial monitor
```

### Node.js Server
```bash
cd server
npm install                # Install dependencies
npm run dev                # Development server
npm test                   # Run Jest tests
npm test -- --coverage     # Coverage report
npm test -- -t "test name" # Run single test
```

### React Dashboard
```bash
cd dashboard
npm install                # Install dependencies
npm run dev                # Development server (Vite)
npm run test:e2e           # Playwright E2E tests
npm run test:e2e:ui        # E2E tests with UI
npx playwright test --project=chromium  # Single browser
```

### Python ML Pipeline
```bash
cd data-processing
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest scripts/test_feature_extraction.py     # Run tests
pytest scripts/test_feature_extraction.py -k "test_name"  # Single test
```

### Edge Impulse MCP Server
```bash
cd mcp-edge-impulse
pip install -r requirements.txt
export EDGE_IMPULSE_API_KEY=your_key
python server.py
```

## Architecture Overview

This is a multi-component earthquake detection system:

**ESP32 Firmware** (`firmware/`) → Reads MPU6050 accelerometer, runs STA/LTA detection algorithm, publishes alerts via MQTT

**Node.js Server** (`server/`) → Subscribes to MQTT topics, stores alerts, exposes REST API and WebSocket for real-time updates, triggers notification services (Pushover/Telegram/Discord)

**React Dashboard** (`dashboard/`) → Connects via WebSocket for real-time alert display, uses Vite for bundling

**Python ML Pipeline** (`data-processing/`) → Feature extraction from seismic data, model training for threshold calibration

**MCP Servers** (`mcp-edge-impulse/`, `kaggle-mcp/`) → Claude Code integrations for Edge Impulse ML training and Kaggle dataset downloads

## Key Detection Parameters

- **STA/LTA Algorithm**: Short-Term Average (1s) / Long-Term Average (30s) ratio triggers at 5.0
- **Alert Levels**: green (<0.03g), yellow (0.03g), orange (0.08g), red (0.15g+) based on PGA
- **Seismic Features**: magnitude, depth, cdi, mmi, sig (for ML classification)

## MQTT Topics

- `earthquake/alert` - Alert events from ESP32
- `earthquake/data` - Raw sensor data
- `earthquake/status` - Device heartbeat
- `earthquake/command/{id}` - Commands to devices

## Code Style

- No single-line (`//`) or multi-line (`/* */`) comments in production code
- Code should be self-documenting through clear naming
- Follow TDD: write tests before implementation
