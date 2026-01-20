# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

@README.md

- Audio-related logic (combining, tagging, TTS helpers, etc.) must live in the upstream `speech-audio-tools` package. When you see audio logic being added or modified locally, propose moving it into `speech-audio-tools` instead and wire this repo to use it.
