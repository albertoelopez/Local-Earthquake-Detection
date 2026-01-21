#include "alert_system.h"
#include "config.h"
#include <ArduinoJson.h>

LocalAlertSystem::LocalAlertSystem(int buzzerPin, int redLedPin, int yellowLedPin, int greenLedPin)
    : buzzerPin(buzzerPin),
      redLedPin(redLedPin),
      yellowLedPin(yellowLedPin),
      greenLedPin(greenLedPin),
      buzzerChannel(0) {}

void LocalAlertSystem::init() {
    pinMode(redLedPin, OUTPUT);
    pinMode(yellowLedPin, OUTPUT);
    pinMode(greenLedPin, OUTPUT);

    ledcSetup(buzzerChannel, 2000, 8);
    ledcAttachPin(buzzerPin, buzzerChannel);

    digitalWrite(greenLedPin, HIGH);
    digitalWrite(yellowLedPin, LOW);
    digitalWrite(redLedPin, LOW);
}

void LocalAlertSystem::setAlertLevel(const String& level) {
    digitalWrite(redLedPin, LOW);
    digitalWrite(yellowLedPin, LOW);
    digitalWrite(greenLedPin, LOW);

    if (level == "EXTREME" || level == "SEVERE" || level == "STRONG") {
        digitalWrite(redLedPin, HIGH);
        sirenPattern();
    } else if (level == "MODERATE") {
        digitalWrite(yellowLedPin, HIGH);
        soundAlarm(1500, 500);
    } else if (level == "LIGHT") {
        digitalWrite(yellowLedPin, HIGH);
        soundAlarm(1000, 300);
    } else {
        digitalWrite(greenLedPin, HIGH);
    }
}

void LocalAlertSystem::displayStatus(const String& status) {
    Serial.println("Status: " + status);
}

void LocalAlertSystem::soundAlarm(int frequency, int durationMs) {
    ledcWriteTone(buzzerChannel, frequency);
    delay(durationMs);
    ledcWriteTone(buzzerChannel, 0);
}

void LocalAlertSystem::sirenPattern() {
    for (int i = 0; i < 3; i++) {
        for (int freq = 800; freq <= 2000; freq += 100) {
            ledcWriteTone(buzzerChannel, freq);
            delay(30);
        }
        for (int freq = 2000; freq >= 800; freq -= 100) {
            ledcWriteTone(buzzerChannel, freq);
            delay(30);
        }
    }
    ledcWriteTone(buzzerChannel, 0);
}

void LocalAlertSystem::stopAlarm() {
    ledcWriteTone(buzzerChannel, 0);
}

MQTTAlertSystem::MQTTAlertSystem(const char* server, int port, const char* user, const char* password)
    : server(server), port(port), user(user), password(password), mqttClient(wifiClient) {}

void MQTTAlertSystem::init() {
    mqttClient.setServer(server, port);
}

bool MQTTAlertSystem::connect(const char* clientId) {
    if (mqttClient.connected()) {
        return true;
    }

    Serial.print("Connecting to MQTT...");

    bool connected;
    if (strlen(user) > 0) {
        connected = mqttClient.connect(clientId, user, password);
    } else {
        connected = mqttClient.connect(clientId);
    }

    if (connected) {
        Serial.println("connected");
        return true;
    } else {
        Serial.print("failed, rc=");
        Serial.println(mqttClient.state());
        return false;
    }
}

bool MQTTAlertSystem::isConnected() {
    return mqttClient.connected();
}

void MQTTAlertSystem::loop() {
    mqttClient.loop();
}

bool MQTTAlertSystem::publishAlert(const EarthquakeEvent& event, const String& deviceId) {
    StaticJsonDocument<512> doc;

    doc["device_id"] = deviceId;
    doc["timestamp"] = millis();
    doc["event"]["magnitude"] = event.magnitude;
    doc["event"]["pga"] = event.pga;
    doc["event"]["pgv"] = event.pgv;
    doc["event"]["cav"] = event.cav;
    doc["event"]["duration"] = event.duration;
    doc["event"]["alert_level"] = event.alertLevel;
    doc["event"]["confirmed"] = event.confirmed;
    doc["location"]["lat"] = DEVICE_LATITUDE;
    doc["location"]["lon"] = DEVICE_LONGITUDE;

    char buffer[512];
    serializeJson(doc, buffer);

    return mqttClient.publish(MQTT_TOPIC_ALERT, buffer, true);
}

bool MQTTAlertSystem::publishData(float ax, float ay, float az, const String& deviceId) {
    StaticJsonDocument<256> doc;

    doc["device_id"] = deviceId;
    doc["timestamp"] = millis();
    doc["acceleration"]["x"] = ax;
    doc["acceleration"]["y"] = ay;
    doc["acceleration"]["z"] = az;

    char buffer[256];
    serializeJson(doc, buffer);

    return mqttClient.publish(MQTT_TOPIC_DATA, buffer);
}

bool MQTTAlertSystem::publishStatus(const String& status, const String& deviceId) {
    StaticJsonDocument<128> doc;

    doc["device_id"] = deviceId;
    doc["status"] = status;
    doc["timestamp"] = millis();

    char buffer[128];
    serializeJson(doc, buffer);

    return mqttClient.publish(MQTT_TOPIC_STATUS, buffer, true);
}

void MQTTAlertSystem::setCallback(MQTT_CALLBACK_SIGNATURE) {
    mqttClient.setCallback(callback);
}

WebhookAlertSystem::WebhookAlertSystem() {}

void WebhookAlertSystem::setPushoverCredentials(const String& token, const String& user) {
    pushoverToken = token;
    pushoverUser = user;
}

void WebhookAlertSystem::setTelegramCredentials(const String& botToken, const String& chatId) {
    telegramBotToken = botToken;
    telegramChatId = chatId;
}

void WebhookAlertSystem::setDiscordWebhook(const String& webhookUrl) {
    discordWebhookUrl = webhookUrl;
}

String WebhookAlertSystem::urlEncode(const String& str) {
    String encoded = "";
    char c;
    char code0;
    char code1;

    for (int i = 0; i < str.length(); i++) {
        c = str.charAt(i);
        if (c == ' ') {
            encoded += '+';
        } else if (isalnum(c)) {
            encoded += c;
        } else {
            code1 = (c & 0xf) + '0';
            if ((c & 0xf) > 9) {
                code1 = (c & 0xf) - 10 + 'A';
            }
            c = (c >> 4) & 0xf;
            code0 = c + '0';
            if (c > 9) {
                code0 = c - 10 + 'A';
            }
            encoded += '%';
            encoded += code0;
            encoded += code1;
        }
    }

    return encoded;
}

bool WebhookAlertSystem::sendPushover(const String& title, const String& message, int priority) {
    if (pushoverToken.length() == 0 || pushoverUser.length() == 0) {
        return false;
    }

    HTTPClient http;
    http.begin("https://api.pushover.net/1/messages.json");
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String payload = "token=" + pushoverToken +
                     "&user=" + pushoverUser +
                     "&title=" + urlEncode(title) +
                     "&message=" + urlEncode(message) +
                     "&priority=" + String(priority) +
                     "&sound=siren";

    int httpCode = http.POST(payload);
    http.end();

    return httpCode == 200;
}

bool WebhookAlertSystem::sendTelegram(const String& message) {
    if (telegramBotToken.length() == 0 || telegramChatId.length() == 0) {
        return false;
    }

    HTTPClient http;
    String url = "https://api.telegram.org/bot" + telegramBotToken + "/sendMessage";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<512> doc;
    doc["chat_id"] = telegramChatId;
    doc["text"] = message;
    doc["parse_mode"] = "Markdown";

    String payload;
    serializeJson(doc, payload);

    int httpCode = http.POST(payload);
    http.end();

    return httpCode == 200;
}

bool WebhookAlertSystem::sendDiscord(const String& message) {
    if (discordWebhookUrl.length() == 0) {
        return false;
    }

    HTTPClient http;
    http.begin(discordWebhookUrl);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<512> doc;
    doc["content"] = message;
    doc["username"] = "Earthquake Alert Bot";

    JsonArray embeds = doc.createNestedArray("embeds");
    JsonObject embed = embeds.createNestedObject();
    embed["title"] = "Earthquake Detected!";
    embed["description"] = message;
    embed["color"] = 16711680;

    String payload;
    serializeJson(doc, payload);

    int httpCode = http.POST(payload);
    http.end();

    return httpCode == 204 || httpCode == 200;
}

void WebhookAlertSystem::broadcastAlert(const EarthquakeEvent& event) {
    String message = "EARTHQUAKE DETECTED!\n";
    message += "Magnitude: " + String(event.magnitude, 2) + "\n";
    message += "PGA: " + String(event.pga, 3) + " g\n";
    message += "CAV: " + String(event.cav, 3) + " g*s\n";
    message += "Alert Level: " + event.alertLevel + "\n";
    message += "Duration: " + String(event.duration / 1000.0, 1) + " seconds";

    int priority = (event.alertLevel == "EXTREME" || event.alertLevel == "SEVERE") ? 2 : 1;

    sendPushover("Earthquake Alert", message, priority);
    sendTelegram(message);
    sendDiscord(message);
}

AlertManager::AlertManager() : localAlert(nullptr), mqttAlert(nullptr), webhookAlert(nullptr) {}

void AlertManager::init(LocalAlertSystem* local, MQTTAlertSystem* mqtt, WebhookAlertSystem* webhook) {
    localAlert = local;
    mqttAlert = mqtt;
    webhookAlert = webhook;
}

void AlertManager::setDeviceId(const String& id) {
    deviceId = id;
}

void AlertManager::sendAlert(const EarthquakeEvent& event, AlertChannel channel) {
    if (channel == ALERT_ALL || channel == ALERT_LOCAL) {
        if (localAlert) {
            localAlert->setAlertLevel(event.alertLevel);
        }
    }

    if (channel == ALERT_ALL || channel == ALERT_MQTT) {
        if (mqttAlert && mqttAlert->isConnected()) {
            mqttAlert->publishAlert(event, deviceId);
        }
    }

    if (channel == ALERT_ALL) {
        if (webhookAlert) {
            webhookAlert->broadcastAlert(event);
        }
    }
}

void AlertManager::sendStatus(const String& status) {
    if (localAlert) {
        localAlert->displayStatus(status);
    }

    if (mqttAlert && mqttAlert->isConnected()) {
        mqttAlert->publishStatus(status, deviceId);
    }
}
