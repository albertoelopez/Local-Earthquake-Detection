import numpy as np
import pandas as pd
from scipy import stats, signal
from scipy.fft import fft, fftfreq
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def extract_statistical_features(segment: np.ndarray) -> Dict[str, float]:
    mean = np.mean(segment)
    std = np.std(segment)

    features = {
        'mean': mean,
        'std': std,
        'var': np.var(segment),
        'min': np.min(segment),
        'max': np.max(segment),
        'range': np.ptp(segment),
        'median': np.median(segment),
        'mad': np.mean(np.abs(segment - mean)),
        'skewness': stats.skew(segment),
        'kurtosis': stats.kurtosis(segment),
        'rms': np.sqrt(np.mean(segment**2)),
        'crest_factor': np.max(np.abs(segment)) / (np.sqrt(np.mean(segment**2)) + 1e-10),
    }

    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    for p in percentiles:
        features[f'percentile_{p}'] = np.percentile(segment, p)

    features['iqr'] = features['percentile_75'] - features['percentile_25']

    return features


def extract_frequency_features(segment: np.ndarray, sampling_rate: int = 100) -> Dict[str, float]:
    N = len(segment)
    yf = fft(segment)
    xf = fftfreq(N, 1/sampling_rate)[:N//2]
    power = 2.0/N * np.abs(yf[:N//2])

    features = {
        'fft_mean': np.mean(power),
        'fft_std': np.std(power),
        'fft_max': np.max(power),
        'fft_min': np.min(power),
        'dominant_freq': xf[np.argmax(power)] if len(power) > 0 else 0,
    }

    total_power = np.sum(power)
    if total_power > 0:
        features['spectral_centroid'] = np.sum(xf * power) / total_power
        features['spectral_spread'] = np.sqrt(
            np.sum(((xf - features['spectral_centroid'])**2) * power) / total_power
        )

        cumsum_power = np.cumsum(power)
        rolloff_idx = np.where(cumsum_power >= 0.85 * total_power)[0]
        features['spectral_rolloff'] = xf[rolloff_idx[0]] if len(rolloff_idx) > 0 else xf[-1]

        features['spectral_flatness'] = stats.gmean(power + 1e-10) / (np.mean(power) + 1e-10)
    else:
        features['spectral_centroid'] = 0
        features['spectral_spread'] = 0
        features['spectral_rolloff'] = 0
        features['spectral_flatness'] = 0

    freq_bands = [(0.1, 1), (1, 5), (5, 10), (10, 20), (20, 50)]
    for low, high in freq_bands:
        mask = (xf >= low) & (xf < high)
        features[f'power_{low}_{high}hz'] = np.sum(power[mask]) if np.any(mask) else 0

    return features


def extract_time_domain_features(segment: np.ndarray, sampling_rate: int = 100) -> Dict[str, float]:
    features = {}

    zero_crossings = np.where(np.diff(np.sign(segment)))[0]
    features['zero_crossing_rate'] = len(zero_crossings) / len(segment)

    mean_crossing_rate = np.where(np.diff(np.sign(segment - np.mean(segment))))[0]
    features['mean_crossing_rate'] = len(mean_crossing_rate) / len(segment)

    threshold = np.std(segment)
    peaks, properties = signal.find_peaks(segment, height=threshold, distance=sampling_rate//10)
    features['num_peaks'] = len(peaks)
    features['peak_density'] = len(peaks) / len(segment)

    if len(peaks) > 1:
        peak_intervals = np.diff(peaks)
        features['peak_interval_mean'] = np.mean(peak_intervals)
        features['peak_interval_std'] = np.std(peak_intervals)
    else:
        features['peak_interval_mean'] = 0
        features['peak_interval_std'] = 0

    if 'peak_heights' in properties and len(properties['peak_heights']) > 0:
        features['peak_height_mean'] = np.mean(properties['peak_heights'])
        features['peak_height_max'] = np.max(properties['peak_heights'])
    else:
        features['peak_height_mean'] = 0
        features['peak_height_max'] = 0

    features['energy'] = np.sum(segment**2)
    features['log_energy'] = np.log(features['energy'] + 1e-10)

    envelope = np.abs(signal.hilbert(segment))
    features['envelope_mean'] = np.mean(envelope)
    features['envelope_std'] = np.std(envelope)
    features['envelope_max'] = np.max(envelope)

    return features


def extract_seismic_features(segment: np.ndarray, sampling_rate: int = 100) -> Dict[str, float]:
    features = {}

    dt = 1.0 / sampling_rate
    velocity = np.cumsum(segment) * dt
    displacement = np.cumsum(velocity) * dt

    features['pgv'] = np.max(np.abs(velocity))
    features['pgd'] = np.max(np.abs(displacement))
    features['pga'] = np.max(np.abs(segment)) / 9.81

    features['cav'] = np.sum(np.abs(segment)) * dt / 9.81

    arias_intensity = np.pi / (2 * 9.81) * np.sum(segment**2) * dt
    features['arias_intensity'] = arias_intensity

    features['significant_duration'] = calculate_significant_duration(segment, sampling_rate)

    return features


def calculate_significant_duration(segment: np.ndarray, sampling_rate: int = 100) -> float:
    dt = 1.0 / sampling_rate
    cumulative_energy = np.cumsum(segment**2) * dt
    total_energy = cumulative_energy[-1]

    if total_energy == 0:
        return 0

    normalized_energy = cumulative_energy / total_energy

    t5_idx = np.where(normalized_energy >= 0.05)[0]
    t95_idx = np.where(normalized_energy >= 0.95)[0]

    if len(t5_idx) > 0 and len(t95_idx) > 0:
        return (t95_idx[0] - t5_idx[0]) / sampling_rate
    return 0


def calculate_sta_lta(
    segment: np.ndarray,
    sampling_rate: int = 100,
    sta_window: float = 1.0,
    lta_window: float = 30.0
) -> np.ndarray:
    sta_samples = int(sta_window * sampling_rate)
    lta_samples = int(lta_window * sampling_rate)

    squared = segment**2

    sta = np.convolve(squared, np.ones(sta_samples)/sta_samples, mode='same')
    lta = np.convolve(squared, np.ones(lta_samples)/lta_samples, mode='same')

    sta_lta = sta / (lta + 1e-10)

    return sta_lta


def extract_sta_lta_features(
    segment: np.ndarray,
    sampling_rate: int = 100
) -> Dict[str, float]:
    sta_lta = calculate_sta_lta(segment, sampling_rate)

    features = {
        'sta_lta_max': np.max(sta_lta),
        'sta_lta_mean': np.mean(sta_lta),
        'sta_lta_std': np.std(sta_lta),
        'sta_lta_trigger_count': np.sum(sta_lta > 5.0),
    }

    return features


def extract_all_features(
    segment: np.ndarray,
    sampling_rate: int = 100
) -> Dict[str, float]:
    features = {}

    features.update(extract_statistical_features(segment))
    features.update(extract_frequency_features(segment, sampling_rate))
    features.update(extract_time_domain_features(segment, sampling_rate))
    features.update(extract_seismic_features(segment, sampling_rate))
    features.update(extract_sta_lta_features(segment, sampling_rate))

    return features


def process_multiaxis_data(
    ax: np.ndarray,
    ay: np.ndarray,
    az: np.ndarray,
    sampling_rate: int = 100
) -> Dict[str, float]:
    features = {}

    magnitude = np.sqrt(ax**2 + ay**2 + az**2)
    horizontal = np.sqrt(ax**2 + ay**2)

    for axis_name, axis_data in [('x', ax), ('y', ay), ('z', az),
                                   ('mag', magnitude), ('horiz', horizontal)]:
        axis_features = extract_all_features(axis_data, sampling_rate)
        for key, value in axis_features.items():
            features[f'{axis_name}_{key}'] = value

    features['vertical_horizontal_ratio'] = np.max(np.abs(az)) / (np.max(np.abs(horizontal)) + 1e-10)

    from scipy.stats import pearsonr
    features['corr_xy'], _ = pearsonr(ax, ay)
    features['corr_xz'], _ = pearsonr(ax, az)
    features['corr_yz'], _ = pearsonr(ay, az)

    return features


class FeatureExtractor:
    def __init__(self, sampling_rate: int = 100):
        self.sampling_rate = sampling_rate
        self.feature_names: Optional[List[str]] = None

    def fit(self, X: np.ndarray) -> 'FeatureExtractor':
        if len(X.shape) == 1:
            sample_features = extract_all_features(X[:1000], self.sampling_rate)
        else:
            sample_features = process_multiaxis_data(
                X[0, :, 0], X[0, :, 1], X[0, :, 2], self.sampling_rate
            )
        self.feature_names = list(sample_features.keys())
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if len(X.shape) == 1:
            X = X.reshape(1, -1)

        features_list = []
        for i in range(len(X)):
            if len(X.shape) == 2:
                features = extract_all_features(X[i], self.sampling_rate)
            else:
                features = process_multiaxis_data(
                    X[i, :, 0], X[i, :, 1], X[i, :, 2], self.sampling_rate
                )
            features_list.append(features)

        if self.feature_names is None:
            self.feature_names = list(features_list[0].keys())

        return np.array([[f[name] for name in self.feature_names] for f in features_list])

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)

    def get_feature_names(self) -> List[str]:
        return self.feature_names or []


if __name__ == "__main__":
    np.random.seed(42)

    t = np.linspace(0, 10, 1000)
    noise = np.random.randn(1000) * 0.1
    signal_clean = np.sin(2 * np.pi * 2 * t) * np.exp(-t/5)
    test_signal = signal_clean + noise

    print("Single-axis feature extraction:")
    features = extract_all_features(test_signal, sampling_rate=100)
    for name, value in sorted(features.items()):
        print(f"  {name}: {value:.6f}")

    print(f"\nTotal features extracted: {len(features)}")

    extractor = FeatureExtractor(sampling_rate=100)
    X = np.random.randn(10, 1000)
    X_features = extractor.fit_transform(X)
    print(f"\nBatch extraction shape: {X_features.shape}")
    print(f"Feature names: {extractor.get_feature_names()[:10]}...")
