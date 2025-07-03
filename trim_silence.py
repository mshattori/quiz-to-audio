#!/usr/bin/env python
import os
import argparse
import subprocess
import tempfile
import time
import numpy as np
from pydub import AudioSegment

def analyze_volume_distribution(input_file):
    """Analyze volume distribution across the entire audio file."""
    print("Analyzing audio volume distribution...")
    audio = AudioSegment.from_file(input_file)
    
    # Calculate volume levels for each segment (1 second intervals)
    segment_length = 1000  # 1 second
    segment_levels = []
    
    for i in range(0, len(audio), segment_length):
        segment = audio[i:i+segment_length]
        if len(segment) > 0:
            segment_samples = np.array(segment.get_array_of_samples())
            if segment.channels == 2:
                segment_samples = segment_samples.reshape((-1, 2))
                segment_samples = segment_samples.mean(axis=1)
            
            segment_float = segment_samples.astype(float) / (2**15)
            non_zero = segment_float[segment_float != 0]
            
            if len(non_zero) > 0:
                rms = np.sqrt(np.mean(non_zero**2))
                segment_dbfs = 20 * np.log10(rms) if rms > 0 else -60
            else:
                segment_dbfs = -60
            
            segment_levels.append(segment_dbfs)
    
    return np.array(segment_levels), len(audio) / 1000

def test_threshold_with_sample(input_file, threshold_db, min_silence=1.0, sample_duration=120):
    """Test threshold on a short sample for quick evaluation."""
    tmp_sample = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    tmp_result = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    
    try:
        # Extract sample
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-t", str(sample_duration),
            "-c", "copy",
            tmp_sample
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Apply silenceremove to sample
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_sample,
            "-af", f"silenceremove=start_periods=1:start_silence={min_silence}:"
                   f"start_threshold={threshold_db}dB:"
                   f"stop_periods=-1:stop_silence={min_silence}:"
                   f"stop_threshold={threshold_db}dB",
            tmp_result
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Calculate reduction percentage
        original = AudioSegment.from_file(tmp_sample)
        result = AudioSegment.from_file(tmp_result)
        
        original_len = len(original) / 1000
        result_len = len(result) / 1000
        reduction = (1 - result_len / original_len) * 100 if original_len > 0 else 0
        
        return reduction
        
    except Exception:
        return None
    finally:
        for f in [tmp_sample, tmp_result]:
            if os.path.exists(f):
                os.remove(f)

def generate_threshold_candidates(segment_levels):
    """Generate threshold candidates based on audio statistics."""
    quiet_10th = np.percentile(segment_levels, 10)
    quiet_25th = np.percentile(segment_levels, 25)
    
    candidates = [
        int(quiet_10th - 5),  # Aggressive
        int(quiet_10th),      # Standard
        int(quiet_25th),      # Conservative
        -30,                  # Fixed value 1
        -25,                  # Fixed value 2
        -20                   # Fixed value 3
    ]
    
    # Remove duplicates and filter reasonable range
    candidates = sorted(list(set([c for c in candidates if -50 <= c <= -10])))
    return candidates

def display_audio_statistics(segment_levels, total_length):
    """Display comprehensive audio statistics."""
    print(f"Audio length: {total_length:.1f}s")
    print(f"Volume statistics:")
    print(f"  Maximum: {np.max(segment_levels):.1f} dBFS")
    print(f"  Minimum: {np.min(segment_levels):.1f} dBFS")
    print(f"  Average: {np.mean(segment_levels):.1f} dBFS")
    print(f"  Median:  {np.median(segment_levels):.1f} dBFS")
    print(f"  10th percentile: {np.percentile(segment_levels, 10):.1f} dBFS")
    print(f"  25th percentile: {np.percentile(segment_levels, 25):.1f} dBFS")

def test_and_display_candidates(input_file, candidates):
    """Test threshold candidates and display results."""
    print(f"\nTesting threshold candidates on 2-minute sample:")
    print("Threshold | Reduction")
    print("----------|----------")
    
    results = []
    for threshold in candidates:
        reduction = test_threshold_with_sample(input_file, threshold)
        if reduction is not None:
            results.append((threshold, reduction))
            print(f"{threshold:8d}  | {reduction:6.1f}%")
        else:
            print(f"{threshold:8d}  | Error")
    
    return results

def get_user_threshold_choice(results, candidates):
    """Let user choose threshold from candidates or enter custom value."""
    print(f"\nRecommendations:")
    print(f"  • 20-40% reduction: Good balance")
    print(f"  • 40-60% reduction: Aggressive but effective")
    print(f"  • >60% reduction: May remove speech")
    
    while True:
        print(f"\nSelect threshold:")
        for i, (threshold, reduction) in enumerate(results, 1):
            print(f"  {i}. {threshold}dB ({reduction:.1f}% reduction)")
        print(f"  c. Custom threshold")
        
        choice = input("Enter choice (1-{} or 'c'): ".format(len(results))).strip().lower()
        
        if choice == 'c':
            try:
                custom = int(input("Enter custom threshold (dB): "))
                if -50 <= custom <= -10:
                    return custom
                else:
                    print("Please enter a value between -50 and -10")
            except ValueError:
                print("Please enter a valid number")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    return results[idx][0]
                else:
                    print(f"Please enter a number between 1 and {len(results)}")
            except ValueError:
                print("Please enter a valid choice")

def trim_with_ffmpeg(input_file, output_file, min_silence=1.0, threshold_db=-20):
    """Trim silence using FFmpeg with progress reporting."""
    # Get original audio length
    original_audio = AudioSegment.from_file(input_file)
    original_length = len(original_audio) / 1000
    print(f'Original audio length: {original_length:.1f}s')
    
    # Use FFmpeg to process and output directly to final format
    ff_cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-af", f"silenceremove=start_periods=1:start_silence={min_silence}:"
               f"start_threshold={threshold_db}dB:"
               f"stop_periods=-1:stop_silence={min_silence}:"
               f"stop_threshold={threshold_db}dB",
        output_file
    ]
    start_time = time.time()
    print(f'Trimming silence from "{input_file}" with FFmpeg...')
    subprocess.run(ff_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    end_time = time.time()
    print(f'Processing time: {end_time - start_time:.2f} seconds')

    # Get processed audio length for statistics
    processed_audio = AudioSegment.from_file(output_file)
    processed_length = len(processed_audio) / 1000
    reduction = original_length - processed_length
    reduction_percent = (reduction / original_length) * 100
    
    print(f'Processed audio length: {processed_length:.1f}s')
    print(f'Reduced by: {reduction:.1f}s ({reduction_percent:.1f}%)')

def smart_threshold_selection(input_file):
    """Analyze audio and let user select optimal threshold."""
    print(f"Audio file: {input_file}")
    
    # 1. Analyze volume distribution
    segment_levels, total_length = analyze_volume_distribution(input_file)
    display_audio_statistics(segment_levels, total_length)
    
    # 2. Generate threshold candidates
    candidates = generate_threshold_candidates(segment_levels)
    
    # 3. Test candidates on sample
    results = test_and_display_candidates(input_file, candidates)
    
    if not results:
        print("All threshold tests failed. Using default -25dB")
        return -25
    
    # 4. Let user choose
    chosen_threshold = get_user_threshold_choice(results, candidates)
    
    print(f"\nSelected threshold: {chosen_threshold}dB")
    return chosen_threshold

def main():
    parser = argparse.ArgumentParser(description='Intelligently trim silence from audio files using optimal threshold detection.')
    parser.add_argument('--min-silence', '-m', type=float, default=2.0, help='Minimum length of silence in seconds')
    parser.add_argument('--threshold', '-t', type=int, help='Silence threshold in dB (if not provided, smart selection is used)')
    parser.add_argument('--auto', '-a', action='store_true', help='Automatically select best threshold without user interaction')
    parser.add_argument('input_file', help='Input audio file')
    parser.add_argument('output_file', help='Output audio file')

    args = parser.parse_args()

    # Check if the input file exists
    if not os.path.isfile(args.input_file):
        print(f'Error: Input file "{args.input_file}" does not exist.')
        return

    # Check if the output directory exists, if not create it
    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Determine threshold
    if args.threshold is not None:
        # Use provided threshold
        threshold = args.threshold
        print(f"Using provided threshold: {threshold}dB")
    elif args.auto:
        # Auto-select best threshold
        segment_levels, _ = analyze_volume_distribution(args.input_file)
        candidates = generate_threshold_candidates(segment_levels)
        results = test_and_display_candidates(args.input_file, candidates)
        
        if results:
            # Select threshold with reduction closest to 40%
            best_result = min(results, key=lambda x: abs(x[1] - 40))
            threshold = best_result[0]
            print(f"Auto-selected threshold: {threshold}dB ({best_result[1]:.1f}% reduction)")
        else:
            threshold = -25
            print("Auto-selection failed. Using default -25dB")
    else:
        # Interactive threshold selection
        threshold = smart_threshold_selection(args.input_file)

    # Process the audio
    print(f"\nProcessing with threshold: {threshold}dB")
    trim_with_ffmpeg(args.input_file, args.output_file, args.min_silence, threshold)
    print(f"\nOutput saved to: {args.output_file}")

if __name__ == '__main__':
    main()
