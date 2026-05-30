# Troubleshooting Guide

# VAClip Troubleshooting Guide

This guide helps diagnose and resolve common issues encountered when installing, configuring, and running VAClip.

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [GPU/CUDA Issues](#gpu-cuda-issues)
3. [FFmpeg Issues](#ffmpeg-issues)
4. [Ingest Issues](#ingest-issues)
5. [Transcription Issues](#transcription-issues)
6. [Scoring Issues](#scoring-issues)
7. [Export Issues](#export-issues)
8. [Pipeline Issues](#pipeline-issues)
9. [CLI Issues](#cli-issues)
10. [Testing Issues](#testing-issues)
11. [Performance Optimization](#performance-optimization)

---

## Installation Issues

### Problem: "externally-managed-environment" error when installing with pip
**Solution:** Use a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .[dev]
```

### Problem: Missing dependencies after installation
**Solution:** Verify installation and reinstall if needed:
```bash
pip list | grep vaclip
# If not showing, reinstall:
pip install -e .[dev]
```

### Problem: ImportError when trying to import vaclip
**Solution:** Ensure you're in the correct environment and the package is installed:
```bash
# Check Python path
python -c "import sys; print('\\n'.join(sys.path))"
# Check if vaclip is installed
python -c "import vaclip; print(vaclip.__version__)"
```

---

## GPU/CUDA Issues

### Problem: CUDA not available or torch.cuda.is_available() returns False
**Solutions:**
1. Verify NVIDIA drivers are installed:
   ```bash
   nvidia-smi
   ```
2. Check CUDA toolkit installation:
   ```bash
   nvcc --version
   ```
3. Reinstall PyTorch with CUDA support:
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```
4. For older GPUs, try:
   ```bash
   pip install torch==2.0.1+cu117 torchvision==0.15.2+cu117 torchaudio==2.0.1 --index-url https://download.pytorch.org/whl/cu117
   ```

### Problem: Out of GPU memory (CUDA out of memory)
**Solutions:**
1. Reduce batch size or model size in settings:
   ```yaml
   transcription:
     model_size: base  # instead of large-v3
     compute_type: int8  # instead of float16
   ```
2. Enable CPU fallback:
   ```yaml
   transcription:
     device: cpu
   ```
3. Clear GPU cache between runs:
   ```python
   import torch
   torch.cuda.empty_cache()
   ```

### Problem: Invalid device specification
**Solution:** Valid options are `cuda`, `cpu`, or `auto`:
```yaml
transcription:
  device: auto  # Let PyTorch decide
```

---

## FFmpeg Issues

### Problem: "FFmpeg not found" or "FFmpeg failed"
**Solutions:**
1. Verify FFmpeg is installed and in PATH:
   ```bash
   ffmpeg -version
   ```
2. Install FFmpeg:
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: Download from https://ffmpeg.org/download.html
3. Verify NVENC support (for GPU encoding):
   ```bash
   ffmpeg -hide_banner -loglevel info -encoders | grep nvenc
   ```
4. If using conda, install from conda-forge:
   ```bash
   conda install -c conda-forge ffmpeg
   ```

### Problem: "Invalid argument" or "Unknown encoder" errors
**Solutions:**
1. Check FFmpeg version (need recent version for NVENC):
   ```bash
   ffmpeg -version
   # Should be 4.0+ for basic NVENC, 11.0+ for better support
   ```
2. Try software encoding as fallback:
   ```yaml
   export:
     video_encoder: libx264  # instead of h264_nvenc
   ```

### Problem: Permission denied when accessing files
**Solutions:**
1. Check file permissions:
   ```bash
   ls -l /path/to/file
   ```
2. Ensure VAClip has read/write access to:
   - Input directory (for source media)
   - Output directory (for exported clips)
   - Cache directory (for intermediate artifacts)
   - Logs directory (for log files)

---

## Ingest Issues

### Problem: "UnsupportedSourceError" for valid files
**Solutions:**
1. Check file extension against supported formats:
   ```python
   # In src/vaclip/ingest/local_adapter.py
   SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv"}
   SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
   ```
2. For URL ingest, verify yt-dlp can handle the URL:
   ```bash
   yt-dlp --extract-flat --print-json "URL_HERE"
   ```

### Problem: yt-dlp extraction fails
**Solutions:**
1. Update yt-dlp:
   ```bash
   pip install -U yt-dlp
   ```
2. Try with cookies if needed:
   ```bash
   yt-dlp --cookies /path/to/cookies.txt "URL_HERE"
   ```
3. For YouTube, try adding `--verbose` to see detailed error:
   ```bash
   yt-dlp --verbose "URL_HERE"
   ```

### Problem: FFmpeg fails during metadata extraction or audio extraction
**Solutions:**
1. Test FFmpeg command manually:
   ```bash
   # Metadata extraction
   ffprobe -v quiet -print_format json -show_streams -show_format "input.mp4"
   
   # Audio extraction
   ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav
   ```
2. Check if file is corrupted or uses unsupported codecs
3. Try converting to a standard format first:
   ```bash
   ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4
   ```

---

## Transcription Issues

### Problem: Transcription returns empty results or very poor quality
**Solutions:**
1. Check audio quality and format:
   - Should be 16kHz mono WAV for best results
   - Use `ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav` to convert
2. Try different model sizes:
   ```yaml
   transcription:
     model_size: tiny  # fastest, least accurate
     # or
     model_size: base  # good balance
     # or
     model_size: small  # better accuracy
     # or
     model_size: medium  # better still
     # or
     model_size: large-v2  # best quality (requires more VRAM)
     # or
     model_size: large-v3  # latest best quality
   ```
3. Adjust VAD (Voice Activity Detection) settings:
   ```yaml
   transcription:
     vad_filter: true
     vad_parameters:
       min_silence_duration_ms: 500  # increase if cutting off speech
       # speech_pad_ms: 400  # add padding around speech
   ```
4. Disable word timestamps if not needed (faster):
   ```yaml
   transcription:
     word_timestamps: false
   ```

### Problem: Slow transcription performance
**Solutions:**
1. Ensure GPU is being used:
   ```yaml
   transcription:
     device: cuda
     compute_type: float16
   ```
2. Reduce beam size:
   ```yaml
   transcription:
     beam_size: 3  # instead of 5
     best_of: 3    # instead of 5
   ```
3. Use faster model:
   ```yaml
   transcription:
     model_size: tiny
     compute_type: int8
   ```

### Problem: "CUDA out of memory" during transcription
**Solutions:**
1. Use smaller model:
   ```yaml
   transcription:
     model_size: tiny
   ```
2. Use int8 compute type:
   ```yaml
   transcription:
     compute_type: int8
   ```
3. Process audio in chunks (if implementing custom transcription)
4. Offload to CPU:
   ```yaml
   transcription:
     device: cpu
   ```

---

## Scoring Issues

### Problem: No segments scored above threshold
**Solutions:**
1. Lower the minimum score threshold:
   ```yaml
   scoring:
     min_score: 0.1  # instead of 0.3
   ```
2. Check transcript quality - if transcription failed, scoring will fail
3. Verify that signal generators are working:
   - Test individual signal components
   - Check that transcript text is being processed correctly
4. Adjust profile weights:
   ```yaml
   # In src/vaclip/scoring/profiles.py or similar
   PODCAST = {
     "transcript": 1.0,
     "audio": 0.5,
     "keyword": 0.3,
     "sentiment": 0.2
   }
   ```

### Problem: Too many false positive segments
**Solutions:**
1. Increase minimum score threshold:
   ```yaml
   scoring:
     min_score: 0.5
   ```
2. Increase minimum segment duration:
   ```yaml
   scoring:
     min_segment_duration: 8.0  # instead of 5.0
   ```
3. Apply post-processing filters:
   - Remove segments that are too short
   - Remove segments with low confidence scores
   - Apply NMS (Non-Maximum Suppression) to remove overlapping segments

### Problem: Scoring is very slow
**Solutions:**
1. Disable embeddings if not needed:
   ```yaml
   scoring:
     use_embeddings: false
   ```
2. Reduce top_k (number of candidates to keep):
   ```yaml
   scoring:
     top_k: 10  # instead of 20
   ```
3. Use simpler models for embedding:
   ```yaml
   scoring:
     embedding_model: all-MiniLM-L6-v2  # instead of all-mpnet-base-v2
   ```

---

## Export Issues

### Problem: Exported clips are corrupted or won't play
**Solutions:**
1. Verify FFmpeg command is correct:
   - Test with a known good command:
     ```bash
     ffmpeg -i input.mp4 -ss 0 -t 5 -c:v libx264 -c:a aac output.mp4
     ```
2. Check that start/end times are valid:
   - Start >= 0
   - End <= media duration
   - Start < End
3. Try different encoding parameters:
   ```yaml
   export:
     video_encoder: libx264
     video_preset: veryfast  # faster encoding
     video_crf: 23  # higher = lower quality but faster
   ```
4. Check disk space and permissions in output directory

### Problem: Export is very slow
**Solutions:**
1. Use faster preset:
   ```yaml
   export:
     video_preset: ultrafast  # fastest, lower quality
     # or
     video_preset: superfast
     # or
     video_preset: veryfast
   ```
2. Use hardware encoding if available:
   ```yaml
   export:
     video_encoder: h264_nvenc  # if you have NVIDIA GPU with NVENC
     nvenc_preset: p1  # p1=p7 (fastest to slowest)
   ```
3. Reduce CRF for faster encoding (lower quality):
   ```yaml
   export:
     video_crf: 28  # instead of 18
   ```

### Problem: "No such file or directory" for output path
**Solutions:**
1. Ensure output directory exists and is writable:
   ```bash
   mkdir -p /path/to/output
   chmod u+w /path/to/output
   ```
2. Check that the filename template doesn't contain invalid characters
3. Verify that the run_id is being generated correctly

---

## Pipeline Issues

### Problem: Pipeline fails at a specific stage
**Solutions:**
1. Check logs for specific error messages
2. Test that stage in isolation:
   - Ingest: Test with a known good file/URL
   - Transcription: Test with a known good audio file
   - Scoring: Test with a known good transcript
   - Export: Test with known good media and segments
3. Verify checkpoint/resume is working correctly:
   ```bash
   # Try running with --from-stage to skip problematic stages
   vaclip run --source video.mp4 --from-stage scoring
   ```

### Problem: Checkpoint/resume not working
**Solutions:**
1. Check that artifact directories exist and are writable
2. Verify that settings.artifacts.overwrite is set correctly:
   ```yaml
   artifacts:
     overwrite: false  # true to re-run stages, false to resume
   ```
3. Check that artifact files are being saved correctly:
   - `cache/<asset_id>/media_asset.json`
   - `cache/<run_id>/transcript.json`
   - `cache/<run_id>/scores_<profile>.json`
   - `cache/<run_id>/exported_clips.json`

### Problem: Pipeline runs but produces no output
**Solutions:**
1. Check logs to see which stages ran
2. Verify that each stage is producing expected output:
   - Ingest: MediaAsset created
   - Transcription: Transcript with words
   - Scoring: ScoredSegments with scores > min_score
   - Export: ExportedClip objects
3. Check filtering criteria:
   - Are segments being filtered out by duration?
   - Are scores below min_score?
   - Is max_clips set to 0?

---

## CLI Issues

### Problem: Command not found: vaclip
**Solutions:**
1. Ensure package is installed:
   ```bash
   pip install -e .
   ```
2. Check that the scripts entry point is working:
   ```bash
   which vaclip
   # or
   vaclip --help
   ```
3. If using virtual environment, ensure it's activated:
   ```bash
   source .venv/bin/activate
   ```

### Problem: CLI commands show NotImplementedError
**Solution:** This indicates the underlying functionality hasn't been implemented yet.
Check the status of:
- M-26: Implement ClipperPipeline
- M-29: Implement `clip` Typer CLI command
- Other phase tasks in docs/tasks.md

### Problem: Rich formatting not working correctly
**Solutions:**
1. Ensure rich is installed:
   ```bash
   pip install rich
   ```
2. Try disabling rich markup:
   ```bash
   vaclip --help  # should work without colors
   ```
3. Check terminal compatibility with ANSI colors

---

## Testing Issues

### Problem: Tests fail due to missing fixtures
**Solutions:**
1. Ensure test fixtures are created:
   ```bash
   ls tests/fixtures/
   # Should contain sample_podcast.mp3, sample_video.mp4, etc.
   ```
2. Run the fixture creation script if needed
3. For media files, they can be generated with:
   ```bash
   # 30 seconds of silent audio
   ffmpeg -f lavfi -i aevalsrc=0:duration=30 -c:a libmp3lame -b:a 64k tests/fixtures/sample_podcast.mp3
   
   # 10 seconds of black video
   ffmpeg -f lavfi -i color=c=black:s=640x360:d=10 -f lavfi -i anullsrc=r=44100:cl=mono -c:v libx264 -c:a aac -shortest tests/fixtures/sample_video.mp4
   ```

### Problem: Tests are too slow
**Solutions:**
1. Use unit tests instead of integration tests for development:
   ```bash
   pytest -m "unit"
   ```
2. Skip integration tests:
   ```bash
   pytest -m "not integration"
   ```
3. Use smaller/faster test fixtures
4. Mock external dependencies more aggressively

### Problem: Coverage reporting shows low coverage
**Solutions:**
1. Run tests with coverage:
   ```bash
   pytest --cov=src/vaclip --cov-report=term-missing
   ```
2. Focus on testing modules with lowest coverage
3. Ensure tests are actually executing the code paths
4. Remove dead code or unused branches

---

## Performance Optimization

### General Optimization Strategies

1. **Batch Processing**: Process multiple files in parallel when possible
2. **Caching**: Leverage existing caching mechanisms:
   - Transcript caching (avoid re-transcription)
   - Media asset caching (avoid re-ingesting)
   - Score caching (avoid re-scoring)
3. **Hardware Acceleration**:
   - Use GPU for transcription (faster-whisper)
   - Use GPU for export (h264_nvenc) if available
   - Consider GPU for embeddings if using sentence-transformers with GPU support
4. **Model Optimization**:
   - Use smaller models when accuracy permits
   - Use quantized models (int8, float16)
   - Prune or distill models for specific use cases

### Specific Component Optimizations

#### Ingest:
- Parallelize downloads of multiple files
- Use yt-dlp's concurrent fragment downloading
- Cache frequently accessed media metadata

#### Transcription:
- Use faster-whisper's VAD to skip silent sections
- Process audio in chunks for very long files
- Cache transcriptions by audio file hash

#### Segmentation/Scoring:
- Process segments in batches for embedding models
- Use approximate nearest neighbor search for large embedding databases
- Precompute and cache embeddings for static content

#### Export:
- Use hardware encoding (NVENC) when available
- Use two-pass encoding for better quality/size ratio
- Export to temporary directory then move to final location

### Monitoring and Profiling

1. **Enable detailed logging**:
   ```yaml
   logging:
     level: DEBUG
   ```
2. **Use Python profiling tools**:
   ```bash
   python -m cProfile -s cumulative vaclip run --source video.mp4
   ```
3. **Monitor GPU utilization**:
   ```bash
   nvidia-smi dmon -s u  # utilization metrics
   nvidia-smi pmon -s uc  # process metrics
   ```
4. **Track end-to-end latency**:
   - Measure time from ingest start to export complete
   - Identify bottlenecks in each stage

---

## Getting Further Help

If you've checked this guide and still encounter issues:

1. **Check the GitHub Issues**:
   - Search existing issues: https://github.com/cbwinslow/clipper/issues
   - Look for similar error messages or symptoms
   - Check if there are open pull requests with fixes

2. **Enable Debug Logging**:
   - Run with `--verbose` flag or set `VACLIP_LOG_LEVEL=DEBUG`
   - Examine logs for stack traces and context

3. **Create a Minimal Reproducible Example**:
   - Reduce the problem to the simplest case that still reproduces the issue
   - Note the exact command and parameters used
   - Record the exact environment (OS, Python version, GPU info)

4. **Ask for Help**:
   - GitHub Discussions: https://github.com/cbwinslow/clipper/discussions
   - Provide:
     - VAClip version (from `vaclip --version`)
     - Detailed steps to reproduce
     - Full error logs and stack traces
     - Environment details (OS, Python, GPU, FFmpeg version)
     - What you've already tried

Remember: When reporting issues, please include as much relevant context as possible to help maintainers diagnose and fix the problem quickly.