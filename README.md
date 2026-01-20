# quiz-to-audio

Convert quiz text (`Q := A` format) to audio with TTS and bundle the Q/A pairs into section MP3s. Audio processing and TTS engines are provided by the external package `speech-audio-tools`.

## Installation
```bash
uv sync
```

## Usage
```bash
uv run quiz2audio quizzes.txt output_dir \
  --lang-QA EJ \
  --speed-QA 1.0:0.9 \
  --engine neural:neural \
  --repeat-question
```

### All options
- `--env-file, -e`: Path to `.env` (default `.env`).
- `--lang-QA`: `EE` (English-English), `EJ` (English -> Japanese), `JE` (Japanese -> English).
- `--speed-QA`: Speech speed; `1.0` or `Q:A` (e.g., `1.0:0.9`).
- `--invert-QA`: Swap Q and A before generation.
- `--gain`: Gain (dB) applied when combining sections.
- `--engine`: Engine (`neural`, `standard`, `openai-tts-1`, etc.). Use `dummy` to generate silent audio for tests.
- `--repeat-question`: Read the Question twice in output.
- `--pause-duration`: Pause between Q/A (ms).
- `--add-number-audio`: Prepend spoken numbers to each QA.
- `--split-by-comma`: Split comma-separated synonyms when speaking.
- `--section-unit`: Number of QAs per section MP3 (default 10).
- `--single-file`: Combine all QAs into one MP3; title uses input filename stem. Mutually exclusive with `--section-unit` when set explicitly.
- `--album`: Override album metadata (default derives from output directory name).
- `quiz_filename`: Input quiz file (`Q := A` lines).
- `output_directory`: Destination for section MP3s.

### Outputs
- `.raw_<output_dir_name>/`: Individual MP3s for each Q/A.
- `output_dir/`: Section MP3s (e.g., `001-010.mp3`).

### Metadata
The section MP3s include ID3 tags:
- **Title**: `{start_number}-{end_number} {Album}` (or quiz filename stem for `--single-file`).
- **Album**: Derived from the output directory name (Title Cased, underscores/hyphens replaced with spaces) unless overridden with `--album`.
- **Artist**: `Homebrew`.

## Environment
- Put AWS (Polly) / OpenAI keys in `.env`.
- For offline testing, use `--engine dummy` to avoid external APIs.

## Development & Testing
- Entry point `quiz2audio` is declared in `[project.scripts]`; run via `uv run quiz2audio ...`.
- E2E (dummy engine):
  ```bash
  uv run pytest tests/test_quiz2audio_e2e.py -q
  ```
  The test generates silent MP3s and checks that section files are produced.

## Architecture
- `quiz_to_audio.quiz_parser`: Quiz file parser (importable).
- `quiz_to_audio.quiz_tts`: QuizTTS using `speech_audio_tools.tts.init_tts_engine` plus a built-in `dummy` engine.
- `quiz_to_audio.cli`: CLI that calls `speech_audio_tools.audio.make_section_mp3_files` after TTS.
- `quiz2audio.py`: Thin wrapper around the CLI.

## Migration notes
- Legacy audio/TTS scripts are removed here; functionality lives in `speech-audio-tools`.
- `speech-audio-tools` is pulled via Git (ssh) as a dependency.
