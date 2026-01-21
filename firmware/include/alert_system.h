#ifndef ALERT_SYSTEM_H
#define ALERT_SYSTEM_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <HTTPClient.h>
#include "earthquake_detector.h"

enum AlertChannel {
    ALERT_LOCAL,
    ALERT_MQTT,
    ALERT_PUSHOVER,
    ALERT_TELEGRAM,
    ALERT_DISCORD,
    ALERT_ALL
};

class LocalAlertSystem {
public:
    LocalAlertSystem(int buzzerPin, int redLedPin, int yellowLedPin, int greenLedPin);
    void init();
    void setAlertLevel(const String& level);
    void displayStatus(const String& status);
    void soundAlarm(int frequency, int durationMs);
    void sirenPattern();
    void stopAlarm();

private:
    int buzzerPin;
    int redLedPin;
    int yellowLedPin;
    int greenLedPin;
    int buzzerChannel;
};

class MQTTAlertSystem {
public:
    MQTTAlertSystem(const char* server, int port, const char* user, const char* password);
    void init();
    bool connect(const char* clientId);
    bool isConnected();
    void loop();
    bool publishAlert(const EarthquakeEvent& event, const String& deviceId);
    bool publishData(float ax, float ay, float az, const String& deviceId);
    bool publishStatus(const String& status, const String& deviceId);
    void setCallback(MQTT_CALLBACK_SIGNATURE);

private:
    WiFiClient wifiClient;
    PubSubClient mqttClient;
    const char* server;
    int port;
    const char* user;
    const char* password;
};

class WebhookAlertSystem {
public:
    WebhookAlertSystem();
    void setPushoverCredentials(const String& token, const String& user);
    void setTelegramCredentials(const String& botToken, const String& chatId);
    void setDiscordWebhook(const String& webhookUrl);

    bool sendPushover(const String& title, const String& message, int priority);
    bool sendTelegram(const String& message);
    bool sendDiscord(const String& message);
    void broadcastAlert(const EarthquakeEvent& event);

private:
    String pushoverToken;
    String pushoverUser;
    String telegramBotToken;
    String telegramChatId;
    String discordWebhookUrl;

    String urlEncode(const String& str);
};

class AlertManager {
public:
    AlertManager();
    void init(LocalAlertSystem* local, MQTTAlertSystem* mqtt, WebhookAlertSystem* webhook);
    void sendAlert(const EarthquakeEvent& event, AlertChannel channel = ALERT_ALL);
    void sendStatus(const String& status);
    void setDeviceId(const String& id);

private:
    LocalAlertSystem* localAlert;
    MQTTAlertSystem* mqttAlert;
    WebhookAlertSystem* webhookAlert;
    String deviceId;
};

#endif
