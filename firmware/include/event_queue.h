#ifndef EVENT_QUEUE_H
#define EVENT_QUEUE_H

#include <Arduino.h>
#include <SPIFFS.h>
#include <vector>
#include "earthquake_detector.h"

#define MAX_QUEUE_SIZE 100
#define QUEUE_FILE "/event_queue.json"

struct QueuedEvent {
    EarthquakeEvent event;
    String deviceId;
    bool sent;
};

class EventQueue {
public:
    EventQueue();
    bool init();
    bool addEvent(const EarthquakeEvent& event, const String& deviceId);
    bool processQueue(std::function<bool(const QueuedEvent&)> sendFunction);
    int getQueueSize() const;
    int getUnsentCount() const;
    void clearSentEvents();
    void clearAll();

private:
    std::vector<QueuedEvent> queue;
    bool saveToDisk();
    bool loadFromDisk();
};

#endif
