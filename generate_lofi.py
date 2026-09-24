import wave
import math
import struct
import random

SAMPLE_RATE = 44100
DURATION = 35.0  # seconds
BPM = 110
BEAT_DUR = 60.0 / BPM
EIGHTH_DUR = BEAT_DUR / 2

# Chord frequencies (Hz) - Upbeat Lo-Fi progression: Cmaj7, Am7, Dm7, G7
CHORDS = [
    [261.63, 329.63, 392.00, 493.88],  # Cmaj7 (C4, E4, G4, B4)
    [220.00, 261.63, 329.63, 392.00],  # Am7 (A3, C4, E4, G4)
    [293.66, 349.23, 440.00, 523.25],  # Dm7 (D4, F4, A4, C5)
    [196.00, 246.94, 293.66, 349.23]   # G7 (G3, B3, D4, F4)
]

def generate_sample(t, beat_idx, chord_idx):
    # 1. Warm Lo-Fi Synth Chord
    chord = CHORDS[chord_idx]
    chord_val = 0.0
    t_in_bar = t % (BEAT_DUR * 4)
    
    # Soft pluck envelope per chord change
    env = math.exp(-1.8 * (t_in_bar / (BEAT_DUR * 4))) * 0.4 + 0.15
    for freq in chord:
        # Warm sine + subtle 2nd harmonic (warm lo-fi tone)
        wave_val = 0.7 * math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t)
        chord_val += wave_val
    chord_val = (chord_val / len(chord)) * env * 0.35

    # 2. Upbeat Lo-Fi Drums (Kick, Snare, Hi-Hat)
    t_in_beat = t % BEAT_DUR
    beat_num = int((t / BEAT_DUR) % 4)
    
    drum_val = 0.0
    
    # Kick Drum on Beat 0 and 2.5
    is_kick = (beat_num == 0 and t_in_beat < 0.15) or (beat_num == 2 and (t_in_beat - 0.5 * BEAT_DUR) > 0 and (t_in_beat - 0.5 * BEAT_DUR) < 0.15)
    if is_kick:
        dt = t_in_beat if beat_num == 0 else (t_in_beat - 0.5 * BEAT_DUR)
        if dt > 0:
            kick_freq = 120.0 * math.exp(-25.0 * dt)
            kick_env = math.exp(-18.0 * dt)
            drum_val += math.sin(2 * math.pi * kick_freq * dt) * kick_env * 0.55

    # Soft Lo-Fi Snare on Beat 1 and 3
    if beat_num in (1, 3) and t_in_beat < 0.18:
        snare_env = math.exp(-22.0 * t_in_beat)
        snare_noise = (random.random() * 2.0 - 1.0) * 0.35
        snare_tone = math.sin(2 * math.pi * 180.0 * t_in_beat) * 0.25
        drum_val += (snare_noise + snare_tone) * snare_env * 0.45

    # Upbeat Hi-Hats on 8th notes
    t_in_eighth = t % EIGHTH_DUR
    if t_in_eighth < 0.05:
        hat_env = math.exp(-60.0 * t_in_eighth)
        hat_noise = (random.random() * 2.0 - 1.0) * 0.15
        drum_val += hat_noise * hat_env

    # 3. Subtle Lo-Fi Vinyl Crackle Warmth
    vinyl_crackle = (random.random() * 2.0 - 1.0) * 0.015
    if random.random() < 0.002:  # occasional warm pop
        vinyl_crackle += (random.random() * 2.0 - 1.0) * 0.08

    total = chord_val + drum_val + vinyl_crackle
    # Soft clipping / limiting
    total = max(-0.95, min(0.95, total))
    return int(total * 32767)

print("Generating upbeat lo-fi track...")
num_samples = int(SAMPLE_RATE * DURATION)
with wave.open("lofi_track.wav", "w") as wav_file:
    wav_file.setnchannels(1)  # Mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(SAMPLE_RATE)
    
    samples = bytearray()
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        beat_idx = int(t / BEAT_DUR)
        chord_idx = int((t / (BEAT_DUR * 4))) % len(CHORDS)
        
        sample = generate_sample(t, beat_idx, chord_idx)
        samples.extend(struct.pack("<h", sample))
        
    wav_file.writeframes(samples)

print("Lo-Fi track generated successfully: lofi_track.wav")
