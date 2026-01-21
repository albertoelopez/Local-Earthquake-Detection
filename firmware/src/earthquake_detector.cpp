#include "earthquake_detector.h"
#include "config.h"
#include <cmath>

EarthquakeDetector::EarthquakeDetector(int sampleRate, float staWindowSec, float ltaWindowSec,
                                       float triggerThreshold, float detriggerThreshold)
    : sampleRate(sampleRate),
      staWindowSamples(static_cast<int>(staWindowSec * sampleRate)),
      ltaWindowSamples(static_cast<int>(ltaWindowSec * sampleRate)),
      triggerThreshold(triggerThreshold),
      detriggerThreshold(detriggerThreshold),
      triggered(false),
      triggerTime(0) {
    sampleBuffer.reserve(ltaWindowSamples + staWindowSamples);
}

void EarthquakeDetector::init() {
    reset();
}

void EarthquakeDetector::addSample(float ax, float ay, float az) {
    AccelSample sample;
    sample.x = ax;
    sample.y = ay;
    sample.z = az;
    sample.timestamp = millis();

    updateBuffers(sample);

    if (sampleBuffer.size() >= ltaWindowSamples) {
        float sta = calculateSTA();
        float lta = calculateLTA();
        float ratio = (lta > 0.0001f) ? sta / lta : 0.0f;

        if (!triggered && ratio > triggerThreshold) {
            triggered = true;
            triggerTime = sample.timestamp;
            currentEvent.startTime = triggerTime;
            currentEvent.pga = 0.0f;
            currentEvent.cav = 0.0f;
        }

        if (triggered) {
            float currentMag = calculateMagnitude(ax, ay, az);
            float pga = calculatePGA();

            if (pga > currentEvent.pga) {
                currentEvent.pga = pga;
            }

            currentEvent.cav = calculateCAV();
            currentEvent.alertLevel = determineAlertLevel(currentEvent.pga);

            if (ratio < detriggerThreshold) {
                currentEvent.duration = sample.timestamp - triggerTime;

                if (currentEvent.duration >= MIN_EVENT_DURATION_SEC * 1000) {
                    currentEvent.confirmed = true;
                    currentEvent.magnitude = calculateMagnitudeEstimate(currentEvent.pga, 10.0f);
                }

                triggered = false;
            }
        }
    }
}

void EarthquakeDetector::updateBuffers(const AccelSample& sample) {
    sampleBuffer.push_back(sample);

    int maxBufferSize = ltaWindowSamples + staWindowSamples;
    if (sampleBuffer.size() > maxBufferSize) {
        sampleBuffer.erase(sampleBuffer.begin());
    }
}

float EarthquakeDetector::calculateMagnitude(float ax, float ay, float az) const {
    float gravityCompensated = std::sqrt(ax*ax + ay*ay + az*az) - 9.81f;
    return std::abs(gravityCompensated);
}

float EarthquakeDetector::calculateSTA() const {
    if (sampleBuffer.size() < staWindowSamples) {
        return 0.0f;
    }

    float sum = 0.0f;
    int startIdx = sampleBuffer.size() - staWindowSamples;

    for (int i = startIdx; i < sampleBuffer.size(); i++) {
        const AccelSample& s = sampleBuffer[i];
        float mag = calculateMagnitude(s.x, s.y, s.z);
        sum += mag * mag;
    }

    return sum / staWindowSamples;
}

float EarthquakeDetector::calculateLTA() const {
    if (sampleBuffer.size() < ltaWindowSamples) {
        return 0.0f;
    }

    float sum = 0.0f;
    int startIdx = sampleBuffer.size() - ltaWindowSamples;

    for (int i = startIdx; i < sampleBuffer.size() - staWindowSamples; i++) {
        const AccelSample& s = sampleBuffer[i];
        float mag = calculateMagnitude(s.x, s.y, s.z);
        sum += mag * mag;
    }

    int ltaSamples = ltaWindowSamples - staWindowSamples;
    return (ltaSamples > 0) ? sum / ltaSamples : 0.0f;
}

float EarthquakeDetector::calculatePGA() const {
    if (sampleBuffer.empty()) {
        return 0.0f;
    }

    float maxPGA = 0.0f;
    int windowSize = std::min(static_cast<int>(sampleBuffer.size()),
                              static_cast<int>(3 * sampleRate));
    int startIdx = sampleBuffer.size() - windowSize;

    for (int i = startIdx; i < sampleBuffer.size(); i++) {
        const AccelSample& s = sampleBuffer[i];
        float mag = calculateMagnitude(s.x, s.y, s.z);
        float pgaG = mag / 9.81f;
        if (pgaG > maxPGA) {
            maxPGA = pgaG;
        }
    }

    return maxPGA;
}

float EarthquakeDetector::calculateCAV() const {
    if (sampleBuffer.empty()) {
        return 0.0f;
    }

    float cav = 0.0f;
    float dt = 1.0f / sampleRate;
    int startIdx = 0;

    if (triggerTime > 0) {
        for (int i = 0; i < sampleBuffer.size(); i++) {
            if (sampleBuffer[i].timestamp >= triggerTime) {
                startIdx = i;
                break;
            }
        }
    }

    for (int i = startIdx; i < sampleBuffer.size(); i++) {
        const AccelSample& s = sampleBuffer[i];
        float mag = calculateMagnitude(s.x, s.y, s.z);
        float pgaG = mag / 9.81f;
        cav += std::abs(pgaG) * dt;
    }

    return cav;
}

float EarthquakeDetector::calculateMagnitudeEstimate(float pga, float distance) const {
    float pgaCmS2 = pga * 981.0f;

    float C1 = 2.0f;
    float C2 = 0.6f;
    float C3 = 1.0f;
    float C4 = 5.0f;
    float C5 = 0.003f;

    float Mw = (std::log10(pgaCmS2) - C1 + C3*std::log10(distance + C4) + C5*distance) / C2;

    return std::max(0.0f, std::min(10.0f, Mw));
}

String EarthquakeDetector::determineAlertLevel(float pga) const {
    if (pga >= PGA_THRESHOLD_VIOLENT) {
        return "EXTREME";
    } else if (pga >= PGA_THRESHOLD_SEVERE) {
        return "SEVERE";
    } else if (pga >= PGA_THRESHOLD_STRONG) {
        return "STRONG";
    } else if (pga >= PGA_THRESHOLD_MODERATE) {
        return "MODERATE";
    } else if (pga >= PGA_THRESHOLD_LIGHT) {
        return "LIGHT";
    }
    return "NEGLIGIBLE";
}

bool EarthquakeDetector::isTriggered() const {
    return triggered;
}

EarthquakeEvent EarthquakeDetector::getCurrentEvent() const {
    return currentEvent;
}

float EarthquakeDetector::getStaLtaRatio() const {
    float sta = calculateSTA();
    float lta = calculateLTA();
    return (lta > 0.0001f) ? sta / lta : 0.0f;
}

float EarthquakeDetector::getCurrentPGA() const {
    return calculatePGA();
}

float EarthquakeDetector::getCurrentCAV() const {
    return calculateCAV();
}

void EarthquakeDetector::reset() {
    sampleBuffer.clear();
    triggered = false;
    triggerTime = 0;
    currentEvent = EarthquakeEvent();
}

ButterworthFilter::ButterworthFilter(float sampleRate, float lowCutoff, float highCutoff, int order)
    : order(order) {

    float wl = 2.0f * lowCutoff / sampleRate;
    float wh = 2.0f * highCutoff / sampleRate;

    float bw = wh - wl;
    float w0 = std::sqrt(wl * wh);

    float alpha = std::sin(PI * w0) * std::sinh(std::log(2.0f) / 2.0f * bw * PI * w0 / std::sin(PI * w0));

    float cosW0 = std::cos(PI * w0);

    b[0] = alpha;
    b[1] = 0.0f;
    b[2] = -alpha;

    a[0] = 1.0f + alpha;
    a[1] = -2.0f * cosW0;
    a[2] = 1.0f - alpha;

    for (int i = 0; i < 3; i++) {
        b[i] /= a[0];
    }
    a[1] /= a[0];
    a[2] /= a[0];
    a[0] = 1.0f;

    reset();
}

float ButterworthFilter::process(float input) {
    for (int i = 4; i > 0; i--) {
        x[i] = x[i-1];
        y[i] = y[i-1];
    }
    x[0] = input;

    y[0] = b[0]*x[0] + b[1]*x[1] + b[2]*x[2] - a[1]*y[1] - a[2]*y[2];

    return y[0];
}

void ButterworthFilter::reset() {
    for (int i = 0; i < 5; i++) {
        x[i] = 0.0f;
        y[i] = 0.0f;
    }
}

KalmanFilter::KalmanFilter(float processNoise, float measurementNoise)
    : Q(processNoise), R(measurementNoise), P(1.0f), K(0.0f), X(0.0f) {}

float KalmanFilter::update(float measurement) {
    P = P + Q;
    K = P / (P + R);
    X = X + K * (measurement - X);
    P = (1.0f - K) * P;
    return X;
}

void KalmanFilter::reset() {
    P = 1.0f;
    K = 0.0f;
    X = 0.0f;
}
