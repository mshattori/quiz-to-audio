# Quiz to audio

Read Q&A quizes separated by " := " and convert them to audio file by Amazon Polly.

## Preperation

ffmpeg is required to use pydub:

```
brew install curl
brew install ffmpeg
```

... brew-installed curl is required to install dependencies of ffmpeg.

pip install:
- pydub
- mutagen
- boto3

```
Usage: quiz2audio.py quiz-filename output-directory
```

NOTE: Use an aws region that supports neural TTS (e.g. us-east-1)
Ref. <https://docs.aws.amazon.com/polly/latest/dg/NTTS-main.html>

## Utilities
- join.py ... Join specified audio files.
- split.py ... Split an audio file by silences.
- trim.py ... Trim either or both ends of an audio file.
- add_album_title.py ... Sets the 'title' (from filename) and 'album' ID3 tags for audio files in a directory.
- addnumber.py ... Add index number audios to audio files.# CLAUDE.md

## Commands

### Core Development Commands
- `python quiz2audio.py <quiz-file> <output-dir>` - Main script to convert Q&A quiz files to audio
- `python tts.py speakers --lang <lang>` - List available TTS speakers for a language
- `python tts.py synthesize --lang <lang> -i <input-file> -o <output-file>` - Synthesize speech from text
- `python tts.py calc-cost <input-file>` - Calculate TTS cost for a quiz file

### Audio Processing Commands
- `python trim_silence.py <input-file> <output-file>` - Intelligently trim silence from audio
- `python split.py <input-file> <output-dir>` - Split audio by detecting silence
- `python join.py <file1> <file2> ... -o <output-file>` - Join multiple audio files
- `python trim.py <input-file> <output-file>` - Trim audio file ends
- `python addnumber.py <input-dir> <output-dir>` - Add index numbers to audio files

### Package Management
- `uv sync` - Install dependencies using uv
- `uv run python <script.py>` - Run Python scripts with uv

## Architecture

### Core Components

**quiz2audio.py** - Main entry point that orchestrates the entire quiz-to-audio conversion process:
- Parses command-line arguments for language, speed, voice engine selection
- Coordinates between TTS generation and audio processing modules
- Supports multiple TTS engines (Amazon Polly, OpenAI) and language combinations

**tts.py** - Text-to-Speech engine abstraction and quiz processing:
- `QuizTTS` class handles quiz file parsing and TTS generation
- `AmazonPollyEngine` and `OpenAISpeechEngine` provide TTS implementations
- `SimpleTTS` for single text-to-speech conversion
- Quiz format: questions and answers separated by " := "
- Supports voice randomization and speaker groups

**audio.py** - Audio processing and section creation:
- `make_section_mp3_files()` combines Q&A pairs into sectioned MP3 files
- Speed modification, gain adjustment, and metadata tagging
- File signature tracking to avoid regenerating unchanged audio
- Section-based organization (default 10 Q&A pairs per section)

**trim_silence.py** - Intelligent silence removal:
- Volume analysis and threshold detection
- Interactive threshold selection with preview
- FFmpeg-based processing for performance
- Smart threshold recommendations based on audio statistics

### Data Flow
1. Quiz file (text) → TTS generation (raw audio files)
2. Raw audio files → Audio processing (combined sections)
3. Optional: Silence trimming, joining, or splitting

### Configuration
- Environment variables loaded from `.env` file
- AWS credentials required for Amazon Polly
- OpenAI API key required for OpenAI TTS
- Language codes: 'en-US', 'ja-JP' (English-Japanese combinations supported)

### File Structure
- Raw audio files stored in `.raw_<dirname>` directories
- Output files organized by sections (001-010.mp3, 011-020.mp3, etc.)
- Metadata files: `.quiz_audio_dict.json`, `.signatures.json`
- Temporary number audio files in `.number_audio/`

### TTS Engines
- **Amazon Polly**: Supports neural, standard, long-form, and generative engines
- **OpenAI**: Supports tts-1 and tts-1-hd models
- Engine selection via `--engine` parameter (e.g., 'neural', 'openai-tts-1')

### Audio Processing Features
- Speed control (separate for questions and answers)
- Gain adjustment
- Silence trimming with smart threshold detection
- Audio joining with optional silence insertion
- Section-based MP3 generation with ID3 tags