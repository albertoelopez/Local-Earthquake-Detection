#ifndef EARTHQUAKE_DETECTOR_H
#define EARTHQUAKE_DETECTOR_H

#include <Arduino.h>
#include <vector>

struct AccelSample {
    float x;
    float y;
    float z;
    unsigned long timestamp;
};

struct EarthquakeEvent {
    float magnitude;
    float pga;
    float pgv;
    float cav;
    unsigned long startTime;
    unsigned long duration;
    String alertLevel;
    bool confirmed;
};

class EarthquakeDetector {
public:
    EarthquakeDetector(int sampleRate, float staWindowSec, float ltaWindowSec,
                       float triggerThreshold, float detriggerThreshold);

    void init();
    void addSample(float ax, float ay, float az);
    bool isTriggered() const;
    EarthquakeEvent getCurrentEvent() const;
    float getStaLtaRatio() const;
    float getCurrentPGA() const;
    float getCurrentCAV() const;
    void reset();

    float calculateSTA() const;
    float calculateLTA() const;
    float calculatePGA() const;
    float calculateCAV() const;
    float calculateMagnitudeEstimate(float pga, float distance) const;
    String determineAlertLevel(float pga) const;

private:
    int sampleRate;
    int staWindowSamples;
    int ltaWindowSamples;
    float triggerThreshold;
    float detriggerThreshold;

    std::vector<AccelSample> sampleBuffer;
    bool triggered;
    unsigned long triggerTime;
    EarthquakeEvent currentEvent;

    float applyButterworthFilter(float input);
    float calculateMagnitude(float ax, float ay, float az) const;
    void updateBuffers(const AccelSample& sample);
};

class ButterworthFilter {
public:
    ButterworthFilter(float sampleRate, float lowCutoff, float highCutoff, int order);
    float process(float input);
    void reset();

private:
    float a[5];
    float b[5];
    float x[5];
    float y[5];
    int order;
};

class KalmanFilter {
public:
    KalmanFilter(float processNoise = 0.01f, float measurementNoise = 0.1f);
    float update(float measurement);
    void reset();

private:
    float Q;
    float R;
    float P;
    float K;
    float X;
};

#endif
