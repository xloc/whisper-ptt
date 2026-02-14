# whisper-ptt

Push-to-talk speech-to-text. Hold a key to record, release to transcribe and type.

## Usage

```
uvx whisper-ptt
uvx whisper-ptt --model base --key alt_r
```

## Options

- `--model` — Whisper model. Default: `base`. Common choices: `tiny`, `base`, `small`, `medium`, `large-v3-turbo`. 
    - Run `uvx whisper-ptt --help` for full list.
- `--key` — Hotkey name from `pynput.keyboard.Key`. Default: `alt_r`

## macOS permissions

This tool needs two macOS permissions to work:

- **Accessibility** — to listen for hotkey presses and type transcribed text into the active window.
- **Microphone** — to record audio.

To grant accessibility access:

1. Open System Settings > Privacy & Security > Accessibility
2. Click the + button and add your terminal app (Terminal, iTerm2, VS Code, etc.)
3. If already listed, toggle it off and back on

Microphone access is prompted automatically on first use.

## Release

```bash
git tag v1.0.x
git push --tags
```

CI runs tests and publishes to PyPI automatically.
