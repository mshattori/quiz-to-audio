# Quiz to audio

Read Q&A quizes separated by " := " and convert them to audio file by Amazon Polly.

Preperation:

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

Use an aws region that supports neural TTS (e.g. us-east-1)
Ref. <https://docs.aws.amazon.com/polly/latest/dg/NTTS-main.html>
