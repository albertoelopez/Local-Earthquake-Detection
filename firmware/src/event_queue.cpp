#include "event_queue.h"
#include <ArduinoJson.h>

EventQueue::EventQueue() {}

bool EventQueue::init() {
    if (!SPIFFS.begin(true)) {
        Serial.println("SPIFFS Mount Failed");
        return false;
    }

    return loadFromDisk();
}

bool EventQueue::addEvent(const EarthquakeEvent& event, const String& deviceId) {
    QueuedEvent queuedEvent;
    queuedEvent.event = event;
    queuedEvent.deviceId = deviceId;
    queuedEvent.sent = false;

    queue.push_back(queuedEvent);

    if (queue.size() > MAX_QUEUE_SIZE) {
        queue.erase(queue.begin());
    }

    return saveToDisk();
}

bool EventQueue::processQueue(std::function<bool(const QueuedEvent&)> sendFunction) {
    bool anyProcessed = false;

    for (auto& queuedEvent : queue) {
        if (!queuedEvent.sent) {
            if (sendFunction(queuedEvent)) {
                queuedEvent.sent = true;
                anyProcessed = true;
            } else {
                break;
            }
        }
    }

    if (anyProcessed) {
        saveToDisk();
    }

    return anyProcessed;
}

int EventQueue::getQueueSize() const {
    return queue.size();
}

int EventQueue::getUnsentCount() const {
    int count = 0;
    for (const auto& queuedEvent : queue) {
        if (!queuedEvent.sent) {
            count++;
        }
    }
    return count;
}

void EventQueue::clearSentEvents() {
    queue.erase(
        std::remove_if(queue.begin(), queue.end(),
            [](const QueuedEvent& e) { return e.sent; }),
        queue.end()
    );
    saveToDisk();
}

void EventQueue::clearAll() {
    queue.clear();
    saveToDisk();
}

bool EventQueue::saveToDisk() {
    File file = SPIFFS.open(QUEUE_FILE, FILE_WRITE);
    if (!file) {
        Serial.println("Failed to open queue file for writing");
        return false;
    }

    DynamicJsonDocument doc(8192);
    JsonArray events = doc.createNestedArray("events");

    for (const auto& queuedEvent : queue) {
        JsonObject e = events.createNestedObject();
        e["deviceId"] = queuedEvent.deviceId;
        e["sent"] = queuedEvent.sent;

        JsonObject evt = e.createNestedObject("event");
        evt["magnitude"] = queuedEvent.event.magnitude;
        evt["pga"] = queuedEvent.event.pga;
        evt["pgv"] = queuedEvent.event.pgv;
        evt["cav"] = queuedEvent.event.cav;
        evt["startTime"] = queuedEvent.event.startTime;
        evt["duration"] = queuedEvent.event.duration;
        evt["alertLevel"] = queuedEvent.event.alertLevel;
        evt["confirmed"] = queuedEvent.event.confirmed;
    }

    serializeJson(doc, file);
    file.close();

    return true;
}

bool EventQueue::loadFromDisk() {
    if (!SPIFFS.exists(QUEUE_FILE)) {
        return true;
    }

    File file = SPIFFS.open(QUEUE_FILE, FILE_READ);
    if (!file) {
        Serial.println("Failed to open queue file for reading");
        return false;
    }

    DynamicJsonDocument doc(8192);
    DeserializationError error = deserializeJson(doc, file);
    file.close();

    if (error) {
        Serial.println("Failed to parse queue file");
        return false;
    }

    queue.clear();
    JsonArray events = doc["events"];

    for (JsonObject e : events) {
        QueuedEvent queuedEvent;
        queuedEvent.deviceId = e["deviceId"].as<String>();
        queuedEvent.sent = e["sent"];

        JsonObject evt = e["event"];
        queuedEvent.event.magnitude = evt["magnitude"];
        queuedEvent.event.pga = evt["pga"];
        queuedEvent.event.pgv = evt["pgv"];
        queuedEvent.event.cav = evt["cav"];
        queuedEvent.event.startTime = evt["startTime"];
        queuedEvent.event.duration = evt["duration"];
        queuedEvent.event.alertLevel = evt["alertLevel"].as<String>();
        queuedEvent.event.confirmed = evt["confirmed"];

        queue.push_back(queuedEvent);
    }

    return true;
}
