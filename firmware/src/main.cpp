#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <WiFi.h>

#include "config.h"
#include "earthquake_detector.h"
#include "alert_system.h"
#include "event_queue.h"

Adafruit_MPU6050 mpu;

EarthquakeDetector detector(SAMPLE_RATE_HZ, STA_WINDOW_SEC, LTA_WINDOW_SEC,
                             STA_LTA_TRIGGER_THRESHOLD, STA_LTA_DETRIGGER_THRESHOLD);

LocalAlertSystem localAlert(BUZZER_PIN, RED_LED_PIN, YELLOW_LED_PIN, GREEN_LED_PIN);
MQTTAlertSystem mqttAlert(MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
WebhookAlertSystem webhookAlert;
AlertManager alertManager;
EventQueue eventQueue;

ButterworthFilter filterX(SAMPLE_RATE_HZ, FILTER_LOW_CUTOFF_HZ, FILTER_HIGH_CUTOFF_HZ, FILTER_ORDER);
ButterworthFilter filterY(SAMPLE_RATE_HZ, FILTER_LOW_CUTOFF_HZ, FILTER_HIGH_CUTOFF_HZ, FILTER_ORDER);
ButterworthFilter filterZ(SAMPLE_RATE_HZ, FILTER_LOW_CUTOFF_HZ, FILTER_HIGH_CUTOFF_HZ, FILTER_ORDER);

KalmanFilter kalmanX(0.01, 0.1);
KalmanFilter kalmanY(0.01, 0.1);
KalmanFilter kalmanZ(0.01, 0.1);

String deviceId;
unsigned long lastSampleTime = 0;
unsigned long sampleInterval = 1000 / SAMPLE_RATE_HZ;
bool wifiConnected = false;
bool mqttConnected = false;

volatile bool dataReady = false;

void IRAM_ATTR onMPUInterrupt() {
    dataReady = true;
}

void connectWiFi() {
    Serial.print("Connecting to WiFi");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 40) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
        wifiConnected = true;
    } else {
        Serial.println("\nWiFi connection failed");
        wifiConnected = false;
    }
}

void connectMQTT() {
    if (!wifiConnected) return;

    if (mqttAlert.connect(deviceId.c_str())) {
        mqttConnected = true;
        alertManager.sendStatus("online");
    } else {
        mqttConnected = false;
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String message = "";
    for (unsigned int i = 0; i < length; i++) {
        message += (char)payload[i];
    }

    Serial.println("MQTT message received: " + String(topic) + " -> " + message);

    if (message == "reset") {
        detector.reset();
        Serial.println("Detector reset");
    } else if (message == "status") {
        alertManager.sendStatus("alive");
    }
}

void setup() {
    Serial.begin(115200);
    while (!Serial) {
        delay(10);
    }

    Serial.println("Earthquake Alert System Starting...");

    deviceId = "ESP32_" + WiFi.macAddress();
    deviceId.replace(":", "");
    Serial.println("Device ID: " + deviceId);

    localAlert.init();
    Serial.println("Local alert system initialized");

    if (!eventQueue.init()) {
        Serial.println("Event queue initialization failed");
    }

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

    if (!mpu.begin(MPU6050_I2C_ADDRESS)) {
        Serial.println("Failed to find MPU6050 chip");
        while (1) {
            localAlert.soundAlarm(500, 200);
            delay(500);
        }
    }

    Serial.println("MPU6050 Found!");

    mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
    mpu.setGyroRange(MPU6050_RANGE_250_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

    detector.init();
    Serial.println("Earthquake detector initialized");

    connectWiFi();

    if (wifiConnected) {
        mqttAlert.init();
        mqttAlert.setCallback(mqttCallback);
        connectMQTT();

        webhookAlert.setPushoverCredentials(PUSHOVER_TOKEN, PUSHOVER_USER);
        webhookAlert.setTelegramCredentials(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID);
        webhookAlert.setDiscordWebhook(DISCORD_WEBHOOK_URL);
    }

    alertManager.init(&localAlert, &mqttAlert, &webhookAlert);
    alertManager.setDeviceId(deviceId);

    localAlert.setAlertLevel("NEGLIGIBLE");
    Serial.println("System ready - monitoring for earthquakes");
}

void loop() {
    unsigned long currentTime = millis();

    if (wifiConnected) {
        if (!mqttAlert.isConnected()) {
            connectMQTT();
        }
        mqttAlert.loop();
    }

    if (currentTime - lastSampleTime >= sampleInterval) {
        lastSampleTime = currentTime;

        sensors_event_t a, g, temp;
        mpu.getEvent(&a, &g, &temp);

        float ax = filterX.process(a.acceleration.x);
        float ay = filterY.process(a.acceleration.y);
        float az = filterZ.process(a.acceleration.z);

        ax = kalmanX.update(ax);
        ay = kalmanY.update(ay);
        az = kalmanZ.update(az);

        detector.addSample(ax, ay, az);

        bool wasTriggered = detector.isTriggered();

        if (wasTriggered) {
            EarthquakeEvent event = detector.getCurrentEvent();

            static String lastAlertLevel = "";
            if (event.alertLevel != lastAlertLevel) {
                lastAlertLevel = event.alertLevel;
                localAlert.setAlertLevel(event.alertLevel);

                Serial.printf("Alert Level: %s, PGA: %.4f g, STA/LTA: %.2f\n",
                              event.alertLevel.c_str(), event.pga, detector.getStaLtaRatio());
            }

            if (event.confirmed && event.duration > 0) {
                Serial.println("CONFIRMED EARTHQUAKE EVENT!");
                Serial.printf("Magnitude: %.2f, PGA: %.4f g, CAV: %.4f g*s, Duration: %lu ms\n",
                              event.magnitude, event.pga, event.cav, event.duration);

                if (wifiConnected && mqttConnected) {
                    alertManager.sendAlert(event, ALERT_ALL);
                } else {
                    eventQueue.addEvent(event, deviceId);
                    alertManager.sendAlert(event, ALERT_LOCAL);
                }

                detector.reset();
            }
        }
    }

    if (wifiConnected && mqttConnected && eventQueue.getUnsentCount() > 0) {
        eventQueue.processQueue([](const QueuedEvent& queuedEvent) {
            return mqttAlert.publishAlert(queuedEvent.event, queuedEvent.deviceId);
        });
        eventQueue.clearSentEvents();
    }

    static unsigned long lastStatusTime = 0;
    if (currentTime - lastStatusTime >= 60000) {
        lastStatusTime = currentTime;

        Serial.printf("Status - STA/LTA: %.2f, PGA: %.6f g, Queue: %d unsent\n",
                      detector.getStaLtaRatio(), detector.getCurrentPGA(), eventQueue.getUnsentCount());

        if (mqttConnected) {
            alertManager.sendStatus("monitoring");
        }
    }
}
