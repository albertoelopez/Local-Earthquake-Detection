import pytest
import numpy as np
from feature_extraction import (
    extract_statistical_features,
    extract_frequency_features,
    extract_time_domain_features,
    extract_seismic_features,
    extract_sta_lta_features,
    extract_all_features,
    calculate_sta_lta,
    calculate_significant_duration,
    FeatureExtractor,
    ButterworthFilter,
    KalmanFilter
)


class TestStatisticalFeatures:
    def test_basic_statistics(self):
        signal = np.array([1, 2, 3, 4, 5])
        features = extract_statistical_features(signal)

        assert features['mean'] == 3.0
        assert features['median'] == 3.0
        assert features['min'] == 1.0
        assert features['max'] == 5.0
        assert features['range'] == 4.0

    def test_variance_and_std(self):
        signal = np.array([1, 2, 3, 4, 5])
        features = extract_statistical_features(signal)

        assert features['std'] == pytest.approx(np.std(signal), rel=1e-6)
        assert features['var'] == pytest.approx(np.var(signal), rel=1e-6)

    def test_percentiles(self):
        signal = np.random.randn(1000)
        features = extract_statistical_features(signal)

        assert 'percentile_1' in features
        assert 'percentile_50' in features
        assert 'percentile_99' in features
        assert features['percentile_50'] == pytest.approx(np.median(signal), rel=1e-6)

    def test_skewness_kurtosis(self):
        normal_signal = np.random.randn(10000)
        features = extract_statistical_features(normal_signal)

        assert abs(features['skewness']) < 0.5
        assert abs(features['kurtosis']) < 1.0


class TestFrequencyFeatures:
    def test_dominant_frequency_detection(self):
        sampling_rate = 100
        t = np.linspace(0, 10, 1000)
        dominant_freq = 5.0
        signal = np.sin(2 * np.pi * dominant_freq * t)

        features = extract_frequency_features(signal, sampling_rate)

        assert abs(features['dominant_freq'] - dominant_freq) < 1.0

    def test_spectral_features_exist(self):
        signal = np.random.randn(1000)
        features = extract_frequency_features(signal, sampling_rate=100)

        assert 'fft_mean' in features
        assert 'fft_std' in features
        assert 'spectral_centroid' in features
        assert 'spectral_rolloff' in features
        assert 'spectral_flatness' in features

    def test_frequency_band_powers(self):
        signal = np.random.randn(1000)
        features = extract_frequency_features(signal, sampling_rate=100)

        assert 'power_0.1_1hz' in features
        assert 'power_1_5hz' in features
        assert 'power_5_10hz' in features
        assert 'power_10_20hz' in features


class TestTimeDomainFeatures:
    def test_zero_crossing_rate(self):
        t = np.linspace(0, 10, 1000)
        signal = np.sin(2 * np.pi * 2 * t)
        features = extract_time_domain_features(signal, sampling_rate=100)

        assert features['zero_crossing_rate'] > 0

    def test_peak_detection(self):
        t = np.linspace(0, 10, 1000)
        signal = np.sin(2 * np.pi * 1 * t)
        features = extract_time_domain_features(signal, sampling_rate=100)

        assert features['num_peaks'] > 0
        assert features['peak_density'] > 0

    def test_energy_calculation(self):
        signal = np.ones(100) * 2
        features = extract_time_domain_features(signal, sampling_rate=100)

        expected_energy = np.sum(signal**2)
        assert features['energy'] == pytest.approx(expected_energy, rel=1e-6)


class TestSeismicFeatures:
    def test_pga_calculation(self):
        signal = np.array([0, 1, 2, 1, 0, -1, -2, -1, 0]) * 9.81
        features = extract_seismic_features(signal, sampling_rate=100)

        assert features['pga'] == pytest.approx(2.0, rel=0.01)

    def test_cav_calculation(self):
        dt = 0.01
        signal = np.ones(100) * 9.81
        features = extract_seismic_features(signal, sampling_rate=100)

        expected_cav = np.sum(np.abs(signal)) * dt / 9.81
        assert features['cav'] == pytest.approx(expected_cav, rel=0.01)

    def test_pgv_pgd_exist(self):
        signal = np.random.randn(1000)
        features = extract_seismic_features(signal, sampling_rate=100)

        assert 'pgv' in features
        assert 'pgd' in features


class TestSTALTAFeatures:
    def test_sta_lta_calculation(self):
        background = np.random.randn(3000) * 0.1
        event = np.random.randn(1000) * 2.0
        signal = np.concatenate([background, event, background[:2000]])

        sta_lta = calculate_sta_lta(signal, sampling_rate=100, sta_window=1.0, lta_window=30.0)

        event_start = 3000
        max_ratio_idx = np.argmax(sta_lta)
        assert abs(max_ratio_idx - event_start) < 200

    def test_sta_lta_features(self):
        signal = np.random.randn(6000)
        features = extract_sta_lta_features(signal, sampling_rate=100)

        assert 'sta_lta_max' in features
        assert 'sta_lta_mean' in features
        assert 'sta_lta_std' in features


class TestSignificantDuration:
    def test_significant_duration_impulse(self):
        signal = np.zeros(1000)
        signal[500:510] = 1.0

        duration = calculate_significant_duration(signal, sampling_rate=100)
        assert duration < 1.0

    def test_significant_duration_long_event(self):
        signal = np.zeros(1000)
        signal[200:800] = np.sin(np.linspace(0, 10*np.pi, 600))

        duration = calculate_significant_duration(signal, sampling_rate=100)
        assert duration > 1.0


class TestAllFeatures:
    def test_all_features_count(self):
        signal = np.random.randn(6000)
        features = extract_all_features(signal, sampling_rate=100)

        assert len(features) > 50

    def test_no_nan_values(self):
        signal = np.random.randn(6000)
        features = extract_all_features(signal, sampling_rate=100)

        for name, value in features.items():
            assert not np.isnan(value), f"Feature {name} is NaN"

    def test_no_inf_values(self):
        signal = np.random.randn(6000)
        features = extract_all_features(signal, sampling_rate=100)

        for name, value in features.items():
            assert not np.isinf(value), f"Feature {name} is Inf"


class TestFeatureExtractor:
    def test_fit_transform(self):
        X = np.random.randn(10, 1000)
        extractor = FeatureExtractor(sampling_rate=100)

        X_features = extractor.fit_transform(X)

        assert X_features.shape[0] == 10
        assert X_features.shape[1] > 50

    def test_transform_after_fit(self):
        X_train = np.random.randn(10, 1000)
        X_test = np.random.randn(5, 1000)

        extractor = FeatureExtractor(sampling_rate=100)
        extractor.fit(X_train)

        X_train_features = extractor.transform(X_train)
        X_test_features = extractor.transform(X_test)

        assert X_train_features.shape[1] == X_test_features.shape[1]

    def test_get_feature_names(self):
        X = np.random.randn(5, 1000)
        extractor = FeatureExtractor(sampling_rate=100)
        extractor.fit_transform(X)

        feature_names = extractor.get_feature_names()

        assert len(feature_names) > 0
        assert all(isinstance(name, str) for name in feature_names)


class TestFilters:
    def test_butterworth_filter(self):
        t = np.linspace(0, 10, 1000)
        low_freq = np.sin(2 * np.pi * 1 * t)
        high_freq = np.sin(2 * np.pi * 30 * t)
        signal = low_freq + high_freq

        filter_obj = ButterworthFilter(
            sample_rate=100,
            low_cutoff=0.5,
            high_cutoff=10.0,
            order=2
        )

        filtered = np.array([filter_obj.process(s) for s in signal])

        from scipy.fft import fft, fftfreq
        N = len(filtered)
        yf = np.abs(fft(filtered[100:]))
        xf = fftfreq(N-100, 1/100)

        low_freq_power = np.sum(yf[np.abs(xf) < 5])
        high_freq_power = np.sum(yf[np.abs(xf) > 20])

        assert low_freq_power > high_freq_power * 2

    def test_kalman_filter(self):
        np.random.seed(42)
        true_signal = np.sin(np.linspace(0, 4*np.pi, 100))
        noisy_signal = true_signal + np.random.randn(100) * 0.5

        kf = KalmanFilter(process_noise=0.01, measurement_noise=0.5)
        filtered = np.array([kf.update(s) for s in noisy_signal])

        noisy_error = np.mean((noisy_signal - true_signal)**2)
        filtered_error = np.mean((filtered[10:] - true_signal[10:])**2)

        assert filtered_error < noisy_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
