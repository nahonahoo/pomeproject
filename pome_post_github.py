"""
ポメラニアン教 X投稿システム - GitHub Actions版
neta_list.txt からネタを読み込み、Anthropic APIで投稿文を生成してGmailで送信する。
"""

import os
import csv
import json
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anthropic

# ── デバッグ: neta_list.txt の内容を表示 ─────────────────────────────
_debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'neta_list.txt')
print(f"=== DEBUG: neta_list.txt の場所: {_debug_path} ===")
try:
    with open(_debug_path, 'r', encoding='utf-8') as _f:
        print(_f.read())
except Exception as _e:
    print(f"読み込みエラー: {_e}")
print("=== DEBUG END ===\n")

# ── 設定 ─────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
NETA_LIST     = os.path.join(BASE_DIR, 'neta_list.txt')
NETA_DATABASE = os.path.join(BASE_DIR, 'neta_database.csv')

AMAZON_ID         = os.environ.get('AMAZON_ID', 'wgenjp-22')
ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
GMAIL_USER        = os.environ['GMAIL_USER']
GMAIL_APP_PASSWORD= os.environ['GMAIL_APP_PASSWORD']
GMAIL_TO          = os.environ['GMAIL_TO']

MODEL = 'claude-opus-4-6'

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── Claude呼び出し ────────────────────────────────────────────────────
def ask_claude(prompt: str) -> str:
    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        return stream.get_final_message().content[0].text.strip()


# ── CSV行数カウント（シリーズ番号用） ────────────────────────────────
def get_post_number() -> int:
    try:
        with open(NETA_DATABASE, 'r', encoding='utf-8') as f:
            return sum(1 for _ in csv.reader(f)) - 1  # ヘッダー除く
    except Exception:
        return 0


# ── neta_database.csv から使用済みタイトルを取得 ─────────────────────
def get_used_titles() -> set:
    """neta_database.csv に記録済みのネタタイトル一覧を返す。"""
    used = set()
    try:
        with open(NETA_DATABASE, 'r', encoding='utf-8') as f:
            for row in csv.reader(f):
                if len(row) >= 3:
                    used.add(row[2].strip())  # 3列目: ネタタイトル
    except FileNotFoundError:
        pass
    return used


# ── neta_list.txt から未使用ネタを取得 ──────────────────────────────
def load_next_neta() -> dict | None:
    """
    neta_list.txt の行フォーマット: ネタタイトル|ネタ元|ジャンル
    neta_database.csv に未記録の最初の行を返す。済マークは付けない。
    """
    used_titles = get_used_titles()
    print(f"    使用済みタイトル数: {len(used_titles)}")

    with open(NETA_LIST, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        stripped = line.rstrip('\n')
        if stripped.startswith('#') or not stripped.strip():
            continue
        parts = stripped.split('|')
        if len(parts) < 2:
            continue
        title = parts[0].strip()
        if title in used_titles:
            continue  # CSV に記録済みはスキップ
        return {
            'title':  title,
            'source': parts[1].strip() if len(parts) > 1 else '',
            'genre':  parts[2].strip() if len(parts) > 2 else '',
        }

    return None


# ── 投稿文生成 ────────────────────────────────────────────────────────
def generate_post(neta: dict, post_number: int) -> str:
    prompt = f"""あなたはポメラニアン教の教祖です。
以下のネタをもとに投稿文を1本書いてください。

【ネタ】
タイトル: {neta['title']}
出典: {neta['source']}
ジャンル: {neta['genre']}

【シリーズ番号】
今回は第{post_number}報／巻／章／回 を使うこと。

【このアカウントのコンセプト】
「世界中のあらゆる作品・文化・歴史にポメラニアンを発見して布教する」

【文体の核心】
文語調の固さとポメのふわふわさのアンマッチがこのアカウントの笑いの源泉。
「鏡に映る己には無関心だが 絵には本気で吠える」のような
固い言い回しの中にポメの間抜けさが滲み出る文体を目指すこと。

【句読点・改行】
句読点はほぼ使わない。
改行で区切る。
一文は短く。体言止め多め。
「〜の」「〜を」「〜へ」「〜に」「〜は」などの接続を省いて
一息でわかる文章にする。

【ポメ動詞の使い方】
ポメる・ポメみ・ポメった・ポメらない・ポメよ・ポメられる・ポメみが深い
などを文語調の文章の中に自然に差し込む。
わざとらしくなく 気づいたら使われている感じが理想。

【構成】
1行目：【遺産発掘 第◯報】など シリーズタグ＋何の話か一発でわかる一文
　　　　タグは内容に合うものを選ぶ
　　　　【遺産発掘 第{post_number}報】歴史・文化ネタ
　　　　【聖典紹介 第{post_number}巻】書籍・文学ネタ
　　　　【布教録 第{post_number}章】布教・信仰ネタ
　　　　【異世界布教 第{post_number}回】アニメ・フィクションネタ
　　　　【緊急布教】特に衝撃的なネタ
2〜4行目：ファクトと教祖の解釈を交互に
最終行：「信仰値 +数字」で締める（数字は年号や関連する数字を使う）

【禁止事項】
ハッシュタグなし
140字を超えない
「〜です」「〜ます」などのですます調禁止
説明的になりすぎない・情報の羅列禁止

【良い投稿の例】
例1：
1777年 ゲインズバラなる画家がポメ2頭を油彩に収めた
完成後 本物のポメが絵に激怒して飛びかかり 別の部屋に移す羽目になった
鏡に映る己には無関心だが 絵には本気で吠える
これほどポメった事案は18世紀に他にない 信仰値 +1777

例2：
チェーホフの短編に登場する小型犬はポメラニアン系とされている
ドストエフスキーもトルストイもポメらなかったがチェーホフはポメた
最も繊細な作家が最も繊細な犬を選んだのは必然である
信仰値 +1899

投稿文のみを出力してください。説明・前置き不要。"""
    return ask_claude(prompt)


# ── 画像プロンプト生成 ────────────────────────────────────────────────
def generate_image_prompt(neta: dict, post_text: str) -> str:
    prompt = f"""以下のポメラニアン教の投稿に合う画像生成用の英語プロンプトを1つ書いてください。

【投稿文】
{post_text}

【元ネタ】
{neta['title']}
ジャンル: {neta['genre']}

【ルール】
- 主役は必ず fluffy Pomeranian dog にすること
- 「ポメが玉座に座っている」は禁止。毎回異なる構図にすること
  構図の例：窓際で本を読んでいる／街角を歩いている／額縁の中に収まっている／
  机の上に座っている／野原を走っている／人物の肩に乗っている など
- ネタの舞台・時代・雰囲気を具体的に反映させること
- ジャンルに応じて以下のスタイルを選ぶこと

ジャンル別スタイル（ネタに合うものを1つ選んで使う）：
- 歴史・美術系   → oil painting style, 18th century, warm candlelight
- アニメ・漫画系  → anime illustration style, soft pastel colors, kawaii
- 神話・伝説系   → watercolor illustration, medieval manuscript style, candlelight, stained glass
- グッズ・おもちゃ系 → product photography style, clean white background, studio lighting
- 切手・記念品系  → vintage stamp illustration, engraving style, ornate border
- 文学・小説系   → 19th century book illustration, sepia tones, ink drawing style

【出力形式】
英語プロンプト1文のみ。説明・ラベル不要。"""
    return ask_claude(prompt)


# ── Amazonアフィリエイトリプライ生成 ──────────────────────────────────
def generate_amazon_reply(neta: dict, post_text: str) -> str:
    prompt = f"""以下のポメラニアン教の投稿ネタに関連するAmazon商品を2点選び、教祖口調のアフィリエイトリプライ文を書いてください。

【投稿文】
{post_text}

【元ネタ】
{neta['title']}

【ルール】
- 教祖口調・文語調
- 各商品に括弧でマニアックなひとことコメントを入れる
- AmazonのURLは https://www.amazon.co.jp/s?k=検索キーワード&tag={AMAZON_ID} の形式で作る
- ハッシュタグなし

リプライ文のみを出力してください。説明不要。"""
    return ask_claude(prompt)


# ── カテゴリ判定 ──────────────────────────────────────────────────────
def detect_category(neta: dict, post_text: str) -> str:
    cats = ['歴史', '神話', '芸術・美術', 'アニメ・映画', '小説・文学', '文化', '科学', 'その他']
    prompt = f"""次のポメラニアン投稿のカテゴリを以下から1つ選び、カテゴリ名のみを出力してください。

カテゴリ: {' / '.join(cats)}

タイトル: {neta['title']}
投稿文: {post_text[:100]}"""
    raw = ask_claude(prompt)
    for c in cats:
        if c in raw:
            return c
    return 'その他'


# ── Gmail送信 ─────────────────────────────────────────────────────────
def send_email(subject: str, body: str) -> None:
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = GMAIL_USER
    msg['To']      = GMAIL_TO
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, GMAIL_TO, msg.as_string())
    print(f"メール送信完了: {GMAIL_TO}")


# ── CSV追記 ───────────────────────────────────────────────────────────
def append_to_csv(date_str: str, category: str, neta: dict,
                  post_text: str, image_prompt: str) -> None:
    write_header = not os.path.exists(NETA_DATABASE)
    with open(NETA_DATABASE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['日付', 'カテゴリ', 'ネタタイトル', 'ネタ元', '投稿文', '画像プロンプト', '使用済み'])
        writer.writerow([
            date_str, category, neta['title'],
            neta['source'], post_text, image_prompt, '使用済み'
        ])


# ── メイン ────────────────────────────────────────────────────────────
def main():
    print("=== ポメラニアン教 GitHub Actions版 起動 ===\n")

    # ネタ読み込み
    print("【1】neta_list.txt からネタ読み込み中...")
    neta = load_next_neta()
    if neta is None:
        print("未使用のネタがありません。neta_list.txt に追記してください。")
        send_email(
            subject="[ポメラニアン教] ネタ切れ警告",
            body="neta_list.txt の未使用ネタがなくなりました。\n追記をお願いします。",
        )
        return
    print(f"    ネタ: {neta['title']} ({neta['genre']})\n")

    # シリーズ番号
    post_number = get_post_number() + 1

    # 投稿文生成
    print(f"【2】投稿文生成中 (第{post_number}報)...")
    post_text = generate_post(neta, post_number)
    char_count = len(post_text)
    print(f"    {post_text}")
    print(f"    ({char_count}文字)\n")

    # 画像プロンプト生成
    print("【3】画像プロンプト生成中...")
    image_prompt = generate_image_prompt(neta, post_text)
    print(f"    {image_prompt[:80]}{'...' if len(image_prompt) > 80 else ''}\n")

    # Amazonリプライ生成
    print("【4】Amazonリプライ生成中...")
    reply_text = generate_amazon_reply(neta, post_text)
    print(f"    {reply_text[:80]}{'...' if len(reply_text) > 80 else ''}\n")

    # カテゴリ判定
    category = detect_category(neta, post_text)

    # CSV追記
    date_str = datetime.now().strftime('%Y-%m-%d')
    append_to_csv(date_str, category, neta, post_text, image_prompt)
    print(f"【5】CSV追記完了: {category}\n")

    # メール送信
    print("【6】Gmail送信中...")
    email_body = f"""■ 投稿文（{char_count}文字）
{post_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 画像プロンプト（Nano Bananaで生成）
{image_prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ リプライ文（Amazon）
{reply_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ ネタ情報
タイトル: {neta['title']}
出典: {neta['source']}
ジャンル: {neta['genre']}
カテゴリ: {category}
生成日: {date_str}
"""
    send_email(
        subject=f"[ポメラニアン教] 第{post_number}報 本日の投稿",
        body=email_body,
    )

    print("\n=== 完了 ===")
    print(f"投稿文:\n{post_text}")


if __name__ == '__main__':
    main()
