#!/usr/bin/env python3
"""
script.md からナレーション音声(macOS say)と実音のピアノトーンを合成し、
1本の音声ファイル(m4a)にまとめる。

script.md の書式:
  - 空行区切りの段落 = ナレーション(sayで読み上げ)
  - [TONE:C4] や [TONE:C4,E4,G4] の行 = その音(単音 or 和音)をゆったり鳴らす
    (音程・和音の聴き取りに向いた、余韻を残す長さ。約1.0〜1.6秒 + 余韻)
    (macOS内蔵のGM音源(gs_instruments.dls)のアコースティックグランドピアノ音色を
     tools/piano_tone バイナリでオフラインレンダリングして使用。サイン波ではない)
  - [BEAT:C4,E4,G4] の行 = その音を短く、テンポ感のある間隔(120bpm相当、0.5秒間隔)で鳴らす
    (拍子・リズムのデモ用。TONEより短く詰めて、実際の拍の速さに近づける)
  - [PAUSE:1.5] の行 = 指定した秒数、無音を挿入する(聴き取り練習で、正解発表の前に考える時間を作る用途など)
  - 文中の {{EN:English Term}} = その直前の専門用語を、ネイティブ発音の英語音声(Samantha)で
    挿入して読み上げる。例: "和声的短音階{{EN:Harmonic Minor Scale}}は、"
    Webページの台本表示では "(English Term)" という括弧書きに変換される

音声合成の直前に、発音辞書(PRONUNCIATION_FIXES, DEGREE_PATTERN)で
sayの読み間違いを補正する(例: 「2度」→「にど」、「属七の和音」→「ぞくしちのわおん」)。
script.md自体やWeb台本表示は漢字のまま変更されない。新しい用語で読み間違いが疑われる場合は、
このファイル冒頭の PRONUNCIATION_FIXES に追加する。

使い方:
  python3 tools/build_audio.py days/day01_.../script.md days/day01_.../audio.m4a

「聴き取り練習」という文字列を含む行が最初に現れた時点の再生位置(秒)を、
audio.marks.json に {"quiz": 秒数} として書き出す(Webページの「クイズへジャンプ」ボタン用)。
"""
import sys
import os
import re
import json
import struct
import wave
import subprocess
import tempfile

QUIZ_MARK_PHRASE = "聴き取り練習"  # このフレーズを含む行の開始位置を marks.json に記録する

SAMPLE_RATE = 44100
VOICE = "Kyoko (Enhanced)"
RATE = 160  # words per minute相当。ゆっくりめで優しい印象にする
EN_VOICE = "Samantha"
EN_RATE = 165  # 英語用語のネイティブ発音挿入用
PIANO_GAIN = 1.7  # ナレーションに対してピアノ音が小さかったための補正

EN_PATTERN = re.compile(r'\{\{EN:([^}]+)\}\}')

# 発音辞書: sayの読み間違いを防ぐため、ナレーション合成の直前にのみ適用する
# (script.md自体・Web台本表示は漢字のまま。音声合成用のテキストだけをここで変換する)
DIGIT_KANJI = {
    '1': 'いち', '2': 'に', '3': 'さん', '4': 'よん', '5': 'ご',
    '6': 'ろく', '7': 'なな', '8': 'はち', '9': 'きゅう',
}
DEGREE_PATTERN = re.compile(r'([1-9])度')  # 「2度」を「にたび」と誤読されるのを防ぐ(「にど」に固定)

PRONUNCIATION_FIXES = [
    ('属七の和音', 'ぞくしちのわおん'),
    ('属九の和音', 'ぞくくのわおん'),
    ('減七の和音', 'げんしちのわおん'),
    ('七の和音', 'しちのわおん'),
    ('導音', 'どうおん'),
    ('同主調', 'どうしゅちょう'),
    ('平行調', 'へいこうちょう'),
    ('前楽節', 'ぜんがくせつ'),
    ('後楽節', 'こうがくせつ'),
    ('楽節', 'がくせつ'),
    ('完全終止', 'かんぜんしゅうし'),
    ('半終止', 'はんしゅうし'),
    ('変終止', 'へんしゅうし'),
    ('偽終止', 'ぎしゅうし'),
    ('借用和音', 'しゃくようわおん'),
    ('代理和音', 'だいりわおん'),
    ('近親調', 'きんしんちょう'),
    ('白鍵', 'はっけん'),
    ('黒鍵', 'こっけん'),
    # 「方」は「〜かた(方法・様子を表す接尾語、人を指す敬称)」と
    # 「〜ほう(方向・比較・一般名詞)」の2通りの読みがあり、say任せだと
    # 頻繁に取り違えるため、実際に台本で使われている単語ごとに固定する。
    ('持っている方は', 'もっているかたは'),
    ('使った方は', 'つかったかたは'),
    ('の方が', 'のほうが'),
    ('弾き方', 'ひきかた'),
    ('弾いて', 'ひいて'),
    ('弾ける', 'ひける'),
    ('弾こう', 'ひこう'),
    ('弾く', 'ひく'),
    ('弾き', 'ひき'),
    ('呼び方', 'よびかた'),
    ('考え方', 'かんがえかた'),
    ('始まり方', 'はじまりかた'),
    ('数え方', 'かぞえかた'),
    ('終わり方', 'おわりかた'),
    ('聞こえ方', 'きこえかた'),
    ('並び方', 'ならびかた'),
    ('動かし方', 'うごかしかた'),
    ('させ方', 'させかた'),
    ('書き方', 'かきかた'),
    ('作り方', 'つくりかた'),
    ('借り方', 'かりかた'),
    ('一方', 'いっぽう'),
    ('両方', 'りょうほう'),
    ('方法', 'ほうほう'),
    ('方向性', 'ほうこうせい'),
    ('方向', 'ほうこう'),
    ('対位法', 'たいいほう'),
    ('声部', 'せいぶ'),
    ('反行', 'はんこう'),
    ('主旋律', 'しゅせんりつ'),
    ('留まらず', 'とどまらず'),
    ('経過音', 'けいかおん'),
    ('刺繍音', 'ししゅうおん'),
    ('掛留音', 'けいりゅうおん'),
    ('掛留という漢字', 'けいりゅうという漢字'),
    # 「主」もsayが「しゅ」ではなく訓読み「ぬし」にしてしまうことがある
    # (主旋律での誤読で判明)。音楽用語としての「主〜」複合語は全て固定する。
    ('主要三和音', 'しゅようさんわおん'),
    ('主和音', 'しゅわおん'),
    ('主調', 'しゅちょう'),
    ('主題', 'しゅだい'),
    ('主役', 'しゅやく'),
]


def apply_pronunciation_fixes(text):
    text = DEGREE_PATTERN.sub(lambda m: DIGIT_KANJI[m.group(1)] + 'ど', text)
    for kanji, reading in PRONUNCIATION_FIXES:
        text = text.replace(kanji, reading)
    return text

BEAT_NOTE_SECONDS = 0.30  # BEATマーカーの実際の音の長さ(短く切って詰める)
BEAT_GAP_SECONDS = 0.20   # BEATマーカー間の無音(音の長さ+無音=0.5秒=120bpm相当)
BEAT_FADE_SAMPLES = 300   # 音を短く切った際のクリック音防止用フェード

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PIANO_TONE_BIN = os.path.join(TOOLS_DIR, "piano_tone")

NOTE_INDEX = {
    'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'F': 5,
    'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8, 'A': 9, 'A#': 10, 'BB': 10, 'B': 11,
}


def note_to_midi(note):
    m = re.match(r'^([A-Ga-g])([#bB]?)(-?\d+)$', note.strip())
    if not m:
        raise ValueError(f"invalid note: {note}")
    letter, accidental, octave = m.groups()
    key = (letter.upper() + accidental.upper()) if accidental else letter.upper()
    idx = NOTE_INDEX[key]
    return (int(octave) + 1) * 12 + idx


def gen_piano_tone_frames(notes, hold_seconds, workdir, idx):
    midi_notes = [str(note_to_midi(n)) for n in notes]
    stereo_wav = os.path.join(workdir, f"tone_{idx}_stereo.wav")
    mono_wav = os.path.join(workdir, f"tone_{idx}_mono.wav")
    subprocess.run(
        [PIANO_TONE_BIN, stereo_wav, str(hold_seconds), *midi_notes],
        check=True,
    )
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", stereo_wav, mono_wav],
        check=True,
    )
    with wave.open(mono_wav, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    samples = struct.unpack(f"<{len(raw)//2}h", raw)
    boosted = [max(-32768, min(32767, int(s * PIANO_GAIN))) for s in samples]
    return struct.pack(f"<{len(boosted)}h", *boosted)


def gen_beat_tone_frames(notes, workdir, idx):
    midi_notes = [str(note_to_midi(n)) for n in notes]
    stereo_wav = os.path.join(workdir, f"beat_{idx}_stereo.wav")
    mono_wav = os.path.join(workdir, f"beat_{idx}_mono.wav")
    subprocess.run(
        [PIANO_TONE_BIN, stereo_wav, "0.05", *midi_notes],
        check=True,
    )
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", stereo_wav, mono_wav],
        check=True,
    )
    with wave.open(mono_wav, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    samples = struct.unpack(f"<{len(raw)//2}h", raw)
    boosted = [max(-32768, min(32767, int(s * PIANO_GAIN))) for s in samples]

    target_n = int(SAMPLE_RATE * BEAT_NOTE_SECONDS)
    cropped = boosted[:target_n]
    fade_n = min(BEAT_FADE_SAMPLES, len(cropped))
    for i in range(fade_n):
        factor = (fade_n - i) / fade_n
        pos = len(cropped) - fade_n + i
        cropped[pos] = int(cropped[pos] * factor)
    return struct.pack(f"<{len(cropped)}h", *cropped)


def gen_silence_frames(duration):
    return b'\x00\x00' * int(SAMPLE_RATE * duration)


def synth_segment(text, voice, rate, workdir, tag):
    txt_path = os.path.join(workdir, f"{tag}.txt")
    aiff_path = os.path.join(workdir, f"{tag}.aiff")
    wav_path = os.path.join(workdir, f"{tag}.wav")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    subprocess.run(
        ["say", "-v", voice, "-r", str(rate), "-o", aiff_path, "-f", txt_path],
        check=True,
    )
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", aiff_path, wav_path],
        check=True,
    )
    with wave.open(wav_path, "rb") as wf:
        return wf.readframes(wf.getnframes())


def synth_narration(text, workdir, idx):
    # EN_PATTERN.split with a capturing group -> [ja, en, ja, en, ja, ...]
    parts = EN_PATTERN.split(text)
    frames = bytearray()
    for i, part in enumerate(parts):
        if not part.strip():
            continue
        is_en = (i % 2 == 1)
        voice = EN_VOICE if is_en else VOICE
        rate = EN_RATE if is_en else RATE
        text_to_speak = part if is_en else apply_pronunciation_fixes(part)
        seg = synth_segment(text_to_speak, voice, rate, workdir, f"narr_{idx}_{i}")
        if is_en:
            frames.extend(gen_silence_frames(0.15))
        frames.extend(seg)
        if is_en:
            frames.extend(gen_silence_frames(0.15))
    return bytes(frames)


def main(script_path, out_path):
    with open(script_path, encoding="utf-8") as f:
        raw_lines = [l.rstrip("\n") for l in f]

    workdir = tempfile.mkdtemp(prefix="build_audio_")
    all_frames = bytearray()
    buf = []
    idx = [0]
    tone_idx = [0]
    marks = {}

    def flush():
        text = "\n".join(buf).strip()
        buf.clear()
        if not text:
            return
        idx[0] += 1
        frames = synth_narration(text, workdir, idx[0])
        all_frames.extend(frames)
        all_frames.extend(gen_silence_frames(0.5))

    for line in raw_lines:
        stripped = line.strip()
        m = re.match(r'^\[TONE:([^\]]+)\]$', stripped)
        b = re.match(r'^\[BEAT:([^\]]+)\]$', stripped)
        p = re.match(r'^\[PAUSE:([\d.]+)\]$', stripped)
        if p:
            flush()
            all_frames.extend(gen_silence_frames(float(p.group(1))))
        elif m:
            flush()
            notes = [n.strip() for n in m.group(1).split(",")]
            hold = 1.0 if len(notes) == 1 else 1.6
            tone_idx[0] += 1
            all_frames.extend(gen_silence_frames(0.3))
            all_frames.extend(gen_piano_tone_frames(notes, hold, workdir, tone_idx[0]))
            all_frames.extend(gen_silence_frames(0.5))
        elif b:
            flush()
            notes = [n.strip() for n in b.group(1).split(",")]
            tone_idx[0] += 1
            all_frames.extend(gen_beat_tone_frames(notes, workdir, tone_idx[0]))
            all_frames.extend(gen_silence_frames(BEAT_GAP_SECONDS))
        elif stripped == "":
            buf.append("")
        else:
            if "quiz" not in marks and QUIZ_MARK_PHRASE in stripped:
                flush()
                marks["quiz"] = round(len(all_frames) / 2 / SAMPLE_RATE, 1)
            buf.append(stripped)
    flush()

    final_wav = os.path.join(workdir, "final.wav")
    with wave.open(final_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(all_frames))

    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", final_wav, out_path], check=True)
    total_seconds = len(all_frames) / 2 / SAMPLE_RATE

    marks_path = os.path.splitext(out_path)[0] + ".marks.json"
    with open(marks_path, "w", encoding="utf-8") as f:
        json.dump(marks, f, ensure_ascii=False, indent=2)

    print(f"Generated: {out_path} ({total_seconds/60:.1f} min), marks: {marks}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_audio.py <script.md> <out.m4a>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
