import numpy as np
import pandas as pd
import h5py
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Generator
import os


class LANLDataLoader:

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.train_file = self.data_path / 'train.csv'
        self.segment_size = 150000

    def load_full_data(self) -> pd.DataFrame:
        if not self.train_file.exists():
            raise FileNotFoundError(f"Training file not found: {self.train_file}")
        return pd.read_csv(self.train_file)

    def load_segments(
        self,
        num_segments: Optional[int] = None,
        segment_size: Optional[int] = None
    ) -> Generator[Tuple[np.ndarray, float], None, None]:
        segment_size = segment_size or self.segment_size

        chunk_size = segment_size * 10
        segments_yielded = 0

        for chunk in pd.read_csv(self.train_file, chunksize=chunk_size):
            acoustic_data = chunk['acoustic_data'].values
            time_to_failure = chunk['time_to_failure'].values

            for i in range(0, len(acoustic_data) - segment_size, segment_size):
                if num_segments and segments_yielded >= num_segments:
                    return

                segment = acoustic_data[i:i + segment_size]
                ttf = time_to_failure[i + segment_size - 1]

                yield segment, ttf
                segments_yielded += 1

    def load_test_segments(self) -> Generator[Tuple[str, np.ndarray], None, None]:
        test_dir = self.data_path / 'test'

        if not test_dir.exists():
            return

        for test_file in sorted(test_dir.glob('*.csv')):
            df = pd.read_csv(test_file)
            segment_id = test_file.stem
            yield segment_id, df['acoustic_data'].values


class STEADDataLoader:

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.metadata_file = self.data_path / 'metadata.csv'
        self.waveforms_file = self.data_path / 'waveforms.hdf5'

    def load_metadata(
        self,
        filter_params: Optional[Dict] = None
    ) -> pd.DataFrame:
        if not self.metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_file}")

        df = pd.read_csv(self.metadata_file)

        if filter_params:
            if 'trace_category' in filter_params:
                df = df[df['trace_category'] == filter_params['trace_category']]
            if 'min_magnitude' in filter_params:
                df = df[df['source_magnitude'] >= filter_params['min_magnitude']]
            if 'max_magnitude' in filter_params:
                df = df[df['source_magnitude'] <= filter_params['max_magnitude']]
            if 'min_distance' in filter_params:
                df = df[df['source_distance_km'] >= filter_params['min_distance']]
            if 'max_distance' in filter_params:
                df = df[df['source_distance_km'] <= filter_params['max_distance']]

        return df

    def load_waveforms(
        self,
        trace_names: List[str],
        normalize: bool = True
    ) -> Dict[str, np.ndarray]:
        if not self.waveforms_file.exists():
            raise FileNotFoundError(f"Waveforms file not found: {self.waveforms_file}")

        waveforms = {}

        with h5py.File(self.waveforms_file, 'r') as f:
            for trace_name in trace_names:
                if trace_name in f['data']:
                    waveform = f['data'][trace_name][()]

                    if normalize:
                        max_val = np.max(np.abs(waveform))
                        if max_val > 0:
                            waveform = waveform / max_val

                    waveforms[trace_name] = waveform

        return waveforms

    def load_batch(
        self,
        batch_size: int = 32,
        filter_params: Optional[Dict] = None,
        shuffle: bool = True
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        metadata = self.load_metadata(filter_params)

        if shuffle:
            metadata = metadata.sample(frac=1).reset_index(drop=True)

        with h5py.File(self.waveforms_file, 'r') as f:
            for i in range(0, len(metadata), batch_size):
                batch_meta = metadata.iloc[i:i + batch_size]

                waveforms = []
                labels = []

                for _, row in batch_meta.iterrows():
                    trace_name = row['trace_name']
                    if trace_name in f['data']:
                        waveform = f['data'][trace_name][()]
                        waveforms.append(waveform)
                        labels.append(1 if row['trace_category'] == 'earthquake_local' else 0)

                if waveforms:
                    yield np.array(waveforms), np.array(labels)


class SyntheticDataGenerator:

    def __init__(self, sampling_rate: int = 100, duration: float = 60.0):
        self.sampling_rate = sampling_rate
        self.duration = duration
        self.num_samples = int(sampling_rate * duration)

    def generate_noise(self, amplitude: float = 0.01) -> np.ndarray:
        return np.random.randn(self.num_samples) * amplitude

    def generate_earthquake(
        self,
        magnitude: float = 5.0,
        distance_km: float = 50.0,
        p_arrival: float = 10.0,
        s_arrival: float = 18.0
    ) -> Tuple[np.ndarray, Dict]:
        t = np.linspace(0, self.duration, self.num_samples)
        signal = np.zeros(self.num_samples)

        pga_scale = 10 ** (0.5 * magnitude - 0.5 * np.log10(distance_km + 10))

        p_wave_duration = 3.0
        p_wave_freq = 5.0
        p_wave_amplitude = pga_scale * 0.3

        p_mask = (t >= p_arrival) & (t < p_arrival + p_wave_duration)
        t_p = t[p_mask] - p_arrival
        p_envelope = np.exp(-t_p / 1.0) * (1 - np.exp(-t_p * 5))
        p_wave = p_wave_amplitude * np.sin(2 * np.pi * p_wave_freq * t_p) * p_envelope
        signal[p_mask] += p_wave

        s_wave_duration = 10.0
        s_wave_freq = 2.0
        s_wave_amplitude = pga_scale

        s_mask = (t >= s_arrival) & (t < s_arrival + s_wave_duration)
        t_s = t[s_mask] - s_arrival
        s_envelope = np.exp(-t_s / 3.0) * (1 - np.exp(-t_s * 3))
        s_wave = s_wave_amplitude * np.sin(2 * np.pi * s_wave_freq * t_s) * s_envelope
        signal[s_mask] += s_wave

        noise = self.generate_noise(amplitude=pga_scale * 0.05)
        signal += noise

        metadata = {
            'magnitude': magnitude,
            'distance_km': distance_km,
            'p_arrival': p_arrival,
            's_arrival': s_arrival,
            'pga': np.max(np.abs(signal)),
            'duration': self.duration
        }

        return signal, metadata

    def generate_non_earthquake(
        self,
        event_type: str = 'traffic'
    ) -> Tuple[np.ndarray, Dict]:
        t = np.linspace(0, self.duration, self.num_samples)
        signal = self.generate_noise(amplitude=0.01)

        if event_type == 'traffic':
            freq = 15 + np.random.rand() * 10
            amplitude = 0.02 + np.random.rand() * 0.03
            modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t)
            signal += amplitude * np.sin(2 * np.pi * freq * t) * modulation

        elif event_type == 'footsteps':
            num_steps = int(self.duration * 2)
            for step in range(num_steps):
                step_time = step * 0.5 + np.random.rand() * 0.1
                if step_time < self.duration:
                    step_idx = int(step_time * self.sampling_rate)
                    if step_idx < self.num_samples - 10:
                        impact = np.exp(-np.linspace(0, 5, 10))
                        signal[step_idx:step_idx + 10] += 0.05 * impact * (1 + np.random.rand())

        elif event_type == 'door_slam':
            slam_time = 10.0 + np.random.rand() * 10
            slam_idx = int(slam_time * self.sampling_rate)
            if slam_idx < self.num_samples - 50:
                impact = np.exp(-np.linspace(0, 10, 50)) * np.sin(np.linspace(0, 20*np.pi, 50))
                signal[slam_idx:slam_idx + 50] += 0.1 * impact

        metadata = {
            'event_type': event_type,
            'pga': np.max(np.abs(signal)),
            'duration': self.duration
        }

        return signal, metadata

    def generate_dataset(
        self,
        num_earthquakes: int = 100,
        num_non_earthquakes: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, List[Dict]]:
        signals = []
        labels = []
        metadata_list = []

        for _ in range(num_earthquakes):
            magnitude = 3.0 + np.random.rand() * 4.0
            distance = 10.0 + np.random.rand() * 200.0
            signal, meta = self.generate_earthquake(magnitude, distance)
            signals.append(signal)
            labels.append(1)
            meta['label'] = 'earthquake'
            metadata_list.append(meta)

        non_eq_types = ['traffic', 'footsteps', 'door_slam']
        for i in range(num_non_earthquakes):
            event_type = non_eq_types[i % len(non_eq_types)]
            signal, meta = self.generate_non_earthquake(event_type)
            signals.append(signal)
            labels.append(0)
            meta['label'] = 'non_earthquake'
            metadata_list.append(meta)

        indices = np.random.permutation(len(signals))
        signals = np.array(signals)[indices]
        labels = np.array(labels)[indices]
        metadata_list = [metadata_list[i] for i in indices]

        return signals, labels, metadata_list


def download_kaggle_dataset(dataset_name: str, output_path: str) -> None:
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()

        os.makedirs(output_path, exist_ok=True)

        if '/' in dataset_name:
            api.dataset_download_files(dataset_name, path=output_path, unzip=True)
        else:
            api.competition_download_files(dataset_name, path=output_path)

        print(f"Dataset downloaded to {output_path}")

    except Exception as e:
        print(f"Failed to download dataset: {e}")
        print("Please download manually from Kaggle and place in the data directory")


if __name__ == "__main__":
    print("Testing SyntheticDataGenerator...")
    generator = SyntheticDataGenerator(sampling_rate=100, duration=60.0)

    eq_signal, eq_meta = generator.generate_earthquake(magnitude=5.5, distance_km=50)
    print(f"Generated earthquake signal: shape={eq_signal.shape}, PGA={eq_meta['pga']:.4f}")

    noise_signal, noise_meta = generator.generate_non_earthquake('traffic')
    print(f"Generated traffic signal: shape={noise_signal.shape}, PGA={noise_meta['pga']:.4f}")

    X, y, metadata = generator.generate_dataset(num_earthquakes=50, num_non_earthquakes=50)
    print(f"\nGenerated dataset: X={X.shape}, y={y.shape}")
    print(f"Earthquake samples: {np.sum(y == 1)}")
    print(f"Non-earthquake samples: {np.sum(y == 0)}")
