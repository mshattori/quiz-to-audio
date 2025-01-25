from pydub import AudioSegment
import numpy as np

sampling_rate = 44100
frequency = 880
duration = 0.25
amplitude = 0.5

# Make a sine wave
t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
sine_wave = amplitude * np.sin(2 * np.pi * frequency * t)

audio_segment = AudioSegment(
    (sine_wave * frequency).astype(np.int16).tobytes(),
    frame_rate=sampling_rate,
    sample_width=2,  # 16bit
    channels=1
)
audio_segment = audio_segment.apply_gain(volume_change=10.0)

audio_segment.export('beep.mp3', format='mp3')
