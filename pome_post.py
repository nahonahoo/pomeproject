import subprocess
import sys
import json
import csv
import os
import urllib.request
import urllib.parse
from datetime import datetime

# Windows コンソールの文字化け対策
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── パッケージ自動インストール ──────────────────────────────────────
def install(pkg):
    subprocess.check_call(
        [sys.executable, '-m', 'pip', 'install', pkg],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

try:
    from ddgs import DDGS
except ImportError:
    print("Installing ddgs...")
    install('ddgs')
    from ddgs import DDGS

# ── 設定読み込み ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'config.json'), 'r', encoding='utf-8') as f:
    config = json.load(f)

AMAZON_ID = config['amazon_id']

# ── Claude呼び出し ────────────────────────────────────────────────
def ask_claude(prompt):
    result = subprocess.run(
        ['claude', '-p', prompt],
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude コマンドエラー:\n{result.stderr.strip()}")
    return result.stdout.strip()

# ── CSV行数カウント（シリーズ番号用） ────────────────────────────
def get_post_number():
    csv_path = os.path.join(BASE_DIR, 'neta_database.csv')
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in csv.reader(f)) - 1  # ヘッダー除く
    except Exception:
        return 0

# ── 1. Web検索でネタ収集 ──────────────────────────────────────────
def search_topic():
    import random
    queries = [
        'pomeranian painting art',
        'pomeranian anime character',
        'pomeranian novel literature',
        'pomeranian movie film',
        'pomeranian toy figure collectible',
        'pomeranian stamp postage',
        'pomeranian folklore legend',
        'pomeranian manga',
        'pomeranian merchandise goods',
        'famous pomeranian owner history',
        'pomeranian game character',
        'pomeranian craft folk art',
    ]
    query = random.choice(queries)
    print(f"   検索クエリ: {query}")
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    if results:
        r = results[0]
        return {
            'title':  r.get('title', 'ポメラニアン雑学'),
            'body':   r.get('body',  ''),
            'source': r.get('href',  ''),
            'query':  query,
        }
    return {'title': 'ポメラニアンの起源', 'body': 'ポメラニアンはポメラニア地方原産の小型スピッツ犬', 'source': '', 'query': ''}

# ── 2. 投稿文生成 ─────────────────────────────────────────────────
def generate_post(topic, post_number):
    prompt = f"""あなたはポメラニアン教の教祖です。
検索で見つけたネタをもとに投稿文を1本書いてください。

【ネタ】
タイトル: {topic['title']}
内容: {topic['body'][:500]}
検索クエリ: {topic.get('query', '')}

【シリーズ番号】
今回は第{post_number}報／巻／章／回 を使うこと。

【このアカウントのコンセプト】
「世界中のあらゆる作品・文化・歴史にポメラニアンを発見して布教する」
歴史だけでなく以下のジャンル全てからネタを拾う。
- 美術・絵画（ゲインズバラ、フラマン絵画など）
- 歴史上の人物とポメのエピソード（モーツァルト、ニュートンなど）
- 小説・文学（チェーホフ、ロシア文学など）
- 神話・伝説・民族文化
- アニメ・漫画（ギヴン「毛玉」、ヒロアカ「爆豪＝Angry Pomeranian」など）
- 映画・ドラマ（タイタニック、ナニーなど）
- ゲーム
- グッズ・おもちゃ・雑貨（ポメラニアン型のユニークな商品）
- 切手・コイン・記念品
- 現代アート
- 民族工芸・伝統工芸

【ネタの品質基準】
以下を全て満たすネタだけを使うこと。
満たさない場合は投稿文を生成せず、1行目に「NG: 理由」とだけ出力すること。

1. 実在する固有名詞があること
   人名・作品名・商品名・地名・年号のいずれか

2. 出典が明確であること
   美術館所蔵・公式アニメ・実在商品・史実・文献記録

3. 「世界のどこかにポメがいた・ポメが作られた」という発見感があること

NGネタ：
- 出典不明の創作エピソード
- 「かもしれない」レベルの推測
- ポメラニアンが全く関係ない検索結果（魚など）

【良いネタの例】
・ゲインズバラ「Pomeranian Bitch and Puppy」1777年 テート所蔵
・モーツァルトが愛犬ポメ「ピンペル」のためにアリアを作曲
・タイタニック号沈没で生き残った犬3頭のうち2頭がポメラニアン
・アニメ「ギヴン」主人公の愛犬ポメラニアン「毛玉」
・ヒロアカで爆豪がAngry Pomeranianと呼ばれていた
・ポメラニアン柄の切手がドイツで発行された
・江戸時代の根付にスピッツ系の犬を模したものがある

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

良い使い方：
「これほどポメった事案は18世紀に他にない」
「ドストエフスキーもトルストイもポメらなかったがチェーホフはポメた」
「これ以上ポメよな話があるだろうか」
「ポメらない人間など存在しないと余は考える」
「全世界にポメらせた」
「余の信仰は歴史によってポメられている」

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
宗教改革を起こしたマルティン・ルター 著作にはポメラニアン「ベルフェルライン」への深い愛が繰り返し記されている
カトリックには刃向かえど ポメへの愛には抗えなかった
ポメらない人間など存在しないと余は考える
信仰値 +1517

例3：
チェーホフの短編に登場する小型犬はポメラニアン系とされている
ドストエフスキーもトルストイもポメらなかったがチェーホフはポメた
最も繊細な作家が最も繊細な犬を選んだのは必然である
信仰値 +1899

投稿文のみを出力してください。説明・前置き不要。"""
    return ask_claude(prompt)

# ── 3. 画像プロンプト生成 ─────────────────────────────────────────
def generate_image_prompt(topic, post_text):
    prompt = f"""以下のポメラニアン教の投稿に合う画像生成用の英語プロンプトを1つ書いてください。

【投稿文】
{post_text}

【元ネタ】
{topic['title']}
検索クエリ: {topic.get('query', '')}

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

# ── 4. 画像戦略の判定 ────────────────────────────────────────────
def detect_image_strategy(topic, post_text):
    """
    ジャンルに応じて画像取得戦略を返す。
    'wikimedia' : Wikimedia Commonsで検索
    'nano_banana': 画像生成プロンプトのみ保存
    """
    prompt = f"""以下のポメラニアン投稿のジャンルを判定してください。

タイトル: {topic['title']}
検索クエリ: {topic.get('query', '')}
投稿文（冒頭）: {post_text[:120]}

以下のいずれか1語だけを出力してください。

wikimedia   ← 美術・絵画・歴史的人物・歴史的事件・切手・コイン・民族工芸
nano_banana ← アニメ・漫画・ゲーム・グッズ・おもちゃ・現代商品・現代アート"""
    result = ask_claude(prompt).strip().lower()
    if 'nano' in result:
        return 'nano_banana'
    return 'wikimedia'

# ── 6. Wikimedia Commons 画像取得 ────────────────────────────────
ALLOWED_LICENSES = {
    'public domain', 'cc0', 'cc-zero', 'pd', 'pd-old',
    'pd-art', 'pd-us', 'pd-old-70', 'pd-old-100',
}

def _wikimedia_api(params):
    params['format'] = 'json'
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'pome_post/1.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

def _is_free_license(extmetadata):
    """ライセンスがパブリックドメインまたはCC0か確認する"""
    license_raw = (
        extmetadata.get('LicenseShortName', {}).get('value', '') +
        extmetadata.get('License', {}).get('value', '')
    ).lower()
    return any(lic in license_raw for lic in ALLOWED_LICENSES)

def get_wikimedia_image(topic, post_text, save_path):
    """
    投稿ネタからWikimedia Commons画像を検索・取得。
    成功時はsave_pathに保存しメタ情報dictを返す。
    失敗時はNoneを返す。
    """
    # Claudeに英語検索ワードを生成させる
    kw_prompt = f"""以下のポメラニアン投稿のネタに関連するWikimedia Commons画像を検索したい。
最も画像が見つかりやすい英語検索キーワードを1〜3語で提案してください。

ネタ: {topic['title']}
投稿文（冒頭）: {post_text[:100]}

例：
- ゲインズバラのポメ絵画 → Gainsborough Pomeranian
- モーツァルト → Mozart portrait
- タイタニック → Titanic 1912
- ヴィクトリア女王 → Queen Victoria portrait

キーワードのみを出力してください。"""
    search_keyword = ask_claude(kw_prompt).strip().splitlines()[0]
    print(f"    Wikimedia検索ワード: {search_keyword}")

    # 画像ファイル名一覧を検索
    try:
        search_data = _wikimedia_api({
            'action': 'query',
            'list': 'search',
            'srsearch': search_keyword,
            'srnamespace': '6',
            'srlimit': '10',
        })
    except Exception as e:
        print(f"    [警告] Wikimedia検索エラー: {e}")
        return None

    hits = search_data.get('query', {}).get('search', [])
    if not hits:
        print("    [情報] 画像が見つかりませんでした")
        return None

    # ヒットした画像を順に試す
    for hit in hits:
        filename = hit['title']  # "File:xxx.jpg" 形式
        try:
            info_data = _wikimedia_api({
                'action': 'query',
                'titles': filename,
                'prop': 'imageinfo',
                'iiprop': 'url|extmetadata|mediatype',
            })
        except Exception:
            continue

        pages = info_data.get('query', {}).get('pages', {})
        page  = next(iter(pages.values()))
        infos = page.get('imageinfo', [])
        if not infos:
            continue

        info       = infos[0]
        mediatype  = info.get('mediatype', '')
        extmeta    = info.get('extmetadata', {})
        image_url  = info.get('url', '')

        # 画像ファイルのみ対象（SVG・PDF除外）
        if mediatype not in ('BITMAP', 'DRAWING'):
            continue
        if image_url.lower().endswith(('.svg', '.pdf', '.tif', '.tiff')):
            continue

        # ライセンス確認
        if not _is_free_license(extmeta):
            continue

        # ファイル名・説明にポメ関連キーワードが含まれるか確認
        VALID_KEYWORDS = {'pomeranian', 'dog', 'portrait', 'painting', 'historical'}
        fn_lower  = filename.lower()
        desc_lower = extmeta.get('ImageDescription', {}).get('value', '').lower()
        if not any(kw in fn_lower or kw in desc_lower for kw in VALID_KEYWORDS):
            print(f"    [スキップ] 無関係な画像: {filename}")
            continue

        # ダウンロード
        try:
            req = urllib.request.Request(image_url, headers={'User-Agent': 'pome_post/1.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                with open(save_path, 'wb') as f:
                    f.write(r.read())
            license_name = extmeta.get('LicenseShortName', {}).get('value', '不明')
            print(f"    画像取得: {filename}")
            print(f"    ライセンス: {license_name}")
            return {'filename': filename, 'url': image_url, 'license': license_name}
        except Exception as e:
            print(f"    [警告] ダウンロード失敗: {e}")
            continue

    print("    [情報] 利用可能な画像が見つかりませんでした")
    return None

# ── 5. Amazonアフィリエイトリプライ生成 ──────────────────────────
def generate_amazon_reply(topic, post_text):
    prompt = f"""以下のポメラニアン教の投稿ネタに関連するAmazon商品を2点選び、教祖口調のアフィリエイトリプライ文を書いてください。

【投稿文】
{post_text}

【元ネタ】
{topic['title']}

【ルール】
- 教祖口調・文語調
- 各商品に括弧でマニアックなひとことコメントを入れる
- AmazonのURLは https://www.amazon.co.jp/s?k=検索キーワード&tag={AMAZON_ID} の形式で作る
- ハッシュタグなし

リプライ文のみを出力してください。説明不要。"""
    return ask_claude(prompt)

# ── 5. カテゴリ判定 ───────────────────────────────────────────────
def detect_category(topic, post_text):
    cats = ['歴史', '神話', '芸術・美術', 'アニメ・映画', '小説・文学', '文化', '科学', 'その他']
    prompt = f"""次のポメラニアン投稿のカテゴリを以下から1つ選び、カテゴリ名のみを出力してください。

カテゴリ: {' / '.join(cats)}

タイトル: {topic['title']}
投稿文: {post_text[:100]}"""
    raw = ask_claude(prompt)
    for c in cats:
        if c in raw:
            return c
    return 'その他'

# ── メイン ────────────────────────────────────────────────────────
def main():
    print("=== ポメラニアン教 X投稿システム 起動 ===\n")

    now      = datetime.now()
    date_key = now.strftime('%Y%m%d_%H%M%S')
    date_csv = now.strftime('%Y-%m-%d')

    drafts_dir = os.path.join(BASE_DIR, 'drafts', date_key)
    os.makedirs(drafts_dir, exist_ok=True)

    # ── Step 1&2: ネタ収集 → 品質チェック → 投稿文生成（最大5回リトライ）
    post_number = get_post_number() + 1
    post_text = None
    topic = None
    for attempt in range(1, 6):
        print(f"【1】ネタ収集中... (試行 {attempt}/5)")
        topic = search_topic()
        print(f"    取得: {topic['title']}")

        print(f"【2】投稿文生成中 (第{post_number}報)...")
        result = generate_post(topic, post_number)

        if result.startswith("NG:"):
            print(f"    品質NG - {result}")
            print("    再検索します...\n")
            continue

        post_text = result
        char_count = len(post_text)
        print(f"    {post_text}")
        print(f"    ({char_count}文字)\n")
        break

    if post_text is None:
        print("5回試行しましたがNGネタのみでした。処理を中断します。")
        return

    # ── Step 3: 画像プロンプト生成
    print("【3】画像プロンプト生成中...")
    image_prompt = generate_image_prompt(topic, post_text)
    print(f"    {image_prompt[:80]}{'...' if len(image_prompt) > 80 else ''}\n")

    # ── Step 3b: 画像戦略判定 → 取得
    print("【3b】画像取得戦略を判定中...")
    image_strategy = detect_image_strategy(topic, post_text)
    print(f"    戦略: {image_strategy}\n")

    image_meta = None
    image_save_path = os.path.join(drafts_dir, 'image.jpg')
    if image_strategy == 'wikimedia':
        print("【3c】Wikimedia Commons 画像取得中...")
        image_meta = get_wikimedia_image(topic, post_text, image_save_path)
        if image_meta:
            print(f"    image.jpg 保存完了\n")
        else:
            print("    画像なし - Nano Bananaで生成してください\n")
    else:
        print("【3c】アニメ・グッズ系 - Nano Banana用プロンプトを保存\n")

    # ── Step 4: Amazonリプライ生成
    print("【4】Amazonリプライ生成中...")
    reply_text = generate_amazon_reply(topic, post_text)
    print(f"    {reply_text[:80]}{'...' if len(reply_text) > 80 else ''}\n")

    # ── Step 5: ファイル保存
    print("【5】ファイル保存中...")

    def save_txt(name, content):
        path = os.path.join(drafts_dir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    save_txt('投稿本文.txt',     post_text)
    save_txt('画像プロンプト.txt', image_prompt)
    save_txt('リプライ文.txt',    reply_text)
    if not image_meta:
        save_txt('画像なし_NanoBananaで生成.txt', image_prompt)
    print(f"    保存先: drafts/{date_key}/\n")

    # ── Step 6: CSV追記
    print("【6】neta_database.csv に追記中...")
    category = detect_category(topic, post_text)
    csv_path  = os.path.join(BASE_DIR, 'neta_database.csv')
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([
            date_csv, category, topic['title'],
            topic['source'], post_text, image_prompt, '未使用'
        ])
    print(f"    カテゴリ: {category} - 追記完了\n")

    print("=" * 40)
    print("完了！")
    print(f"投稿文:\n{post_text}")
    print(f"\n保存先: drafts/{date_key}/")

if __name__ == '__main__':
    main()
