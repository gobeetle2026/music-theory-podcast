#!/usr/bin/env python3
"""
Day1〜30 + おまけ回のaudio.m4aから、Podcastアプリ用のRSSフィード(feed.xml)を生成する。
GitHub Pages(https://gobeetle2026.github.io/music-theory-podcast/)での配信を前提とする。

使い方:
  python3 tools/build_podcast_feed.py
"""
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.parse import quote
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_player_page as bp

BASE = bp.BASE
BASE_URL = "https://gobeetle2026.github.io/music-theory-podcast"
FEED_URL = f"{BASE_URL}/feed.xml"
COVER_URL = f"{BASE_URL}/web/cover.png"
FEED_PATH = os.path.join(BASE, "feed.xml")

AUTHOR_NAME = "音楽理論学習"
AUTHOR_EMAIL = "noreply@example.com"

# 実際の配信日ではないため、Day1を起点に1日ずつ架空の公開日をずらして
# ポッドキャストアプリでの並び順(episode番号・pubDateとも昇順で一致)を安定させる。
EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def get_duration_seconds(audio_path):
    out = subprocess.run(["afinfo", audio_path], capture_output=True, text=True, check=True).stdout
    m = re.search(r"estimated duration:\s*([\d.]+) sec", out)
    return float(m.group(1))


def format_duration(seconds):
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def plain_transcript(dir_name):
    """WebページのHTML台本表示(bp.load_transcript_html)と同じ変換ロジックで、
    RSSのdescription用にプレーンテキスト版の台本全文を作る(段落は空行区切り)。"""
    script_path = os.path.join(BASE, "days", dir_name, "script.md")
    with open(script_path, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f]
    parts = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^\[PAUSE:[\d.]+\]$', stripped):
            continue
        tone = bp.note_marker_to_text(stripped)
        if tone:
            parts.append(tone)
        else:
            parts.append(bp.EN_DISPLAY_PATTERN.sub(lambda m: f" ({m.group(1)})", stripped))
    return "\n\n".join(parts)


def html_transcript(dir_name):
    return bp.load_transcript_html(dir_name)


def episode_item(*, guid, title, summary, dir_name, audio_rel_path, pub_date, episode_num=None, season=1, episode_type="full"):
    audio_path = os.path.join(BASE, audio_rel_path)
    size_bytes = os.path.getsize(audio_path)
    duration = get_duration_seconds(audio_path)
    url = f"{BASE_URL}/{quote(audio_rel_path)}"

    full_text = plain_transcript(dir_name)
    description = f"{summary}\n\n――――――――――\n\n{full_text}"
    content_html = f"<p>{escape(summary)}</p><hr/>\n" + html_transcript(dir_name)
    content_cdata = content_html.replace("]]>", "] ]>")

    extra = ""
    if episode_num is not None:
        extra += f"      <itunes:season>{season}</itunes:season>\n"
        extra += f"      <itunes:episode>{episode_num}</itunes:episode>\n"
    extra += f"      <itunes:episodeType>{episode_type}</itunes:episodeType>\n"

    return f"""    <item>
      <title>{escape(title)}</title>
      <description>{escape(description)}</description>
      <content:encoded><![CDATA[{content_cdata}]]></content:encoded>
      <itunes:summary>{escape(summary)}</itunes:summary>
      <guid isPermaLink="false">{escape(guid)}</guid>
      <pubDate>{format_datetime(pub_date)}</pubDate>
      <enclosure url="{escape(url)}" length="{size_bytes}" type="audio/x-m4a"/>
      <itunes:duration>{format_duration(duration)}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
{extra}    </item>"""


def build_items():
    items_with_date = []

    for day in bp.DAYS:
        pub_date = EPOCH + timedelta(days=day["num"] - 1)
        xml = episode_item(
            guid=f"music-theory-podcast-day{day['num']:02d}",
            title=f"第{day['num']}回 {day['title']}",
            summary=day["desc"],
            dir_name=day["dir"],
            audio_rel_path=f"days/{day['dir']}/audio.m4a",
            pub_date=pub_date,
            episode_num=day["num"],
            season=1,
        )
        items_with_date.append((pub_date, xml))

    bonus_start = EPOCH + timedelta(days=len(bp.DAYS) + 30)
    for i, entry in enumerate(bp.BONUS):
        pub_date = bonus_start + timedelta(days=i)
        xml = episode_item(
            guid=f"music-theory-podcast-{entry['id']}",
            title=f"おまけ {entry['title']}",
            summary=entry["desc"],
            dir_name=entry["dir"],
            audio_rel_path=f"days/{entry['dir']}/audio.m4a",
            pub_date=pub_date,
            episode_num=None,
            episode_type="bonus",
        )
        items_with_date.append((pub_date, xml))

    # 新しいものが上に来るよう、pubDate降順で並べる(標準的なpodcastフィードの慣習)
    items_with_date.sort(key=lambda t: t[0], reverse=True)
    return [xml for _, xml in items_with_date]


def build_feed():
    items_xml = "\n".join(build_items())
    last_build = format_datetime(datetime.now(timezone.utc))

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(bp.SERIES_TITLE)}</title>
    <link>{escape(BASE_URL)}</link>
    <atom:link href="{escape(FEED_URL)}" rel="self" type="application/rss+xml"/>
    <language>ja</language>
    <description>{escape("自転車に乗りながら聴くだけで学べる、ゼロからの音楽理論講座。Day1から順番に、音の基礎から和声・楽式まで体系的に学ぶ。")}</description>
    <itunes:summary>自転車に乗りながら聴くだけで学べる、ゼロからの音楽理論講座。Day1から順番に、音の基礎から和声・楽式まで体系的に学ぶ。</itunes:summary>
    <itunes:author>{escape(AUTHOR_NAME)}</itunes:author>
    <itunes:owner>
      <itunes:name>{escape(AUTHOR_NAME)}</itunes:name>
      <itunes:email>{escape(AUTHOR_EMAIL)}</itunes:email>
    </itunes:owner>
    <itunes:image href="{escape(COVER_URL)}"/>
    <image>
      <url>{escape(COVER_URL)}</url>
      <title>{escape(bp.SERIES_TITLE)}</title>
      <link>{escape(BASE_URL)}</link>
    </image>
    <itunes:category text="Education"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <lastBuildDate>{last_build}</lastBuildDate>
{items_xml}
  </channel>
</rss>
"""


def main():
    xml = build_feed()
    with open(FEED_PATH, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"wrote {FEED_PATH} ({len(bp.DAYS)} days + {len(bp.BONUS)} bonus episodes)")


if __name__ == "__main__":
    main()
