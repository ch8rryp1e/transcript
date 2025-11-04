# transcript

## Audio/Video Transcriber

Desktop application for automatic transcription of audio and video files using OpenAI Whisper model.

## Features

- Support for multiple audio formats (MP3, WAV, M4A, FLAC, OGG)
- Support for video formats (MP4, AVI, MOV, MKV, FLV, WMV, WebM)
- Automatic audio extraction from video
- Batch processing of multiple files
- Parallel processing (up to 2 files simultaneously)
- Multiple Whisper models (tiny, base, small, medium, large)
- Support for 20+ languages
- Automatic language detection
- Translation to Russian 
- Recursive folder search
- Real-time progress tracking
- Graphical user interface


## Usage

1. Select Whisper model (tiny/base/small/medium/large)
2. Choose language or use auto-detection
3. Add files or folders
4. Click "Start Transcription"
5. Save results when complete

Transcriptions are saved in the same directory as the original files with `_transcription.txt` suffix.

## Whisper Models

| Model  | Size    | Memory | Speed | Accuracy |
|--------|---------|--------|-------|----------|
| tiny   | ~39MB   | ~1GB   | ~32x  | Low      |
| base   | ~74MB   | ~1GB   | ~16x  | Medium   |
| small  | ~244MB  | ~2GB   | ~6x   | Good     |
| medium | ~769MB  | ~5GB   | ~2x   | High     |
| large  | ~1550MB | ~10GB  | ~1x   | Highest  |

## Supported Languages

auto, en, es, fr, de, ru

## Supported Formats

**Audio:** MP3, WAV, M4A, FLAC, OGG  
**Video:** MP4, AVI, MOV, MKV, FLV, WMV, WebM, M4V


## Technical Details

### Architecture
- Main GUI thread manages interface
- Worker thread handles model loading and coordination
- ThreadPoolExecutor processes files in parallel (max 2 workers)

### Processing Flow
1. Load Whisper model
2. Extract audio from video if needed (creates temporary WAV)
3. Transcribe via Whisper
4. Save result
5. Clean up temporary files
6. Update GUI via Qt signals


## Credits

- OpenAI Whisper - Transcription model
- PyQt6 - GUI framework
- MoviePy - Video processing
- FFmpeg - Media conversion