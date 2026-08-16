#!/usr/bin/env python3
"""
各Dayのaudio.m4a + script.mdから、Android等のブラウザで聴ける
単体HTMLページ(音声をdata URIとして埋め込み)を生成する。
生成物はweb/dayNN.htmlに出力し、Artifactツールで個別に公開する。

使い方:
  python3 tools/build_player_page.py
"""
import base64
import html
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE, "web")
PLAYLISTS_DIR = os.path.join(BASE, "playlists")

SERIES_TITLE = "音楽理論学習"
SERIES_TOTAL_HINT = "全30回(予定・分量により前後)"
FAVICON = "🎹"

DAYS = [
    {
        "num": 1,
        "dir": "day01_音とオクターブ",
        "title": "音とオクターブ",
        "desc": "音は空気の振動であること、ドレミの「階名」と「音名」の違い、鍵盤の仕組み、そしてオクターブと周波数の関係を学ぶ回。",
        "points": [
            "音は空気の振動。振動の速さ(周波数)が高さを決める",
            "ドレミには「階名」と「音名」の2つの役割がある(日本語:ハニホヘト/英語:C D E F G A B)",
            "鍵盤上でいちばん近い距離が「半音」",
            "オクターブ = 同じ音名どうしの最も近い関係。周波数はちょうど2倍になる",
        ],
    },
    {
        "num": 2,
        "dir": "day02_半音と全音",
        "title": "半音と全音",
        "desc": "前回登場した「半音」を掘り下げ、半音2つ分の「全音」との違い、そして鍵盤の中で距離が変わる場所を学ぶ回。",
        "points": [
            "半音 = 鍵盤上でいちばん近い距離。全音 = 半音2つ分の距離",
            "ミとファ、シとドは黒鍵を挟まないため半音の関係になる",
            "白鍵だけを見ても、全音の場所と半音の場所が混在している",
            "この並び方の規則性が、次回以降学ぶ「音階」の正体になる",
        ],
    },
    {
        "num": 3,
        "dir": "day03_音程の基礎",
        "title": "音程の基礎",
        "desc": "2つの音の距離を「度」という単位で数える方法を学ぶ回。2度・3度から、安定した響きを持つ5度、オクターブと同じ8度まで。",
        "points": [
            "音程 = 2音の距離。基準の音を1度として順に数える",
            "ド→ミは3度、ド→ソは5度(安定した力強い響き)",
            "8度は前回までに学んだ「オクターブ」と同じ関係",
            "度数(数字)と音程の「質」の違いは次回Day4で扱う",
        ],
    },
    {
        "num": 4,
        "dir": "day04_音程の種類",
        "title": "音程の種類",
        "desc": "同じ3度でも響きが違う理由を学ぶ回。長・短・完全・増・減という「音程の質」を、実際の響きと結びつけて理解する。",
        "points": [
            "長3度は明るく開けた響き、短3度は陰りのある響き。半音の数の違いから生まれる",
            "1・4・5・8度は完全音程(安定)、2・3・6・7度は長/短の質を持つ",
            "完全・長・短からさらにずれた音程には増・減という言葉を使う",
            "悲愴・月光の切なさは、和音に含まれる短3度の響きが大きな理由の一つ",
        ],
    },
    {
        "num": 5,
        "dir": "day05_長音階",
        "title": "長音階",
        "desc": "ドレミファソラシドの規則性を学ぶ回。全・全・半・全・全・全・半という並び方が、長音階(メジャースケール)の正体。",
        "points": [
            "長音階 = 全・全・半・全・全・全・半という並び方",
            "この並び方さえ守れば、どの音から始めても同じ性格の音階になる(移動ド)",
            "開始音によってはシャープ・フラットが必要になる",
            "1番目と3番目の音が長3度の関係にあることが「長」音階の名前の由来",
        ],
    },
    {
        "num": 6,
        "dir": "day06_短音階",
        "title": "短音階",
        "desc": "悲愴・月光の切なさの正体に迫る回。自然的・和声的・旋律的という3種類の短音階と、「導音」が生む強い戻りの感覚を学ぶ。",
        "points": [
            "自然的短音階 = 白鍵だけ。1番目と3番目が短3度",
            "和声的短音階 = 7番目の音を半音上げ、主音へ強く戻る「導音」を作る",
            "その代わり6番目と7番目の間に、独特で異国的な増2度が生まれる",
            "旋律的短音階 = 上りだけ6・7番目を上げてなめらかにし、下りは自然的短音階に戻る",
        ],
    },
    {
        "num": 7,
        "dir": "day07_調号と五度圏",
        "title": "調号と五度圏",
        "desc": "曲によってシャープ・フラットの数が違う理由を学ぶ回。五度圏の規則と、悲愴・月光にもつながる「平行調」の関係を理解する。",
        "points": [
            "完全5度上がるごとにシャープが1つ増え、5度下がるごとにフラットが1つ増える",
            "この関係を円状に並べたものが五度圏",
            "シャープはファ・ド・ソ・レ・ラ・ミ・シの順、フラットはその逆順で増える",
            "同じ調号を共有する長調・短調のペアが平行調(悲愴→変ホ長調、月光→ホ長調)",
        ],
        "diagram": """<figure class="diagram">
  <svg viewBox="0 0 480 480" role="img" aria-label="五度圏の図。頂点のCから時計回りにG, D, A, E, B, F#とシャープが1つずつ増え、反時計回りにF, Bb, Eb, Ab, Dbとフラットが1つずつ増える。内側の輪は各長調の平行調(短調)を示す。">
    <circle cx="240" cy="240" r="195" fill="none" stroke="var(--hairline)" stroke-width="1"/>
    <circle cx="240" cy="240" r="125" fill="none" stroke="var(--hairline)" stroke-width="1"/>

    <text x="240" y="80" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">C</text>
    <text x="320" y="101.4" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">G</text>
    <text x="378.6" y="160" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">D</text>
    <text x="400" y="240" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">A</text>
    <text x="378.6" y="320" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--accent)">E</text>
    <text x="320" y="378.6" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">B</text>
    <text x="240" y="400" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="14" font-weight="600" fill="var(--text)">F#/Gb</text>
    <text x="160" y="378.6" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">Db</text>
    <text x="101.4" y="320" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">Ab</text>
    <text x="80" y="240" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--accent)">Eb</text>
    <text x="101.4" y="160" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">Bb</text>
    <text x="160" y="101.4" dy="0.35em" text-anchor="middle" font-family="var(--serif)" font-size="18" font-weight="600" fill="var(--text)">F</text>

    <text x="240" y="150" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">Am</text>
    <text x="285" y="162" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">Em</text>
    <text x="317.9" y="195" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">Bm</text>
    <text x="330" y="240" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">F#m</text>
    <text x="317.9" y="285" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--accent)">C#m</text>
    <text x="285" y="317.9" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">G#m</text>
    <text x="240" y="330" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="12" fill="var(--text-muted)">D#m</text>
    <text x="195" y="317.9" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">Bbm</text>
    <text x="162" y="285" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">Fm</text>
    <text x="150" y="240" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--accent)">Cm</text>
    <text x="162" y="195" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">Gm</text>
    <text x="195" y="162" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="var(--text-muted)">Dm</text>

    <text x="240" y="25" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">0</text>
    <text x="347.5" y="53.8" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">1♯</text>
    <text x="426.2" y="132.5" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">2♯</text>
    <text x="455" y="240" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">3♯</text>
    <text x="426.2" y="347.5" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--accent)">4♯</text>
    <text x="347.5" y="426.2" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">5♯</text>
    <text x="240" y="455" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="10" fill="var(--text-muted)">6♯/6♭</text>
    <text x="132.5" y="426.2" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">5♭</text>
    <text x="53.8" y="347.5" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">4♭</text>
    <text x="25" y="240" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--accent)">3♭</text>
    <text x="53.8" y="132.5" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">2♭</text>
    <text x="132.5" y="53.8" dy="0.35em" text-anchor="middle" font-family="var(--mono)" font-size="11" fill="var(--text-muted)">1♭</text>
  </svg>
  <figcaption>五度圏。外側の輪が長調、内側の輪がその平行調(短調)、一番外側の数字がシャープ・フラットの数。時計回りに5度ずつ上がるとシャープが1つ増え、反時計回りに5度ずつ下がるとフラットが1つ増える。オレンジで示したEb / Cmが悲愴(ハ短調)の平行調、E / C#mが月光(嬰ハ短調)の平行調。</figcaption>
</figure>""",
    },
    {
        "num": 8,
        "dir": "day08_三和音",
        "title": "三和音",
        "desc": "和音の基本、三和音に入る回。長三和音と短三和音の作り方と、真ん中の音1つが曲全体の明るさを左右する仕組みを学ぶ。",
        "points": [
            "三和音 = ある音を基準に3度を2つ積み重ねたもの",
            "長三和音 = 下に長3度・上に短3度、短三和音 = その逆",
            "外側(根音〜第5音)はどちらも完全5度で共通。真ん中の音だけが明暗を分ける",
            "悲愴の冒頭の和音、月光の伴奏はどちらも短三和音が土台",
        ],
    },
    {
        "num": 9,
        "dir": "day09_減三和音と増三和音",
        "title": "減三和音と増三和音",
        "desc": "三和音の残り2種類、減三和音と増三和音を学ぶ回。外側の音程そのものが緊張感を生む、不安定な響きの正体を理解する。",
        "points": [
            "減三和音(Diminished Triad) = 短3度を2つ重ねる。外側は完全5度より半音狭い減5度",
            "増三和音(Augmented Triad) = 長3度を2つ重ねる。外側は完全5度より半音広い増5度",
            "長・短三和音は外側が完全5度で安定。減・増三和音は外側そのものが緊張感の元",
            "この回から専門用語にネイティブ発音の英語を併記(音声・台本テキストとも)",
        ],
    },
    {
        "num": 10,
        "dir": "day10_七の和音",
        "title": "七の和音",
        "desc": "三和音にもう1音重ねる七の和音、中でも最重要の属七の和音を学ぶ回。「主和音に帰りたがる力」の正体に迫る。",
        "points": [
            "七の和音(Seventh Chord) = 三和音の上にさらに3度を重ね、根音から第7音までが7度になる和音",
            "属七の和音(Dominant Seventh Chord) = 調の5番目の音の長三和音+短7度",
            "内部に増4度・減5度(不安定な音程)を含み、主和音へ強く進みたがる",
            "属七→主和音の進行は音楽で最も基本的な「着地」パターン。悲愴・月光のフレーズ終止にも頻出",
        ],
    },
    {
        "num": 11,
        "dir": "day11_和音の転回形",
        "title": "和音の転回形",
        "desc": "同じ和音でも一番下の音が変わると響きの重心が変わる、転回形を学ぶ回。低音の動きをなめらかにする実用的な理由も理解する。",
        "points": [
            "基本形(Root Position) = 根音が最低音。第一転回形(First Inversion) = 第3音が最低音、第二転回形(Second Inversion) = 第5音が最低音",
            "和音の名前を決めるのは最低音ではなく、音の組み合わせそのもの",
            "転回形を使うと、和音間を移動する際の低音の動きをなめらかにできる",
            "基本形が最も安定、第二転回形が最も不安定で通過点的な響き",
        ],
    },
    {
        "num": 12,
        "dir": "day12_ダイアトニックコード",
        "title": "ダイアトニックコード",
        "desc": "音階の音だけで作れる7つの和音、ダイアトニックコードを学ぶ回。長・短・短・長・長・短・減という規則性が、これまでの知識を1つにつなげる。",
        "points": [
            "ダイアトニックコード(Diatonic Chords) = 音階の音だけを使って各度数に作る三和音",
            "長調では 長・短・短・長・長・短・減(I ii iii IV V vi vii°)という決まった並びになる",
            "I・IV・Vは主要三和音(Primary Triads)と呼ばれ、必ず長三和音になる",
            "vii°(シレファ)はDay10の属七の和音(ソシレファ)から根音を抜いた形と一致する",
        ],
    },
    {
        "num": 13,
        "dir": "day13_主要三和音とカデンツ",
        "title": "主要三和音とカデンツ",
        "desc": "I・IV・Vにトニック・サブドミナント・ドミナントという役割を与え、フレーズの終わり方(カデンツ)を学ぶ回。Phase2の総仕上げ。",
        "points": [
            "I=トニック(家)、IV=サブドミナント(少し離れた場所)、V=ドミナント(最も緊張感の高い場所)",
            "完全終止(V→I、特にV7→I)が最も力強い終わり方",
            "半終止(V で止まる)は宙ぶらりん、変終止(IV→I)は柔らかい終わり方",
            "偽終止(V→vi)は予想を裏切る進行。悲愴・月光の最後は基本的に完全終止で締めくくられる",
        ],
    },
    {
        "num": 14,
        "dir": "day14_実践1_悲愴の和音進行",
        "title": "実践1: 悲愴の和音進行",
        "desc": "ここまでの理論を使って、悲愴ソナタ冒頭のグラーヴェ序奏を実際に聴き解く回。ハ短調のトニックから減七の和音、緊張感の強い属九の和音へ。",
        "points": [
            "冒頭はハ短調のトニック(ド ミ♭ ソ)。フォルテピアノ(強く打ってすぐ弱める)で始まる",
            "2・3小節目は減七の和音(短3度を3つ重ねた4音の和音)で不安定になる",
            "序奏全体は半音階的・転調が多く、落ち着く場所を避け続ける",
            "序奏の終わりは属七の和音よりさらに緊張感の強い属九の和音で止まり、アレグロへなだれ込む",
        ],
    },
    {
        "num": 15,
        "dir": "day15_拍子の基礎",
        "title": "拍子の基礎",
        "desc": "Phase3の最初の回。2拍子・3拍子・4拍子という強弱のパターンを学び、悲愴のアレグロと月光の第一楽章が同じ拍子でできていることを知る。",
        "points": [
            "拍子(Time Signature) = 強い拍と弱い拍が規則的に繰り返されるパターン",
            "2拍子=強弱、3拍子=強弱弱、4拍子=強弱中弱",
            "悲愴のアレグロ・ディ・モルト・エ・コン・ブリオも、月光の第一楽章も、どちらも2分の2拍子(アラ・ブレーヴェ)",
            "細かく4つに割って数えるか、大きな2拍でまとめて感じるかで、体感するスピード感が変わる",
        ],
    },
    {
        "num": 16,
        "dir": "day16_シンコペーション",
        "title": "リズムパターンとシンコペーション",
        "desc": "拍をさらに半分に分割したときに生まれるリズムの表情を学ぶ回。裏拍にアクセントを置くシンコペーションの独特な推進力を体感する。",
        "points": [
            "拍の分割(Subdivision) = 1拍をさらに半分に分けること",
            "素直なリズムは拍の頭にアクセント",
            "シンコペーション(Syncopation) = 裏拍にアクセントを置き、本来強い拍を休むことで生まれる前のめりな感覚",
            "ジャズ・ポップス・ラテン音楽で広く使われ、クラシックでも聴き手の予想を裏切る効果として使われる",
        ],
    },
    {
        "num": 17,
        "dir": "day17_機能和声",
        "title": "機能和声",
        "desc": "Day13のトニック・サブドミナント・ドミナントを深掘りする回。残りの4つの和音がそれぞれどの機能の仲間かを整理し、Day13の偽終止の謎も解ける。",
        "points": [
            "ii(サブドミナントの仲間)、vi(トニックの仲間)、vii°(ドミナントの仲間)",
            "iii はトニックにもドミナントにも寄り添える、あいまいな性格を持つ",
            "偽終止(V→vi)が意外に聞こえるのは、viがトニックに近いが同じではないから",
            "I-V-vi-IVは、主要三和音と代理和音を組み合わせた、ジャンルを問わず使われる定番進行",
        ],
    },
    {
        "num": 18,
        "dir": "day18_二次ドミナント",
        "title": "二次ドミナント",
        "desc": "ドミナントの働きを、トニック以外の和音にも一時的に作り出す、二次ドミナントを学ぶ回。音階の外の音1つで生まれる「一瞬のトニック化」を体感する。",
        "points": [
            "二次ドミナント(Secondary Dominant) = トニック以外の和音に対して作る、専用のドミナント",
            "音階の外の音を1つ混ぜることで、その和音を一瞬だけ主役に見せかける(トニック化 Tonicization)",
            "V/V(ドの調でレファ#ラ)はソへ、V/vi(ミソ#シ)はラへ、強い引力で進む",
            "転調とは違い、あくまで一時的な色付け。クラシック・ジャズ・ポップス問わず広く使われる",
        ],
    },
    {
        "num": 19,
        "dir": "day19_借用和音",
        "title": "借用和音",
        "desc": "同主調(同じ主音を持つ長調と短調)から和音の色をそのまま借りてくる、借用和音を学ぶ回。二次ドミナントとの違いも整理する。",
        "points": [
            "同主調(Parallel Key) = 主音が同じ長調と短調の関係(平行調とは別物)",
            "借用和音(Borrowed Chord) = 同主調のもう一方から和音をそのまま借りる技法",
            "長調でivを借りると切なく映画的な響き、♭VIを借りるとドラマチックな翳りが生まれる",
            "二次ドミナントは「引力」を作る技法、借用和音は「色」を持ち込む技法。ピカルディ終止はその逆方向",
        ],
    },
    {
        "num": 20,
        "dir": "day20_転調の基礎",
        "title": "転調の基礎",
        "desc": "Phase4最終回。二次ドミナントとは違い、新しい調を本当の主役として扱う「転調」と、橋渡し役のピボットコードを学ぶ。",
        "points": [
            "転調(Modulation) = 一時的なトニック化と違い、新しい調をしばらく本当の主役として扱う技法",
            "近親調(Closely Related Key) = 五度圏で隣り合う調や平行調など、最も自然に移りやすい調",
            "ピボットコード(Pivot Chord) = もとの調と新しい調、両方の意味で読み替えられる橋渡しの和音",
            "新しい調のドミナントでしっかり着地することで転調が確定する。ソナタ形式でも多用される王道の型",
        ],
    },
    {
        "num": 21,
        "dir": "day21_動機とフレーズ",
        "title": "動機・フレーズ・楽節",
        "desc": "Phase5「楽曲の構造」の最初の回。曲を組み立てる最小単位、動機からフレーズ、質問と答えのペアである楽節までを学ぶ。",
        "points": [
            "動機(Motif) = 曲の中で最小の意味あるまとまり。形を保ったまま移調されて展開される",
            "フレーズ(Phrase) = 動機がまとまってできる、カデンツで終わる音楽の「文章」",
            "楽節(Period) = 質問のような前楽節(半終止)と、答えのような後楽節(完全終止)のペア",
            "「きらきら星」の前半・後半もこの前楽節・後楽節の関係そのもの",
        ],
    },
    {
        "num": 22,
        "dir": "day22_楽式",
        "title": "楽式",
        "desc": "楽節が組み合わさってできる、曲全体の設計図を学ぶ回。前へ進み続ける二部形式と、円を描いて戻ってくる三部形式の違いを体感する。",
        "points": [
            "楽式(Musical Form) = 楽節が組み合わさってできる、曲全体の設計図",
            "二部形式(Binary Form、AB) = 前へ前へと進んでいく2つのまとまり",
            "三部形式(Ternary Form、ABA) = 対照的なBを経て、最初のAに戻ってくる3つのまとまり",
            "三部形式の「戻ってくる」瞬間が独特の安心感を生む。ポップスのAメロ・サビ・Aメロにも通じる",
        ],
    },
    {
        "num": 23,
        "dir": "day23_ソナタ形式",
        "title": "ソナタ形式",
        "desc": "月光ソナタ第一楽章を題材に、クラシック最重要の形式、ソナタ形式を学ぶ回。バラバラの調が最後に1つへまとまる仕組みを体感する。",
        "points": [
            "ソナタ形式(Sonata Form) = 提示部・展開部・再現部の3部構成。異なる調の主題が再現部で1つの調にまとまる",
            "月光ソナタでは第二主題があえて短調(嬰ト短調)のまま提示され、一貫した静けさを保つ",
            "展開部はドミナントの和音の上にじっと留まることで、静かな緊張感を作る",
            "劇的な対比よりも静かな響きの移り変わりを重視した、自由度の高いソナタ形式の例",
        ],
    },
    {
        "num": 24,
        "dir": "day24_変奏曲形式",
        "title": "変奏曲形式",
        "desc": "1つの主題を姿を変えながら繰り返す、変奏曲形式を学ぶ回。旋法やリズムが変わっても、和音の役割の骨組みは保たれ続けることを体感する。",
        "points": [
            "変奏曲形式(Theme and Variations) = 1つの主題を、姿を変えながら繰り返す形式",
            "旋法を変える(長調⇄短調)、リズムを変える、旋律を飾り付けるなど、変化のさせ方は様々",
            "姿が変わっても、トニック・サブドミナント・ドミナントという和音の役割の骨組みは保たれる",
            "モーツァルトの「きらきら星変奏曲」が代表例。ベートーヴェンも生涯多くの変奏曲を作曲した",
        ],
    },
    {
        "num": 25,
        "dir": "day25_対位法入門",
        "title": "対位法入門",
        "desc": "Phase6「作曲の基礎知識」の最初の回。和音を縦の積み重ねとして見る発想から離れ、旋律同士を横に組み合わせる対位法の考え方を学ぶ。",
        "points": [
            "対位法(Counterpoint) = 独立して歌える複数の旋律を横に組み合わせる技術。和音中心の発想はホモフォニー",
            "完全5度・完全8度を保ったまま同じ方向に動く並行(Parallel Motion)は声部の独立性を失わせる",
            "互いに逆方向へ動く反行(Contrary Motion)は独立性を保ちながら心地よく響く",
            "バッハのフーガから現代のカウンターメロディーまで、対位法の考え方は受け継がれている",
        ],
    },
    {
        "num": 26,
        "dir": "day26_非和声音",
        "title": "非和声音",
        "desc": "旋律に表情を与える3種類の非和声音、経過音・刺繍音・掛留音を学ぶ回。和音に含まれない音がどう旋律を歌わせているかを体感する。",
        "points": [
            "非和声音(Non-Chord Tone) = その瞬間の和音には含まれない旋律の音",
            "経過音(Passing Tone) = 和音の音と和音の音の間を隣の音でなめらかにつなぐ",
            "刺繍音(Neighbor Tone) = 和音の音から隣へ寄り道して、また同じ音へ戻る",
            "掛留音(Suspension) = 前の和音の音をあえて伸ばして次の和音とぶつけ、隣の音へ下がって解決する",
        ],
    },
    {
        "num": 27,
        "dir": "day27_コード進行のパターン",
        "title": "コード進行のパターン",
        "desc": "ジャンルを問わず使われる定番のコード進行を学ぶ回。I-V-vi-IV、50年代進行、ジャズのツーファイブワン、パッヘルベルのカノンまで。",
        "points": [
            "I-V-vi-IV = ジャンルを問わず使われる王道進行(Day17の代理和音の応用)",
            "I-vi-IV-V = 50年代のポップス・ドゥーワップでよく使われた進行",
            "ii-V-I(ツーファイブワン) = ジャズの基本進行。機能和声のS-D-Tをそのまま表す",
            "パッヘルベルのカノンの8和音進行は、何百年経った今も数え切れないポップスで使われている",
        ],
    },
    {
        "num": 28,
        "dir": "day28_モーダルインターチェンジ",
        "title": "モーダルインターチェンジ",
        "desc": "Phase6最終回。Day19の借用和音の考え方を広げ、フラット7番目の和音とナポリの和音という、さらに2つの色を手に入れる。",
        "points": [
            "モーダルインターチェンジ(Modal Interchange) = 借用和音の考え方を広げた呼び方",
            "♭VII → I は、ロックやポップスでよく使われる開放的な着地パターン",
            "ナポリの和音(Neapolitan Chord、♭II) = ドミナントの直前に置かれ、劇的な色を加える借用和音",
            "調そのものは変えず、和音の色だけを変える技法。転調(Day20)とは別物",
        ],
    },
    {
        "num": 29,
        "dir": "day29_月光を読み解く",
        "title": "実践2: 月光を読み解く",
        "desc": "Day23の続き。月光ソナタ第一楽章を、ベートーヴェン自身の演奏指示「センツァ・ソルディーノ」の視点も交えて、あらためて読み解く。",
        "points": [
            "嬰ハ短調のトニックと、あえて短調のまま提示される第二主題(嬰ト短調)を再確認",
            "「センツァ・ソルディーノ」= ダンパーペダルを踏みっぱなしにする指示。響きが重なり合う霧のような質感を狙ったもの",
            "有名な三連符の伴奏は、これまで学んだ三和音・七の和音を分散させただけの形",
            "絶対音感を活かせば、あの三連符の中の和音を1つずつ聴き分けられる",
        ],
    },
    {
        "num": 30,
        "dir": "day30_悲愴を読み解く",
        "title": "実践3: 悲愴を読み解く/総まとめ",
        "desc": "最終回。Day14の続きとして悲愴ソナタのアレグロを読み解き、月光との対比を通して、30日間の学びを締めくくる。",
        "points": [
            "悲愴のアレグロもソナタ形式。第二主題は変ホ短調の翳りを経てから変ホ長調へ明るさを取り戻す",
            "月光の第二主題は短調のまま貫くのに対し、悲愴は最終的に明るさへたどり着くという対照的な結末",
            "Day1の「音は空気の振動」から始まり、音程・音階・和音・機能和声・拍子・楽曲構造・作曲技法まで積み上げてきた30日間の総まとめ",
            "演奏・作曲・鑑賞のすべてに、この講座で得た「言葉にできる耳」を役立てていく",
        ],
    },
]

# curriculum.md のPhase構成と対応させる。目次ページでこの単位ごとに見出しを出す。
PHASES = [
    (1, 7, "Phase 1", "基礎 ― 音・音程・音階"),
    (8, 14, "Phase 2", "和音の基礎"),
    (15, 16, "Phase 3", "リズムと拍子"),
    (17, 20, "Phase 4", "機能和声と転調"),
    (21, 24, "Phase 5", "楽曲の構造"),
    (25, 28, "Phase 6", "作曲の基礎知識"),
    (29, 30, "Phase 7", "総合実践"),
]

# 番号付きのDay1〜30とは別に、リクエストに応じて作る単発の「おまけ回」。
# id は web/bonusXX.html のファイル名や urls.txt のキーにそのまま使われる。
BONUS = [
    {
        "id": "bonus01",
        "dir": "bonus01_エンドレスレイン",
        "title": "エンドレスレインを読み解く",
        "desc": "おまけの回。X JAPANの名曲を、実際のシ長調の響きで、これまで学んだ理論(転回形・対位法・転調)を使って読み解く。",
        "points": [
            "実際のキーはシ長調(ギターの譜面はハ長調のコードフォームで書かれることが多いが、半音下げチューニングのため実音は半音下がる)",
            "Aメロは属和音が第一転回形で現れ、低音がなめらかに一歩下がる",
            "サビは上の和音を保ったまま低音だけが階段状に下りていく、対位法的なベースライン",
            "間奏前にシ長調からソ長調へ転調。近親調ではない大胆な転調だが、共通音(シ)が橋渡しをしている",
        ],
    },
    {
        "id": "bonus02",
        "dir": "bonus02_耳のリセットドリル",
        "title": "耳のリセットドリル",
        "desc": "おまけの回。黒鍵の多い調(ロ長調など)を耳コピーしたあとに聴く、実用的なリセット用ドリル。とにかくたくさんの音を鳴らす回。",
        "points": [
            "ハ長調の主和音を基準点に固定してから、半音階を1音ずつ名前付きで確認する",
            "同じ半音階を、今度は名前を言わずに下りながら、自分で当てる自己テスト",
            "ドを基準に、音階の各音との距離を1つずつ確かめ直す",
            "ロ長調とハ長調の主和音を交互に聴き比べ、最後はハ長調のカデンツで締めくくる",
        ],
    },
]

# 自転車での聞き流し用に、Day5話ぶんを1本の音声にまとめた連続再生モード。
# 実体は tools/build_playlist.py で playlists/ 以下に生成する(通常回より低ビットレート)。
PLAYLISTS = [
    {"id": "playlist01", "dir": "playlist01_day01-05", "title": "連続再生: Day1〜5", "days": [1, 2, 3, 4, 5]},
    {"id": "playlist02", "dir": "playlist02_day06-10", "title": "連続再生: Day6〜10", "days": [6, 7, 8, 9, 10]},
    {"id": "playlist03", "dir": "playlist03_day11-15", "title": "連続再生: Day11〜15", "days": [11, 12, 13, 14, 15]},
    {"id": "playlist04", "dir": "playlist04_day16-20", "title": "連続再生: Day16〜20", "days": [16, 17, 18, 19, 20]},
    {"id": "playlist05", "dir": "playlist05_day21-25", "title": "連続再生: Day21〜25", "days": [21, 22, 23, 24, 25]},
    {"id": "playlist06", "dir": "playlist06_day26-30", "title": "連続再生: Day26〜30", "days": [26, 27, 28, 29, 30]},
]


def note_marker_to_text(line):
    stripped = line.strip()
    m = re.match(r'^\[TONE:([^\]]+)\]$', stripped)
    if m:
        return "♪ " + " · ".join(n.strip() for n in m.group(1).split(","))
    b = re.match(r'^\[BEAT:([^\]]+)\]$', stripped)
    if b:
        return "♩ " + " · ".join(n.strip() for n in b.group(1).split(","))
    return None


EN_DISPLAY_PATTERN = re.compile(r'\{\{EN:([^}]+)\}\}')


def load_transcript_html(day_dir):
    script_path = os.path.join(BASE, "days", day_dir, "script.md")
    with open(script_path, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f]
    parts = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^\[PAUSE:[\d.]+\]$', stripped):
            continue
        tone = note_marker_to_text(stripped)
        if tone:
            parts.append(f'<p class="tone-line">{html.escape(tone)}</p>')
        else:
            stripped = EN_DISPLAY_PATTERN.sub(lambda m: f" ({m.group(1)})", stripped)
            parts.append(f"<p>{html.escape(stripped)}</p>")
    return "\n".join(parts)


def audio_data_uri(day_dir):
    audio_path = os.path.join(BASE, "days", day_dir, "audio.m4a")
    with open(audio_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:audio/mp4;base64,{b64}"


CSS = """
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #171310;
    --surface: #211c17;
    --surface-2: #29231d;
    --text: #ece6da;
    --text-muted: #a99d8a;
    --accent: #d97a5e;
    --accent-ink: #1c110c;
    --brass: #d9b568;
    --hairline: rgba(236, 230, 218, 0.14);
  }
}
:root[data-theme="dark"] {
  --bg: #171310;
  --surface: #211c17;
  --surface-2: #29231d;
  --text: #ece6da;
  --text-muted: #a99d8a;
  --accent: #d97a5e;
  --accent-ink: #1c110c;
  --brass: #d9b568;
  --hairline: rgba(236, 230, 218, 0.14);
}
:root {
  --bg: #e9e2d2;
  --surface: #f8f4e9;
  --surface-2: #f1ead9;
  --text: #2a241c;
  --text-muted: #6b6153;
  --accent: #8a3324;
  --accent-ink: #fbeee9;
  --brass: #8a6a1f;
  --hairline: rgba(42, 36, 28, 0.13);

  --serif: "Hiragino Mincho ProN", "Yu Mincho", "Noto Serif JP", ui-serif, serif;
  --sans: -apple-system, BlinkMacSystemFont, "Hiragino Kaku Gothic ProN", "Yu Gothic", "Noto Sans JP", sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, monospace;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--accent); }
.wrap {
  max-width: 560px;
  margin: 0 auto;
  padding: 2.5rem 1.25rem calc(6.5rem + env(safe-area-inset-bottom));
}
.eyebrow {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-family: var(--mono);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 1.1rem;
}
.eyebrow a { color: var(--text-muted); text-decoration: none; border-bottom: 1px solid var(--hairline); }
.eyebrow a:hover { color: var(--accent); border-color: var(--accent); }
.head {
  display: flex;
  align-items: baseline;
  gap: 0.9rem;
  margin-bottom: 0.6rem;
}
.day-num {
  font-family: var(--serif);
  font-size: 2.6rem;
  font-weight: 600;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
h1 {
  font-family: var(--serif);
  font-weight: 600;
  font-size: 1.7rem;
  margin: 0;
  text-wrap: balance;
}
.desc {
  color: var(--text-muted);
  font-size: 0.98rem;
  margin: 0.9rem 0 1.8rem;
  text-wrap: pretty;
}
.player {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 20;
  background: var(--surface);
  border-top: 1px solid var(--hairline);
  box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.12);
  padding: 0.9rem 1.25rem calc(0.9rem + env(safe-area-inset-bottom));
}
.player-inner {
  max-width: 560px;
  margin: 0 auto;
}
.player-row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.player audio {
  flex: 1;
  min-width: 0;
  display: block;
}
.rewind-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  flex-shrink: 0;
  background: var(--surface-2);
  border: 1px solid var(--hairline);
  border-radius: 999px;
  padding: 0.45rem 0.7rem;
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.02em;
  color: var(--text);
  cursor: pointer;
}
.rewind-btn:hover { border-color: var(--accent); color: var(--accent); }
.rewind-btn:active { transform: scale(0.95); }
.rewind-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.rewind-btn svg { width: 15px; height: 15px; flex-shrink: 0; }
.quiz-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
  background: none;
  border: none;
  padding: 0;
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.02em;
  color: var(--brass);
  cursor: pointer;
}
.quiz-btn:hover { color: var(--accent); }
.quiz-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.quiz-btn svg { width: 11px; height: 11px; flex-shrink: 0; }
.duration-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-top: 0.55rem;
  letter-spacing: 0.03em;
}
h2 {
  font-family: var(--serif);
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0 0 0.8rem;
}
.points {
  list-style: none;
  margin: 0 0 2.2rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.points li {
  position: relative;
  padding-left: 1.3rem;
  font-size: 0.94rem;
  color: var(--text);
}
.points li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brass);
}
figure.diagram {
  margin: 0 0 2.2rem;
}
figure.diagram svg {
  display: block;
  width: 100%;
  height: auto;
}
figure.diagram figcaption {
  margin-top: 0.9rem;
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--text-muted);
  text-align: center;
}
details {
  border-top: 1px solid var(--hairline);
  padding-top: 1.1rem;
  margin-bottom: 2.2rem;
}
summary {
  cursor: pointer;
  font-family: var(--serif);
  font-size: 1.02rem;
  font-weight: 600;
  color: var(--text);
}
summary::marker { color: var(--brass); }
.transcript {
  margin-top: 1.2rem;
  font-size: 0.92rem;
  color: var(--text-muted);
  max-width: 65ch;
}
.transcript p { margin: 0 0 0.9rem; }
.tone-line {
  color: var(--brass);
  font-family: var(--mono);
  font-size: 0.82rem;
  letter-spacing: 0.02em;
}
nav.pager {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid var(--hairline);
  padding-top: 1.4rem;
}
nav.pager a {
  text-decoration: none;
  color: var(--text);
  font-size: 0.88rem;
  border: 1px solid var(--hairline);
  border-radius: 10px;
  padding: 0.6rem 0.9rem;
  flex: 1;
}
nav.pager a.disabled {
  color: var(--text-muted);
  pointer-events: none;
  opacity: 0.5;
}
nav.pager .label {
  display: block;
  font-family: var(--mono);
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 0.2rem;
}
nav.pager a:last-child { text-align: right; }
"""


def load_quiz_mark(day_dir):
    marks_path = os.path.join(BASE, "days", day_dir, "audio.marks.json")
    if not os.path.exists(marks_path):
        return None
    with open(marks_path, encoding="utf-8") as f:
        marks = json.load(f)
    return marks.get("quiz")


def format_mmss(seconds):
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def render_day_html(day, prev_url, next_url, index_url):
    audio_uri = audio_data_uri(day["dir"])
    transcript_html = load_transcript_html(day["dir"])
    points_html = "\n".join(f"<li>{html.escape(p)}</li>" for p in day["points"])
    quiz_seconds = load_quiz_mark(day["dir"])
    quiz_btn_html = (
        f'''<button type="button" class="quiz-btn" aria-label="聴き取り練習へジャンプ" onclick="var a=document.getElementById('player-audio');a.currentTime={quiz_seconds};">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M5 4l8 8-8 8V4z"/><path d="M13 4l8 8-8 8V4z"/></svg>
        <span>クイズへ {format_mmss(quiz_seconds)}</span>
      </button>'''
        if quiz_seconds is not None else ""
    )

    prev_html = (
        f'<a href="{prev_url}"><span class="label">← 前回</span>Day{day["num"]-1}</a>'
        if prev_url else '<a class="disabled"><span class="label">← 前回</span>—</a>'
    )
    is_final_day = day["num"] == DAYS[-1]["num"]
    if next_url:
        next_html = f'<a href="{next_url}"><span class="label">次回 →</span>Day{day["num"]+1}</a>'
    elif is_final_day:
        next_html = '<a class="disabled"><span class="label">全30回</span>完走</a>'
    else:
        next_html = '<a class="disabled"><span class="label">次回 →</span>準備中</a>'
    index_link = f'<a href="{index_url}">全体の目次</a>' if index_url else "<span>全体の目次</span>"
    diagram_html = day.get("diagram", "")
    diagram_section = f'<h2>図解</h2>\n{diagram_html}\n' if diagram_html else ""

    return f"""<title>{SERIES_TITLE} Day{day["num"]} — {html.escape(day["title"])}</title>
<style>{CSS}</style>
<div class="wrap">
  <div class="eyebrow">
    <span>{SERIES_TITLE} · {SERIES_TOTAL_HINT}</span>
    {index_link}
  </div>
  <div class="head">
    <span class="day-num">{day["num"]:02d}</span>
    <h1>{html.escape(day["title"])}</h1>
  </div>
  <p class="desc">{html.escape(day["desc"])}</p>

  <h2>この回のポイント</h2>
  <ul class="points">
    {points_html}
  </ul>

  {diagram_section}
  <details>
    <summary>台本を読む(テキスト版)</summary>
    <div class="transcript">
      {transcript_html}
    </div>
  </details>

  <nav class="pager">
    {prev_html}
    {next_html}
  </nav>
</div>

<div class="player">
  <div class="player-inner">
    <div class="player-row">
      <button type="button" class="rewind-btn" aria-label="10秒戻る" onclick="var a=document.getElementById('player-audio');a.currentTime=Math.max(0,a.currentTime-10);">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><polyline points="3 4 3 9 8 9"/></svg>
        <span>10s</span>
      </button>
      <audio id="player-audio" controls preload="none" src="{audio_uri}"></audio>
    </div>
    <div class="duration-row">
      <span>自転車移動でも聴けるように、耳だけで完結する内容です</span>
      {quiz_btn_html}
    </div>
  </div>
</div>
"""


def render_bonus_html(entry, index_url):
    audio_uri = audio_data_uri(entry["dir"])
    transcript_html = load_transcript_html(entry["dir"])
    points_html = "\n".join(f"<li>{html.escape(p)}</li>" for p in entry["points"])
    quiz_seconds = load_quiz_mark(entry["dir"])
    quiz_btn_html = (
        f'''<button type="button" class="quiz-btn" aria-label="聴き取り練習へジャンプ" onclick="var a=document.getElementById('player-audio');a.currentTime={quiz_seconds};">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M5 4l8 8-8 8V4z"/><path d="M13 4l8 8-8 8V4z"/></svg>
        <span>クイズへ {format_mmss(quiz_seconds)}</span>
      </button>'''
        if quiz_seconds is not None else ""
    )
    index_link = f'<a href="{index_url}">全体の目次</a>' if index_url else "<span>全体の目次</span>"
    diagram_html = entry.get("diagram", "")
    diagram_section = f'<h2>図解</h2>\n{diagram_html}\n' if diagram_html else ""

    return f"""<title>{SERIES_TITLE} おまけ — {html.escape(entry["title"])}</title>
<style>{CSS}</style>
<div class="wrap">
  <div class="eyebrow">
    <span>{SERIES_TITLE} · おまけの回</span>
    {index_link}
  </div>
  <div class="head">
    <span class="day-num">EX</span>
    <h1>{html.escape(entry["title"])}</h1>
  </div>
  <p class="desc">{html.escape(entry["desc"])}</p>

  <h2>この回のポイント</h2>
  <ul class="points">
    {points_html}
  </ul>

  {diagram_section}
  <details>
    <summary>台本を読む(テキスト版)</summary>
    <div class="transcript">
      {transcript_html}
    </div>
  </details>

  <nav class="pager">
    <a href="{index_url}"><span class="label">← 戻る</span>全体の目次</a>
    <a class="disabled"><span class="label">おまけ</span>単発回</a>
  </nav>
</div>

<div class="player">
  <div class="player-inner">
    <div class="player-row">
      <button type="button" class="rewind-btn" aria-label="10秒戻る" onclick="var a=document.getElementById('player-audio');a.currentTime=Math.max(0,a.currentTime-10);">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><polyline points="3 4 3 9 8 9"/></svg>
        <span>10s</span>
      </button>
      <audio id="player-audio" controls preload="none" src="{audio_uri}"></audio>
    </div>
    <div class="duration-row">
      <span>自転車移動でも聴けるように、耳だけで完結する内容です</span>
      {quiz_btn_html}
    </div>
  </div>
</div>
"""


def playlist_audio_data_uri(entry):
    audio_path = os.path.join(PLAYLISTS_DIR, entry["dir"], "audio.m4a")
    with open(audio_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:audio/mp4;base64,{b64}"


def load_playlist_marks(entry):
    marks_path = os.path.join(PLAYLISTS_DIR, entry["dir"], "audio.marks.json")
    if not os.path.exists(marks_path):
        return {}
    with open(marks_path, encoding="utf-8") as f:
        return json.load(f)


def render_playlist_html(entry, day_urls, index_url):
    audio_uri = playlist_audio_data_uri(entry)
    marks = load_playlist_marks(entry)
    days_by_num = {d["num"]: d for d in DAYS}

    rows = []
    for num in entry["days"]:
        day = days_by_num[num]
        seconds = marks.get(f"day{num:02d}")
        jump_attr = (
            f"onclick=\"var a=document.getElementById('player-audio');a.currentTime={seconds};a.play();\""
            if seconds is not None else "disabled"
        )
        time_label = format_mmss(seconds) if seconds is not None else "--:--"
        day_url = day_urls.get(num)
        detail_link = (
            f'<a href="{day_url}" class="playlist-detail">詳細</a>' if day_url else ""
        )
        rows.append(f"""
        <div class="playlist-row">
          <button type="button" class="playlist-jump" {jump_attr}>
            <span class="playlist-jump-num">{num:02d}</span>
            <span class="playlist-jump-body">
              <span class="playlist-jump-title">{html.escape(day["title"])}</span>
              <span class="playlist-jump-time">{time_label}〜</span>
            </span>
          </button>
          {detail_link}
        </div>""")
    rows_html = "\n".join(rows)
    index_link = f'<a href="{index_url}">全体の目次</a>' if index_url else "<span>全体の目次</span>"

    return f"""<title>{SERIES_TITLE} 連続再生 — {html.escape(entry["title"])}</title>
<style>{CSS}
.playlist-list {{ display: flex; flex-direction: column; }}
.playlist-row {{
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.85rem 0;
  border-top: 1px solid var(--hairline);
}}
.playlist-row:first-child {{ border-top: none; }}
.playlist-jump {{
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.9rem;
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  color: var(--text);
}}
.playlist-jump:disabled {{ opacity: 0.4; cursor: default; }}
.playlist-jump-num {{
  font-family: var(--serif);
  font-size: 1.3rem;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  width: 2rem;
  flex-shrink: 0;
}}
.playlist-jump-body {{ display: flex; flex-direction: column; }}
.playlist-jump-title {{ font-family: var(--serif); font-weight: 600; font-size: 0.98rem; }}
.playlist-jump-time {{ font-family: var(--mono); font-size: 0.74rem; color: var(--text-muted); margin-top: 0.15rem; }}
.playlist-detail {{
  flex-shrink: 0;
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-muted);
  text-decoration: none;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
}}
.playlist-detail:hover {{ color: var(--accent); border-color: var(--accent); }}
</style>
<div class="wrap">
  <div class="eyebrow">
    <span>{SERIES_TITLE} · 連続再生モード</span>
    {index_link}
  </div>
  <div class="head">
    <span class="day-num">▶</span>
    <h1>{html.escape(entry["title"])}</h1>
  </div>
  <p class="desc">自転車での聞き流し用に、5話ぶんを1本につなげた音声です。曲名をタップすると、その回の頭から再生します。</p>

  <div class="playlist-list">
    {rows_html}
  </div>
</div>

<div class="player">
  <div class="player-inner">
    <div class="player-row">
      <button type="button" class="rewind-btn" aria-label="10秒戻る" onclick="var a=document.getElementById('player-audio');a.currentTime=Math.max(0,a.currentTime-10);">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><polyline points="3 4 3 9 8 9"/></svg>
        <span>10s</span>
      </button>
      <audio id="player-audio" controls preload="none" src="{audio_uri}"></audio>
    </div>
    <div class="duration-row">
      <span>5話連続。各Dayの間に短いアナウンスが入ります</span>
    </div>
  </div>
</div>
"""


def render_index_html(day_urls, bonus_urls, playlist_urls):
    days_by_num = {day["num"]: day for day in DAYS}
    groups_html = []
    for start, end, phase_label, phase_title in PHASES:
        phase_days = [days_by_num[n] for n in range(start, end + 1) if n in days_by_num]
        if not phase_days:
            continue
        rows = []
        for day in phase_days:
            url = day_urls.get(day["num"])
            href = url if url else "#"
            disabled = "" if url else ' style="opacity:.45; pointer-events:none;"'
            rows.append(f"""
        <a class="row" href="{href}"{disabled}>
          <span class="row-num">{day["num"]:02d}</span>
          <span class="row-body">
            <span class="row-title">{html.escape(day["title"])}</span>
            <span class="row-desc">{html.escape(day["desc"])}</span>
          </span>
        </a>""")
        groups_html.append(f"""
    <section class="phase-group">
      <h2 class="phase-heading"><span class="phase-label">{html.escape(phase_label)}</span>{html.escape(phase_title)}</h2>
      <div class="phase-rows">
        {"".join(rows)}
      </div>
    </section>""")
    groups_html_joined = "\n".join(groups_html)

    bonus_rows = []
    for entry in BONUS:
        url = bonus_urls.get(entry["id"])
        href = url if url else "#"
        disabled = "" if url else ' style="opacity:.45; pointer-events:none;"'
        bonus_rows.append(f"""
        <a class="row" href="{href}"{disabled}>
          <span class="row-num">EX</span>
          <span class="row-body">
            <span class="row-title">{html.escape(entry["title"])}</span>
            <span class="row-desc">{html.escape(entry["desc"])}</span>
          </span>
        </a>""")
    bonus_section = ""
    if bonus_rows:
        bonus_section = f"""
    <section class="phase-group">
      <h2 class="phase-heading"><span class="phase-label">おまけ</span>単発のリクエスト回</h2>
      <div class="phase-rows">
        {"".join(bonus_rows)}
      </div>
    </section>"""

    playlist_rows = []
    for entry in PLAYLISTS:
        url = playlist_urls.get(entry["id"])
        href = url if url else "#"
        disabled = "" if url else ' style="opacity:.45; pointer-events:none;"'
        day_range = f"Day{entry['days'][0]}〜{entry['days'][-1]}"
        playlist_rows.append(f"""
        <a class="row" href="{href}"{disabled}>
          <span class="row-num">▶</span>
          <span class="row-body">
            <span class="row-title">{html.escape(entry["title"])}</span>
            <span class="row-desc">{day_range}を1本につなげた、自転車での聞き流し用の連続再生版</span>
          </span>
        </a>""")
    playlist_section = ""
    if playlist_rows:
        playlist_section = f"""
    <section class="phase-group">
      <h2 class="phase-heading"><span class="phase-label">連続再生</span>5話ずつのまとめ聞き</h2>
      <div class="phase-rows">
        {"".join(playlist_rows)}
      </div>
    </section>"""

    return f"""<title>{SERIES_TITLE} — 目次</title>
<style>{CSS}
.phase-group {{ margin-bottom: 2.4rem; }}
.phase-group:last-child {{ margin-bottom: 0; }}
.phase-heading {{
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  font-family: var(--serif);
  font-size: 1.02rem;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 0.4rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--hairline);
}}
.phase-label {{
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 400;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent);
  flex-shrink: 0;
}}
.phase-rows {{ display: flex; flex-direction: column; }}
.row {{
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  padding: 1rem 0;
  border-top: 1px solid var(--hairline);
  text-decoration: none;
  color: var(--text);
}}
.phase-rows .row:first-child {{ border-top: none; }}
.row-num {{
  font-family: var(--serif);
  font-size: 1.6rem;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  width: 2.2rem;
  flex-shrink: 0;
}}
.row-title {{ display:block; font-family: var(--serif); font-weight:600; font-size:1.05rem; margin-bottom:0.25rem; }}
.row-desc {{ display:block; color: var(--text-muted); font-size: 0.86rem; }}
</style>
<div class="wrap">
  <div class="eyebrow"><span>{SERIES_TITLE} · {SERIES_TOTAL_HINT}</span></div>
  <div class="head" style="margin-bottom:0.3rem;">
    <h1 style="font-size:1.9rem;">目次</h1>
  </div>
  <p class="desc">音楽理論をゼロから学ぶ、耳で聴くだけの講座です。Day1から順番に聴いてください。</p>
  {groups_html_joined}
  {playlist_section}
  {bonus_section}
</div>
"""


def main():
    os.makedirs(WEB_DIR, exist_ok=True)
    urls_path = os.path.join(WEB_DIR, "urls.txt")
    known_urls = {}
    if os.path.exists(urls_path):
        with open(urls_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                known_urls[k.strip()] = v.strip()

    index_url = known_urls.get("index")
    day_urls = {int(k[3:]): v for k, v in known_urls.items() if k.startswith("day")}
    bonus_urls = {k: v for k, v in known_urls.items() if k.startswith("bonus")}
    playlist_urls = {k: v for k, v in known_urls.items() if k.startswith("playlist")}

    for i, day in enumerate(DAYS):
        prev_url = known_urls.get(f"day{DAYS[i-1]['num']:02d}") if i > 0 else None
        next_url = known_urls.get(f"day{DAYS[i+1]['num']:02d}") if i < len(DAYS) - 1 else None
        out_path = os.path.join(WEB_DIR, f"day{day['num']:02d}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(render_day_html(day, prev_url, next_url, index_url))
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"wrote {out_path} ({size_mb:.2f} MB)")

    for entry in BONUS:
        out_path = os.path.join(WEB_DIR, f"{entry['id']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(render_bonus_html(entry, index_url))
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"wrote {out_path} ({size_mb:.2f} MB)")

    for entry in PLAYLISTS:
        out_path = os.path.join(WEB_DIR, f"{entry['id']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(render_playlist_html(entry, day_urls, index_url))
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"wrote {out_path} ({size_mb:.2f} MB)")

    index_out = os.path.join(WEB_DIR, "index.html")
    with open(index_out, "w", encoding="utf-8") as f:
        f.write(render_index_html(day_urls, bonus_urls, playlist_urls))
    print(f"wrote {index_out}")


if __name__ == "__main__":
    main()
