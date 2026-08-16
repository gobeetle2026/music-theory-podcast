#!/usr/bin/env python3
"""
複数Dayのaudio.m4aを1本につなげた、連続再生用プレイリスト音声を作る。
自転車での聞き流し用に、話と話の間に短いアナウンスを挟み、
1ページの容量を抑えるためビットレートを下げて書き出す
(通常のDay単体ページはこのビットレート変更の影響を受けない)。

使い方:
  python3 tools/build_playlist.py 1 5 web_playlists/playlist01.m4a
  (Day1からDay5までを1本にまとめる)

出力と同じディレクトリ・同じベース名で、各Dayの開始位置(秒)を
{"day01": 0.0, "day02": 123.4, ...} として *.marks.json にも書き出す
(Webページの「DayNへジャンプ」ボタン用)。
"""
import sys
import os
import json
import wave
import subprocess
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_RATE = 44100
VOICE = "Kyoko (Enhanced)"
RATE = 160
BITRATE = 40000  # 5話ぶんを16MB以内に収めるため、通常回(既定ビットレート)より下げる


def gen_silence(duration):
    return b'\x00\x00' * int(SAMPLE_RATE * duration)


def synth_announce(text, workdir, tag):
    txt_path = os.path.join(workdir, f"{tag}.txt")
    aiff_path = os.path.join(workdir, f"{tag}.aiff")
    wav_path = os.path.join(workdir, f"{tag}.wav")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "-o", aiff_path, "-f", txt_path], check=True)
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", aiff_path, wav_path],
        check=True,
    )
    with wave.open(wav_path, "rb") as wf:
        return wf.readframes(wf.getnframes())


def find_day_dir(num):
    for name in sorted(os.listdir(os.path.join(BASE, "days"))):
        if name.startswith(f"day{num:02d}_"):
            return name
    raise FileNotFoundError(f"day{num:02d}_... not found under days/")


def read_wav_data_chunk(path):
    # afconvert が m4a からデコードすると、WAVE_FORMAT_EXTENSIBLE 付きのヘッダを
    # 書き出すことがあり、Python標準のwaveモジュールが読めない(unknown format)ため、
    # data チャンクだけを自前で取り出す
    with open(path, "rb") as f:
        raw = f.read()
    pos = 12
    while pos < len(raw):
        chunk_id = raw[pos:pos + 4]
        chunk_size = int.from_bytes(raw[pos + 4:pos + 8], "little")
        if chunk_id == b"data":
            return raw[pos + 8:pos + 8 + chunk_size]
        pos += 8 + chunk_size + (chunk_size % 2)
    raise ValueError(f"no data chunk found in {path}")


def decode_to_wav_frames(m4a_path, workdir, tag):
    wav_path = os.path.join(workdir, f"{tag}.wav")
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", m4a_path, wav_path],
        check=True,
    )
    return read_wav_data_chunk(wav_path)


def main(start, count, out_path):
    workdir = tempfile.mkdtemp(prefix="build_playlist_")
    all_frames = bytearray()
    marks = {}

    for i in range(count):
        num = start + i
        dir_name = find_day_dir(num)
        m4a_path = os.path.join(BASE, "days", dir_name, "audio.m4a")

        ann_frames = synth_announce(f"第{num}回です。", workdir, f"ann_{num}")
        all_frames.extend(gen_silence(0.6))
        all_frames.extend(ann_frames)
        all_frames.extend(gen_silence(0.8))

        marks[f"day{num:02d}"] = round(len(all_frames) / 2 / SAMPLE_RATE, 1)

        day_frames = decode_to_wav_frames(m4a_path, workdir, f"day_{num}")
        all_frames.extend(day_frames)
        all_frames.extend(gen_silence(1.2))
        print(f"  + Day{num} ({dir_name})")

    final_wav = os.path.join(workdir, "final.wav")
    with wave.open(final_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(all_frames))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    subprocess.run(
        ["afconvert", "-f", "m4af", "-d", "aac", "-b", str(BITRATE), final_wav, out_path],
        check=True,
    )

    marks_path = os.path.splitext(out_path)[0] + ".marks.json"
    with open(marks_path, "w", encoding="utf-8") as f:
        json.dump(marks, f, ensure_ascii=False, indent=2)

    total_seconds = len(all_frames) / 2 / SAMPLE_RATE
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"Generated: {out_path} ({total_seconds/60:.1f} min, {size_mb:.2f} MB), marks: {marks}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: build_playlist.py <start_day> <count> <out.m4a>")
        sys.exit(1)
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
