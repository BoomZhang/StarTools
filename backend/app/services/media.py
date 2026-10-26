"""音视频与语音 P1：ffmpeg 转码、Whisper 语音识别与系统 TTS。"""

import json
import os
import re
import shutil
import subprocess
import threading
import wave
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.services.common import safe_stem, timestamp_label
from app.services.types import FileResult, ProcessOutcome, TaskError, TextResult

os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

VIDEO_TYPES = {
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mov": "video/quicktime",
    "mkv": "video/x-matroska",
    "avi": "video/x-msvideo",
    "flv": "video/x-flv",
    "m4v": "video/x-m4v",
    "wmv": "video/x-ms-wmv",
    "ts": "video/mp2t",
}
AUDIO_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "opus": "audio/ogg",
    "wma": "audio/x-ms-wma",
    "aiff": "audio/aiff",
}
AUDIO_BITRATES = {"64k", "96k", "128k", "192k", "256k", "320k"}
VIDEO_PRESETS = {
    "ultrafast", "superfast", "veryfast", "faster", "fast",
    "medium", "slow", "slower", "veryslow",
}


def _audio_codec(target_format: str, bitrate: str) -> list[str]:
    if target_format == "mp3":
        return ["-c:a", "libmp3lame", "-b:a", bitrate]
    if target_format == "wav":
        return ["-c:a", "pcm_s16le"]
    if target_format in {"m4a", "aac"}:
        return ["-c:a", "aac", "-b:a", bitrate]
    if target_format == "flac":
        return ["-c:a", "flac"]
    if target_format == "ogg":
        return ["-c:a", "libvorbis", "-b:a", bitrate]
    if target_format == "opus":
        return ["-c:a", "libopus", "-b:a", bitrate]
    if target_format == "wma":
        return ["-c:a", "wmav2", "-b:a", bitrate]
    if target_format == "aiff":
        return ["-c:a", "pcm_s16be"]
    raise TaskError("E1-400", "不支持的目标音频格式")

_WHISPER_LOCK = threading.Lock()
_WHISPER_MODELS: dict[str, object] = {}
_VOICE_CACHE: dict[str, str | None] = {}


def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def speech_available() -> bool:
    if not ffmpeg_available():
        return False
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False
    return True


def tts_available() -> bool:
    return any(shutil.which(name) for name in ("say", "espeak-ng", "espeak"))


def _run_ffmpeg(args: list[str], timeout: int = 300) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise TaskError("E4-504", "音视频处理超时，请缩短时长或降低参数后重试", 504) from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        message = detail[-1][:160] if detail else "未知原因"
        raise TaskError("E3-422", f"音视频处理失败：{message}")


def _probe(path: Path) -> dict:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise TaskError("E4-503", "ffmpeg/ffprobe 不可用", 503) from exc
    if result.returncode != 0:
        raise TaskError("E1-400", "媒体文件无法读取，可能已损坏或格式不支持")
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise TaskError("E1-400", "媒体信息解析失败") from exc


def _duration(probe: dict) -> float:
    try:
        return float(probe.get("format", {}).get("duration") or 0)
    except (TypeError, ValueError):
        return 0.0


def _has_stream(probe: dict, kind: str) -> bool:
    return any(stream.get("codec_type") == kind for stream in probe.get("streams", []))


def _file_result(target: Path, content_type: str, meta: dict, notes: list[str], outcome: ProcessOutcome) -> None:
    outcome.results.append(
        FileResult(filename=target.name, path=target, content_type=content_type, meta=meta)
    )
    outcome.notes.extend(notes)


def process_audio_convert(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    path = files[0]
    name = names[0]
    target_format = str(params.get("format", "mp3")).lower()
    if target_format not in AUDIO_TYPES:
        raise TaskError("E1-400", "不支持的目标音频格式")
    bitrate = str(params.get("bitrate", "192k"))
    if bitrate not in {"128k", "192k", "256k", "320k"}:
        bitrate = "192k"

    probe = _probe(path)
    duration = _duration(probe)
    if duration <= 0:
        raise TaskError("E1-400", "音频时长为 0，无法处理")
    if duration > 3600:
        raise TaskError("E2-413", f"音频 {duration / 60:.0f} 分钟，上限 60 分钟", 413)

    target = workdir / f"{safe_stem(name)}.{target_format}"
    codec = _audio_codec(target_format, bitrate)
    _run_ffmpeg(["-i", str(path), "-vn", *codec, str(target)], timeout=max(120, int(duration * 3)))

    outcome = ProcessOutcome()
    _file_result(
        target,
        AUDIO_TYPES[target_format],
        {"format": target_format, "duration": round(duration, 1), "original_size": path.stat().st_size, "new_size": target.stat().st_size},
        ["仅转换编码，不改变音轨内容。"],
        outcome,
    )
    return outcome


def process_video_to_gif(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    path = files[0]
    name = names[0]
    probe = _probe(path)
    if not _has_stream(probe, "video"):
        raise TaskError("E1-400", "文件中没有视频轨")
    duration = _duration(probe)
    if duration <= 0:
        raise TaskError("E1-400", "视频时长为 0，无法处理")

    start = max(0.0, float(params.get("start", 0) or 0))
    end = float(params.get("end", min(duration, start + 5)) or 0)
    if end <= start or start >= duration or end > duration + 0.2:
        raise TaskError("E1-400", f"起止时间需落在 0–{duration:.1f} 秒内")
    if end - start > 15:
        raise TaskError("E2-413", "单个 GIF 片段不能超过 15 秒", 413)

    width = int(params.get("width", 480) or 480)
    if width not in {320, 480, 640, 800}:
        width = 480
    fps = int(params.get("fps", 12) or 12)
    if fps not in {10, 15, 24}:
        fps = 12

    target = workdir / f"{safe_stem(name)}_{timestamp_label()}.gif"
    filter_chain = (
        f"fps={fps},scale={width}:-1:flags=lanczos,"
        "split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer"
    )
    _run_ffmpeg(
        [
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{end - start:.3f}",
            "-i",
            str(path),
            "-vf",
            filter_chain,
            "-loop",
            "0",
            str(target),
        ],
        timeout=300,
    )
    outcome = ProcessOutcome()
    _file_result(
        target,
        "image/gif",
        {
            "start": start,
            "end": end,
            "width": width,
            "fps": fps,
            "duration": round(end - start, 2),
            "new_size": target.stat().st_size,
        },
        ["GIF 使用调色板压缩；颜色较多时可能出现色带。"],
        outcome,
    )
    return outcome


def process_video_compress(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    path = files[0]
    name = names[0]
    probe = _probe(path)
    if not _has_stream(probe, "video"):
        raise TaskError("E1-400", "文件中没有视频轨")
    duration = _duration(probe)
    if duration > 1800:
        raise TaskError("E2-413", "视频超过 30 分钟上限", 413)

    level = str(params.get("level", "balanced"))
    presets = {
        "light": {"crf": 28, "width": 1280},
        "balanced": {"crf": 23, "width": 1920},
        "max": {"crf": 18, "width": 1920},
    }
    base = presets.get(level, presets["balanced"])

    try:
        start = max(0.0, float(params.get("trim_start", 0) or 0))
        end_param = params.get("trim_end")
        end = float(end_param) if end_param not in (None, "") else duration
    except (TypeError, ValueError) as exc:
        raise TaskError("E1-400", "裁剪起止时间参数不合法") from exc
    if start >= duration or end <= start:
        raise TaskError("E1-400", "裁剪起止时间不合法")
    if end > duration + 0.2:
        end = duration
    clip_duration = end - start

    def int_param(key: str, default: int, low: int, high: int) -> int:
        value = params.get(key)
        if value in (None, ""):
            return default
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise TaskError("E1-400", f"{key} 参数不合法") from exc
        if not low <= number <= high:
            raise TaskError("E1-400", f"{key} 需在 {low}–{high} 之间")
        return number

    codec = str(params.get("codec", "h264")).lower()
    if codec not in {"h264", "h265"}:
        codec = "h264"
    rate_mode = str(params.get("rate_mode", "crf")).lower()
    if rate_mode not in {"crf", "bitrate"}:
        rate_mode = "crf"
    crf = int_param("crf", base["crf"], 0, 51)
    preset = str(params.get("preset", "medium"))
    if preset not in VIDEO_PRESETS:
        preset = "medium"
    width = int_param("width", base["width"], 128, 7680)
    fps = int_param("fps", 0, 0, 120)
    audio_mode = str(params.get("audio", "aac")).lower()
    if audio_mode not in {"aac", "mp3", "copy", "none"}:
        audio_mode = "aac"
    audio_bitrate = str(params.get("audio_bitrate", "128k"))
    if audio_bitrate not in AUDIO_BITRATES:
        audio_bitrate = "128k"
    channels = str(params.get("audio_channels", "keep"))
    if channels not in {"keep", "1", "2"}:
        channels = "keep"
    sample_rate = str(params.get("audio_sample_rate", "keep"))
    if sample_rate not in {"keep", "22050", "44100", "48000"}:
        sample_rate = "keep"
    faststart = str(params.get("faststart", "true")) != "false"

    args: list[str] = []
    if start > 0:
        args += ["-ss", f"{start:.3f}"]
    args += ["-t", f"{clip_duration:.3f}", "-i", str(path), "-map", "0:v:0"]

    video_codec = "libx264" if codec == "h264" else "libx265"
    args += ["-c:v", video_codec, "-preset", preset, "-pix_fmt", "yuv420p"]
    if rate_mode == "bitrate":
        try:
            mbps = float(params.get("video_bitrate", 2) or 2)
        except (TypeError, ValueError) as exc:
            raise TaskError("E1-400", "视频码率参数不合法") from exc
        if not 0.1 <= mbps <= 100:
            raise TaskError("E1-400", "视频码率需在 0.1–100 Mbps 之间")
        args += ["-b:v", f"{mbps:g}M"]
    else:
        args += ["-crf", str(crf)]

    filters = [f"scale=w='min(iw,{width})':h=-2"]
    if fps:
        filters.append(f"fps={fps}")
    args += ["-vf", ",".join(filters)]

    if audio_mode == "none":
        args += ["-an"]
    else:
        args += ["-map", "0:a?"]
        if audio_mode == "copy":
            args += ["-c:a", "copy"]
        else:
            args += ["-c:a", "aac" if audio_mode == "aac" else "libmp3lame", "-b:a", audio_bitrate]
            if channels != "keep":
                args += ["-ac", channels]
            if sample_rate != "keep":
                args += ["-ar", sample_rate]

    if codec == "h265":
        args += ["-tag:v", "hvc1"]
    if faststart:
        args += ["-movflags", "+faststart"]

    target = workdir / f"{safe_stem(name)}_压缩.mp4"
    _run_ffmpeg([*args, str(target)], timeout=1200)

    outcome = ProcessOutcome()
    _file_result(
        target,
        "video/mp4",
        {
            "level": level,
            "codec": codec,
            "rate_mode": rate_mode,
            "crf": crf if rate_mode == "crf" else None,
            "width": width,
            "fps": fps or None,
            "audio": audio_mode,
            "trim_start": round(start, 2),
            "trim_end": round(end, 2),
            "original_size": path.stat().st_size,
            "new_size": target.stat().st_size,
            "ratio": round((1 - target.stat().st_size / path.stat().st_size) * 100, 1),
            "duration": round(clip_duration, 1),
        },
        ["压缩后分辨率不会高于原视频；H.265 体积更小，但旧设备可能无法播放。"],
        outcome,
    )
    return outcome


def process_extract_audio(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    path = files[0]
    name = names[0]
    probe = _probe(path)
    if not _has_stream(probe, "audio"):
        raise TaskError("E3-422", "视频中没有音轨，无法提取音频")
    target_format = str(params.get("format", "mp3")).lower()
    if target_format not in AUDIO_TYPES:
        target_format = "mp3"
    bitrate = str(params.get("bitrate", "192k"))
    if bitrate not in AUDIO_BITRATES:
        bitrate = "192k"
    target = workdir / f"{safe_stem(name)}.{target_format}"
    _run_ffmpeg(
        ["-i", str(path), "-vn", *_audio_codec(target_format, bitrate), str(target)], timeout=600
    )
    outcome = ProcessOutcome()
    _file_result(
        target,
        AUDIO_TYPES[target_format],
        {"format": target_format, "duration": round(_duration(probe), 1), "new_size": target.stat().st_size},
        ["仅提取原视频音轨并重新编码。"],
        outcome,
    )
    return outcome


def process_video_convert(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    path = files[0]
    name = names[0]
    probe = _probe(path)
    if not _has_stream(probe, "video"):
        raise TaskError("E1-400", "文件中没有视频轨")
    duration = _duration(probe)
    if duration > 1800:
        raise TaskError("E2-413", "视频超过 30 分钟上限", 413)
    target_format = str(params.get("format", "mp4")).lower()
    if target_format not in VIDEO_TYPES:
        target_format = "mp4"

    target = workdir / f"{safe_stem(name)}.{target_format}"
    if target_format == "webm":
        codec = [
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "0",
            "-crf",
            "36",
            "-row-mt",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "libopus",
            "-b:a",
            "96k",
        ]
        timeout = 1200
    elif target_format == "wmv":
        codec = ["-c:v", "wmv2", "-b:v", "4M", "-c:a", "wmav2", "-b:a", "128k"]
        timeout = 900
    elif target_format == "avi":
        codec = ["-c:v", "mpeg4", "-q:v", "4", "-c:a", "libmp3lame", "-b:a", "128k"]
        timeout = 900
    else:
        codec = [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
        ]
        timeout = 900
        if target_format in {"mp4", "mov", "m4v"}:
            codec.extend(["-movflags", "+faststart"])
    _run_ffmpeg(
        ["-i", str(path), "-map", "0:v:0", "-map", "0:a?", *codec, str(target)],
        timeout=timeout,
    )
    outcome = ProcessOutcome()
    _file_result(
        target,
        VIDEO_TYPES[target_format],
        {"format": target_format, "duration": round(duration, 1), "new_size": target.stat().st_size},
        ["不同浏览器对 WebM / MOV 的支持不同，分享前请确认兼容性。"],
        outcome,
    )
    return outcome


def _whisper_model():
    from faster_whisper import WhisperModel

    model_dir = settings.whisper_model_path
    local_path = model_dir / settings.whisper_model_size
    cache_key = str(local_path)
    with _WHISPER_LOCK:
        if cache_key in _WHISPER_MODELS:
            return _WHISPER_MODELS[cache_key]
        model_dir.mkdir(parents=True, exist_ok=True)
        model = WhisperModel(
            str(local_path) if (local_path / "model.bin").exists() else settings.whisper_model_size,
            device="cpu",
            compute_type="int8",
            download_root=str(model_dir),
        )
        _WHISPER_MODELS[cache_key] = model
        return model


def _srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def process_speech_to_text(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    if not speech_available():
        raise TaskError("E4-503", "语音识别引擎不可用，请联系维护者", 503)
    path = files[0]
    name = names[0]
    probe = _probe(path)
    duration = _duration(probe)
    if duration <= 0:
        raise TaskError("E1-400", "音频时长为 0，无法识别")
    if duration > 3600:
        raise TaskError("E2-413", f"音频 {duration / 60:.0f} 分钟，上限 60 分钟", 413)
    if not _has_stream(probe, "audio"):
        raise TaskError("E1-400", "文件中没有音频轨")

    wav = workdir / ".speech.wav"
    _run_ffmpeg(
        ["-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
        timeout=300,
    )
    language_param = str(params.get("language", "auto"))
    language = {"zh-CN": "zh", "zh-TW": "zh", "en": "en"}.get(language_param)
    output_mode = str(params.get("output", "text"))

    try:
        model = _whisper_model()
        with wave.open(str(wav), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
                raise TaskError("E3-422", "音频预处理失败，请更换文件后重试")
            frames = handle.readframes(handle.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        segments, info = model.transcribe(
            audio,
            language=language,
            vad_filter=True,
            beam_size=1,
            word_timestamps=False,
        )
        entries = [
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": str(segment.text).strip(),
            }
            for segment in segments
            if str(segment.text).strip()
        ]
    except TaskError:
        raise
    except Exception as exc:  # pragma: no cover
        raise TaskError("E4-500", f"语音识别失败：{str(exc)[:160]}") from exc

    if not entries:
        raise TaskError("E3-422", "未识别到有效语音，可能是纯音乐、静音或音量过低")

    if output_mode == "srt":
        lines = []
        for index, entry in enumerate(entries, start=1):
            lines.append(str(index))
            lines.append(f"{_srt_time(entry['start'])} --> {_srt_time(entry['end'])}")
            lines.append(entry["text"])
            lines.append("")
        text = "\n".join(lines).strip()
        filename = f"{safe_stem(name)}.srt"
    elif output_mode == "timestamped":
        text = "\n".join(
            f"[{_srt_time(entry['start']).replace(',', '.')} -> {_srt_time(entry['end']).replace(',', '.')}] {entry['text']}"
            for entry in entries
        )
        filename = f"{safe_stem(name)}_时间戳.txt"
    else:
        text = "\n".join(entry["text"] for entry in entries)
        filename = f"{safe_stem(name)}.txt"

    return ProcessOutcome(
        results=[
            TextResult(
                filename=filename,
                text=text,
                meta={
                    "duration": round(duration, 1),
                    "segments": len(entries),
                    "detected_language": getattr(info, "language", None),
                    "output": output_mode,
                },
            )
        ],
        notes=[
            "时间戳为引擎估算值，允许数百毫秒误差；结果需人工校对。",
        ],
    )


def _say_voice(language: str) -> str | None:
    if language not in _VOICE_CACHE:
        _VOICE_CACHE[language] = None
        if shutil.which("say"):
            try:
                listing = subprocess.run(
                    ["say", "-v", "?"], capture_output=True, text=True, timeout=20
                ).stdout
            except Exception:
                listing = ""
            target_prefix = "zh" if language == "zh" else "en"
            for line in listing.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[-1].lower().startswith(target_prefix):
                    _VOICE_CACHE[language] = " ".join(parts[:-1])
                    break
    return _VOICE_CACHE[language]


def process_text_to_speech(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    if not tts_available():
        raise TaskError("E4-503", "语音合成引擎不可用，请联系维护者", 503)
    text = str(params.get("text", "")).strip()
    if not text:
        raise TaskError("E1-400", "请输入要合成的文本")
    if len(text) > 5000:
        raise TaskError("E2-413", f"文本 {len(text)} 字符，上限 5000 字符", 413)
    if re.search(r"<[^>]+>", text):
        raise TaskError("E1-400", "仅支持纯文本，不接受 HTML 或 SSML 标记")

    language = str(params.get("voice", "zh"))
    language = language if language in {"zh", "en"} else "zh"
    speed = float(params.get("speed", 1.0) or 1.0)
    speed = max(0.5, min(2.0, speed))
    target_format = str(params.get("format", "mp3")).lower()
    target_format = target_format if target_format in {"mp3", "wav"} else "mp3"

    text_file = workdir / ".tts.txt"
    text_file.write_text(text, encoding="utf-8")
    raw_audio = workdir / (".tts.aiff" if shutil.which("say") else ".tts.wav")

    if shutil.which("say"):
        command = ["say", "-r", str(round(175 * speed)), "-o", str(raw_audio), "-f", str(text_file)]
        voice = _say_voice(language)
        if voice:
            command[1:1] = ["-v", voice]
    else:
        binary = shutil.which("espeak-ng") or shutil.which("espeak")
        voice = "cmn" if language == "zh" else "en-us"
        command = [
            binary,
            "-v",
            voice,
            "-s",
            str(round(175 * speed)),
            "-w",
            str(raw_audio),
            "-f",
            str(text_file),
        ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as exc:
        raise TaskError("E4-504", "语音合成超时，请缩短文本后重试", 504) from exc
    if result.returncode != 0 or not raw_audio.exists():
        detail = (result.stderr or "").strip()[:160]
        raise TaskError("E3-422", f"语音合成失败：{detail or '未知原因'}")

    target = workdir / f"语音_{timestamp_label()}.{target_format}"
    if target_format == "wav" and raw_audio.suffix == ".wav":
        raw_audio.replace(target)
    else:
        _run_ffmpeg(["-i", str(raw_audio), "-vn", str(target)], timeout=120)
    raw_audio.unlink(missing_ok=True)
    text_file.unlink(missing_ok=True)

    probe = _probe(target)
    duration = _duration(probe)
    if duration <= 0:
        target.unlink(missing_ok=True)
        raise TaskError("E3-422", "合成结果为空，请调整文本后重试")

    return ProcessOutcome(
        results=[
            FileResult(
                filename=target.name,
                path=target,
                content_type=AUDIO_TYPES.get(target_format, "audio/mpeg"),
                meta={
                    "format": target_format,
                    "duration": round(duration, 1),
                    "chars": len(text),
                    "voice": language,
                    "speed": speed,
                },
            )
        ],
        notes=["只使用引擎内置通用音色；输入文本合成完成后立即丢弃，不保存为原始数据。"],
    )
