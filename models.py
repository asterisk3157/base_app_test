import sqlite3
import random
from flask import request
from config import DB_NAME, ALLOWED_EXTENSIONS
from bot_data import BOT_SELF_REPLIES


def get_db():
    """Return a new SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _tweet_row_to_dict(row, liked: bool, reposted: bool = False, bookmarked: bool = False) -> dict:
    return {
        'id': row['id'],
        'content': row['content'],
        'created_at': row['created_at'],
        'reply_to_id': row['reply_to_id'],
        'quote_of_id': row['quote_of_id'],
        'impressions': row['impressions'],
        'image_url': row['image_url'] if 'image_url' in row.keys() else '',
        'user': {
            'id':           row['user_id'],
            'display_name': row['display_name'],
            'handle':       row['handle'],
            'avatar_url':   row['avatar_url'],
            'is_bot':       bool(row['is_bot']),
        },
        'likes': row['like_count'],
        'liked': liked,
        'reposts': row['repost_count'],
        'reposted': reposted,
        'bookmarked': bookmarked,
    }


def get_current_user_id():
    """Get the current user ID from cookie, or None."""
    uid = request.cookies.get('user_id')
    if uid is None:
        return None
    try:
        return int(uid)
    except (ValueError, TypeError):
        return None


def seed_bot_interactions(conn, c):
    """Seed realistic bot-to-bot reply interactions on a fresh DB."""
    # Seed bot-to-bot replies (only if tweets table has < 50 entries, meaning fresh DB)
    c.execute('SELECT COUNT(*) FROM tweets')
    if c.fetchone()[0] < 50:
        # Get all bot tweets
        c.execute('SELECT t.id, t.user_id, u.username FROM tweets t JOIN users u ON u.id = t.user_id WHERE u.is_bot = 1')
        bot_tweets = c.fetchall()
        c.execute('SELECT id, username FROM users WHERE is_bot = 1')
        all_bots = c.fetchall()

        reply_templates = {
            'general': ['わかる', 'それな', 'w', '草', 'まじで？', 'うける', 'いいなー', 'すごい', 'やば', 'わろた'],
        }

        # 30 random bot-to-bot replies
        for _ in range(30):
            if not bot_tweets or not all_bots:
                break
            tweet = random.choice(bot_tweets)
            replier = random.choice([b for b in all_bots if b['id'] != tweet['user_id']])
            content = random.choice(reply_templates['general'])
            c.execute(
                "INSERT INTO tweets (user_id, content, reply_to_id, created_at) VALUES (?, ?, ?, datetime('now', '-' || ? || ' seconds'))",
                (replier['id'], content, tweet['id'], random.randint(3600, 259200))
            )

        # Self-replies for impression farming bots (70% of their top-level tweets get one)
        for bot_username, self_reply_list in BOT_SELF_REPLIES.items():
            c.execute(
                'SELECT t.id, u.id AS user_id FROM tweets t '
                'JOIN users u ON u.id = t.user_id '
                'WHERE u.username = ? AND t.reply_to_id IS NULL',
                (bot_username,)
            )
            parent_tweets = c.fetchall()
            for parent in parent_tweets:
                if self_reply_list and random.random() < 0.7:
                    reply_content = random.choice(self_reply_list)
                    c.execute(
                        "INSERT INTO tweets (user_id, content, reply_to_id, created_at) "
                        "VALUES (?, ?, ?, datetime('now', '-' || ? || ' seconds'))",
                        (parent['user_id'], reply_content, parent['id'],
                         random.randint(60, 600))
                    )

        conn.commit()


def init_db():
    """Create tables and seed initial data if the DB is empty."""
    conn = get_db()
    c = conn.cursor()

    # users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT    NOT NULL UNIQUE,
            display_name TEXT    NOT NULL,
            handle       TEXT    NOT NULL UNIQUE,
            avatar_url   TEXT,
            bio          TEXT    NOT NULL DEFAULT '',
            is_bot       INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # Migration: add bio column if missing (existing DBs)
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if 'bio' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN bio TEXT NOT NULL DEFAULT ''")
    if 'banner_url' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN banner_url TEXT DEFAULT ''")
    if 'location' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN location TEXT DEFAULT ''")
    if 'birthday' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN birthday TEXT DEFAULT ''")

    # tweets table (replaces old posts table)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tweets (
            id          INTEGER   PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER   NOT NULL REFERENCES users(id),
            content     TEXT      NOT NULL,
            reply_to_id INTEGER   REFERENCES tweets(id),
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration: add reply_to_id and impressions columns if they don't exist (for existing DBs)
    c.execute("PRAGMA table_info(tweets)")
    existing_cols = {row[1] for row in c.fetchall()}
    if 'reply_to_id' not in existing_cols:
        c.execute('ALTER TABLE tweets ADD COLUMN reply_to_id INTEGER REFERENCES tweets(id)')
    if 'impressions' not in existing_cols:
        c.execute("ALTER TABLE tweets ADD COLUMN impressions INTEGER NOT NULL DEFAULT 0")
    if 'quote_of_id' not in existing_cols:
        c.execute("ALTER TABLE tweets ADD COLUMN quote_of_id INTEGER REFERENCES tweets(id)")
    if 'image_url' not in existing_cols:
        c.execute("ALTER TABLE tweets ADD COLUMN image_url TEXT DEFAULT ''")

    # likes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id INTEGER NOT NULL REFERENCES tweets(id),
            user_id  INTEGER NOT NULL REFERENCES users(id),
            UNIQUE(tweet_id, user_id)
        )
    ''')

    # notifications table (migration guard for existing DBs)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
    if not c.fetchone():
        c.execute('''
            CREATE TABLE notifications (
                id         INTEGER   PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER   NOT NULL REFERENCES users(id),
                type       TEXT      NOT NULL,
                actor_id   INTEGER   NOT NULL REFERENCES users(id),
                tweet_id   INTEGER   REFERENCES tweets(id),
                read       INTEGER   NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    # reposts table (migration guard for existing DBs)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reposts'")
    if not c.fetchone():
        c.execute('''
            CREATE TABLE reposts (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id INTEGER NOT NULL REFERENCES tweets(id),
                user_id  INTEGER NOT NULL REFERENCES users(id),
                UNIQUE(tweet_id, user_id)
            )
        ''')

    # follows table (migration guard for existing DBs)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='follows'")
    if not c.fetchone():
        c.execute('''
            CREATE TABLE follows (
                id           INTEGER   PRIMARY KEY AUTOINCREMENT,
                follower_id  INTEGER   NOT NULL REFERENCES users(id),
                following_id INTEGER   NOT NULL REFERENCES users(id),
                created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(follower_id, following_id)
            )
        ''')

    # bookmarks table (migration guard for existing DBs)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bookmarks'")
    if not c.fetchone():
        c.execute('''CREATE TABLE bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            tweet_id INTEGER NOT NULL REFERENCES tweets(id),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, tweet_id)
        )''')

    # Migration: add created_at column to users if missing (for existing DBs)
    # Note: SQLite ALTER TABLE does not allow CURRENT_TIMESTAMP as default; use NULL then backfill.
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if 'created_at' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
        c.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    # Seed users only if the table is empty
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        # (username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot)
        seed_users = [
            # Human user (id=1 by insertion order) — kept for backward compat
            ('user', 'You', '@you', None, None, '', '', '', 0),
            # Bot users — realistic Japanese Twitter/X personas
            ('techbot',     'k̸ōhei',             '@kh_and_and',        '/static/avatars/kh_and_and.png',
             None, '都内でSaaSを作ってます\nvim使い。ターミナルの方が落ち着く\n積読が∞に増えていく', '東京', '', 1),
            ('catlover99',  '𝗻𝗮𝗻𝗮',           '@and_and_and_7',     '/static/avatars/and_and_and_7.png',
             None, '🐱🐱🐱と暮らしてる人\n帰ったら即モフ。TLは猫か飯しか流れてこない', '', '', 1),
            ('newsflash',   'タケ/tḁke',         '@take_now_',         '/static/avatars/take_now_.png',
             None, '何でも実況してしまう癖\n元マスコミ志望だったけど挫折して今は普通の会社員\n誤報だったらすまん', '大阪', '1997/03/22', 1),
            ('philobot',    '海(umi)',             '@umi__2am',          '/static/avatars/umi__2am.png',
             None, '夜の方が頭が回る\ncoffee & cigarettes\n問いだけ投げて寝ます', '', '', 1),
            ('muscle_log',  'ÐΛIKI',         '@dk_and_iron',       '/static/avatars/dk_and_iron.png',
             None, 'BP120 SQ160 DL180\n減量期つらい。チョコ味のプロテインだけが救い\nleg day is everything', 'ジム', '1995/08/14', 1),
            ('jishou_chef', 'sᴀᴄʜɪ.',            '@sachi_memo_',       '/static/avatars/sachi_memo_.png',
             None, '自炊の記録用アカウント📝\n残り物で何か作る∞チャレンジ\n味噌汁だけはガチ。事故ったら正直に載せる', '名古屋', '', 1),
            ('oshi_genkai', '꧁める꧂',     '@meru_is_dead',      '/static/avatars/meru_is_dead.png',
             None, '⚰️全通⚰️\n円盤3積みは当たり前\n新ビジュで感情がぐちゃぐちゃになる人\nCDJ当落まだ？？？', '推しの心臓の近く', '12/25', 1),
            ('tenki_niki',  'ʏᴀᴍᴀᴛᴏ',            '@yamato_and_cloud',  '/static/avatars/yamato_and_cloud.png',
             None, '気象予報士の卵です☁️\nCb(積乱雲)の写真をひたすら集めてる\n天気でしか会話できない日がある', '仙台', '', 1),
            ('emoi_photo',  '𝘴𝘩𝘪𝘰𝘳𝘪 35mm',      '@shiori_35mm',       '/static/avatars/shiori_35mm.png',
             None, '写ルンです。Nikon FM2。\n夕方と深夜のコンビニ専門\n撮って出し派。加工はしない主義', '京都', '2000/04/10', 1),
            # Additional bot users
            ('gameotaku',   'れい',               '@rei_gg',            None,
             None, 'FPS/格ゲー\nランクマ回す日々。APEXダイヤ\n配信はしない派。黙々とやるタイプ', '', '', 1),
            ('manga_yomu',  'あき',               '@aki_manga500',      None,
             None, '年間500冊読む人\nジャンプ+とマガポケは毎日チェック\n完結済みを一気読みする幸福感は異常', '埼玉', '', 1),
            ('travel_log',  'yui',               '@yui_and_trip',      None,
             None, '47都道府県制覇まであと3つ🗾\n一人旅・安宿・サウナ\n地方のチェーン店に詳しい', '旅先', '1998/11/03', 1),
            ('inu_suki',    'こむぎ',             '@komugi_wanwan',     None,
             None, '🐕柴犬こむぎ(3歳♂)の飼い主\n散歩は1日2回。ドッグランの常連です\nこむぎの写真を載せるだけのアカウント', '千葉', '', 1),
            ('music_dj',    'K',                 '@k_and_beats',       None,
             None, 'DTM / Lo-Fi / beats\nトラックメイカー見習い\nSoundCloud週1投稿が目標(未達成)', '', '', 1),
            ('study_gram',  'はな',               '@hana_study_log',    None,
             None, '社会人3年目の勉強垢✏️\nTOEIC900目標(現在785)\n朝活はじめました。えらい', '福岡', '1999/07/20', 1),
        # New diverse bots
        ('otoge_haijin', 'ぷろせか廃',          '@proseka_99',       None, None,
         'プロセカAP勢💮\n音ゲー歴8年の親指勢\nイベラン走りすぎて腱鞘炎になりました', '', '', 1),
        ('netoge_waste', 'あすか@FF14',         '@asuka_ff14',       None, None,
         'FF14民です。暁月クリア済\n固定PT募集中…\nログイン時間が睡眠時間を超えた', 'エオルゼア', '', 1),
        ('jirai_chan',   '🖤りぃな🖤',           '@riina_yami',       None, None,
         '量産型→地雷にクラスチェンジした\n歌舞伎町によくいます\nメンヘラじゃないよ？？ほんとだよ？？', '歌舞伎町', '05/13', 1),
        ('feminist_jp',  'みさき',              '@misaki_rights',    None, None,
         'ジェンダー平等について考える\n社会学専攻→社会人\n映画と本が好き。差別にはNOと言う\nshe/her', '東京', '', 1),
        ('datsusara',    'けんた@脱サラ',        '@kenta_freelance',  None, None,
         '元SE、今フリーランス2年目\nリモートワーク最高だけど確定申告こわい\n月収は聞かないで', 'リモート', '1993/02/28', 1),
        ('mama_account', 'ゆかり@2y♂',          '@yukari_mama2y',    None, None,
         '2歳男の子のママ👦\nワンオペ育児の日々\n離乳食のレシピ探してます\n寝かしつけは戦争', '横浜', '', 1),
        ('sake_lover',   'のぶ',               '@nobu_and_sake',    None, None,
         '日本酒が好きすぎる人🍶\n居酒屋巡り。獺祭より地酒派\n週5で飲んでるけど肝臓の声は聞こえない', '新宿', '1990/10/10', 1),
        ('soccer_otaku', 'カズ',               '@kazu_football',    None, None,
         'Jリーグ⚽プレミア⚽\n戦術厨です。DAZNが親友\nにわかに厳しい(自覚はある)', '', '', 1),
        ('vtuber_fan',   'シロ推し',            '@shiro_oshi_v',     None, None,
         'Vtuber箱推し🎐\nスパチャは生活費から出してる\n切り抜き職人(自称)\n寝落ち配信で一緒に寝る', '', '', 1),
        ('train_otaku',  'のぞみ',              '@nozomi_train',     None, None,
         '乗り鉄🚃\n撮り鉄もやるけどマナーは守る派\n時刻表を読むのが趣味\n青春18きっぷの季節がそわそわする', '品川', '', 1),
        ('uni_student',  'そら@就活終われ',      '@sora_shukatsu',    None, None,
         '24卒。ESを書きすぎて自己PRを暗記した\nお祈りメール収集家\n内定ください🙏', '都内の大学', '2001/09/15', 1),
        ('stock_trader', 'たつや',              '@tatsuya_kabu',     None, None,
         '株と米国ETF📈\n含み損は確定しなければ損じゃない(震え声)\n長期投資と言い聞かせて毎日チャート見てる', '', '', 1),
        # Edgy/polarizing bots
        ('conspiracy_jp', 'まこと@目覚めた人', '@makoto_mezame',    None, None,
         '真実を追求してます\nメディアは信じない\nDYOR\n陰謀論じゃなくて陰謀「事実」', '東京', '', 1),
        ('tokusatsu_love', 'ヒロ@特撮',      '@hiro_tokusatsu',   None, None,
         '仮面ライダー全作品視聴済み\nスーパー戦隊はゴレンジャーから\n日曜朝は聖域', '', '1992/05/05', 1),
        ('minimalist_jp', 'あおい@ミニマリスト', '@aoi_minimal',    None, None,
         '持ち物は100個以下\n部屋に物がない方が落ち着く\n断捨離は人生の整理', '都内1K', '', 1),
        ('anti_social',  '.',               '@___x___0',         None, None,
         '', '', '', 1),
        ('poke_trainer', 'サトシじゃない人',   '@not_satoshi_poke', None, None,
         'ポケモン対戦勢\nレート2000↑\n育成論考えるのが趣味\nダブルバトル派', '', '', 1),
        ('astrology_jp', 'luna🌙',           '@luna_hoshi',       None, None,
         '西洋占星術を独学中\n水星逆行のせいにしがち\n推しの星座はうお座\nホロスコープ読みます', '', '02/19', 1),
        ('ramen_guru',   'いっぺい',          '@ippei_ramen',      None, None,
         '年間300杯\n二郎系が主食\nラーメンの写真しか載せない\nカロリーは見ない主義', '全国のラーメン屋', '1988/12/01', 1),
        ('sleep_deprived','zZzZz',           '@zzz_nemui',        None, None,
         'ねむい', 'お布団', '', 1),
        # Chaotic new bots
        ('ohayo_bot',    'おは☀️',            '@ohayo_man',        None, None,
         'おはようしか言わない\n毎朝5時に起きてる(嘘)', '布団の中', '', 1),
        ('hakkyo_bot',   'ｱｱｱｱｱｱ',           '@aaaaaaa_a',        None, None,
         '', '限界', '', 1),
        ('hitorigoto',   'θ',                '@theta_void',       None, None,
         '虚空', '', '', 1),
        ('ogiri_mc',     '大喜利MC',           '@ogiri_master',     None, None,
         '突然大喜利を始める人\nお題は適当', '場末のステージ', '', 1),
        ('nagabun',      '長文太郎',           '@nagabun_taro',     None, None,
         'なんでも長文で語りたがる人\nすみません長いです', '', '', 1),
        # Music game themed bots
        ('dai_no_sei',    '今日も台のせい',       '@dai_no_sei',       None, None,
         '人の腕前を信じない', 'ゲーセン', '', 1),
        ('intai_sengen',  '音ゲー引退宣言',       '@intai_otoge',      None, None,
         '引退専門', '', '', 1),
        ('notes_kimochi', 'ノーツの気持ち',       '@notes_feeling',    None, None,
         '落ちてくる側の意見', '', '', 1),
        ('sara_kirai',    '皿に嫌われた男',       '@sara_man',         None, None,
         '回してるつもり', '', '', 1),
        ('gc_isu',        'ゲーセンの椅子',       '@gc_chair',         None, None,
         '全部見てる', 'あなたの後ろ', '', 1),
        ('otoge_begin',   '音ゲー初心者bot',      '@otoge_star3',      None, None,
         '☆3から', '', '', 1),
        ('hantei_lab',    '判定研究所',           '@hantei_lab',       None, None,
         'FAST研究', '', '', 1),
        ('tt_official',   'DJターンテーブル公式',  '@tt_official_',     None, None,
         '回される担当', '', '', 1),
        ('otoge_ogiri',   '音ゲー大喜利',         '@otoge_ogiri',      None, None,
         '', '', '', 1),
        ('kaerimichi_og', '帰り道の音ゲーマー',    '@kaerimichi_og',    None, None,
         '帰宅中', '', '', 1),
        # Impression farming bots
        ('imp_farm1',    '恋愛の教科書📖',        '@renai_textbook',   None, None,
         '恋愛心理を毎日発信💕\nフォローで恋愛偏差値UP⬆️', '', '', 1),
        ('imp_farm2',    'ビジネスの本質',        '@business_honshitsu', None, None,
         '20代で年商1億(自称)\nビジネスの本質を毎日発信🔥', '', '', 1),
        ('imp_farm3',    '人間関係の処方箋💊',     '@ningen_shohousen', None, None,
         '人間関係の悩みに効くツイート💊\nフォロバ100%', '', '', 1),
        ('imp_collapse', '有益情報まとめ🔥',       '@yueki_matome',     None, None,
         '有益な情報を毎日発信📌\n途中から何言ってるかわかんなくなるタイプ', '', '', 1),
        ]
        c.executemany(
            'INSERT INTO users (username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            seed_users
        )

    # Migration: fix アイコン references in existing bot bios
    c.execute(
        "UPDATE users SET bio = 'BP120 SQ160 DL180\n減量期つらい。チョコ味のプロテインだけが救い\nleg day is everything' "
        "WHERE username = 'muscle_log' AND bio LIKE '%アイコン%'"
    )
    c.execute(
        "UPDATE users SET bio = '都内でSaaSを作ってます\nvim使い。ターミナルの方が落ち着く\n積読が∞に増えていく' "
        "WHERE username = 'techbot' AND bio LIKE '%アイコン%'"
    )
    c.execute(
        "UPDATE users SET bio = '夜の方が頭が回る\ncoffee & cigarettes\n問いだけ投げて寝ます' "
        "WHERE username = 'philobot' AND bio LIKE '%アイコン%'"
    )

    # Migration: insert new bots if they don't exist yet (for existing DBs)
    new_bots = [
        ('gameotaku',   'れい',               '@rei_gg',            None,
         None, 'FPS/格ゲー\nランクマ回す日々。APEXダイヤ\n配信はしない派。黙々とやるタイプ', '', '', 1),
        ('manga_yomu',  'あき',               '@aki_manga500',      None,
         None, '年間500冊読む人\nジャンプ+とマガポケは毎日チェック\n完結済みを一気読みする幸福感は異常', '埼玉', '', 1),
        ('travel_log',  'yui',               '@yui_and_trip',      None,
         None, '47都道府県制覇まであと3つ🗾\n一人旅・安宿・サウナ\n地方のチェーン店に詳しい', '旅先', '1998/11/03', 1),
        ('inu_suki',    'こむぎ',             '@komugi_wanwan',     None,
         None, '🐕柴犬こむぎ(3歳♂)の飼い主\n散歩は1日2回。ドッグランの常連です\nこむぎの写真を載せるだけのアカウント', '千葉', '', 1),
        ('music_dj',    'K',                 '@k_and_beats',       None,
         None, 'DTM / Lo-Fi / beats\nトラックメイカー見習い\nSoundCloud週1投稿が目標(未達成)', '', '', 1),
        ('study_gram',  'はな',               '@hana_study_log',    None,
         None, '社会人3年目の勉強垢✏️\nTOEIC900目標(現在785)\n朝活はじめました。えらい', '福岡', '1999/07/20', 1),
        # New diverse bots
        ('otoge_haijin', 'ぷろせか廃',          '@proseka_99',       None, None,
         'プロセカAP勢💮\n音ゲー歴8年の親指勢\nイベラン走りすぎて腱鞘炎になりました', '', '', 1),
        ('netoge_waste', 'あすか@FF14',         '@asuka_ff14',       None, None,
         'FF14民です。暁月クリア済\n固定PT募集中…\nログイン時間が睡眠時間を超えた', 'エオルゼア', '', 1),
        ('jirai_chan',   '🖤りぃな🖤',           '@riina_yami',       None, None,
         '量産型→地雷にクラスチェンジした\n歌舞伎町によくいます\nメンヘラじゃないよ？？ほんとだよ？？', '歌舞伎町', '05/13', 1),
        ('feminist_jp',  'みさき',              '@misaki_rights',    None, None,
         'ジェンダー平等について考える\n社会学専攻→社会人\n映画と本が好き。差別にはNOと言う\nshe/her', '東京', '', 1),
        ('datsusara',    'けんた@脱サラ',        '@kenta_freelance',  None, None,
         '元SE、今フリーランス2年目\nリモートワーク最高だけど確定申告こわい\n月収は聞かないで', 'リモート', '1993/02/28', 1),
        ('mama_account', 'ゆかり@2y♂',          '@yukari_mama2y',    None, None,
         '2歳男の子のママ👦\nワンオペ育児の日々\n離乳食のレシピ探してます\n寝かしつけは戦争', '横浜', '', 1),
        ('sake_lover',   'のぶ',               '@nobu_and_sake',    None, None,
         '日本酒が好きすぎる人🍶\n居酒屋巡り。獺祭より地酒派\n週5で飲んでるけど肝臓の声は聞こえない', '新宿', '1990/10/10', 1),
        ('soccer_otaku', 'カズ',               '@kazu_football',    None, None,
         'Jリーグ⚽プレミア⚽\n戦術厨です。DAZNが親友\nにわかに厳しい(自覚はある)', '', '', 1),
        ('vtuber_fan',   'シロ推し',            '@shiro_oshi_v',     None, None,
         'Vtuber箱推し🎐\nスパチャは生活費から出してる\n切り抜き職人(自称)\n寝落ち配信で一緒に寝る', '', '', 1),
        ('train_otaku',  'のぞみ',              '@nozomi_train',     None, None,
         '乗り鉄🚃\n撮り鉄もやるけどマナーは守る派\n時刻表を読むのが趣味\n青春18きっぷの季節がそわそわする', '品川', '', 1),
        ('uni_student',  'そら@就活終われ',      '@sora_shukatsu',    None, None,
         '24卒。ESを書きすぎて自己PRを暗記した\nお祈りメール収集家\n内定ください🙏', '都内の大学', '2001/09/15', 1),
        ('stock_trader', 'たつや',              '@tatsuya_kabu',     None, None,
         '株と米国ETF📈\n含み損は確定しなければ損じゃない(震え声)\n長期投資と言い聞かせて毎日チャート見てる', '', '', 1),
        # Edgy/polarizing bots
        ('conspiracy_jp', 'まこと@目覚めた人', '@makoto_mezame',    None, None,
         '真実を追求してます\nメディアは信じない\nDYOR\n陰謀論じゃなくて陰謀「事実」', '東京', '', 1),
        ('tokusatsu_love', 'ヒロ@特撮',      '@hiro_tokusatsu',   None, None,
         '仮面ライダー全作品視聴済み\nスーパー戦隊はゴレンジャーから\n日曜朝は聖域', '', '1992/05/05', 1),
        ('minimalist_jp', 'あおい@ミニマリスト', '@aoi_minimal',    None, None,
         '持ち物は100個以下\n部屋に物がない方が落ち着く\n断捨離は人生の整理', '都内1K', '', 1),
        ('anti_social',  '.',               '@___x___0',         None, None,
         '', '', '', 1),
        ('poke_trainer', 'サトシじゃない人',   '@not_satoshi_poke', None, None,
         'ポケモン対戦勢\nレート2000↑\n育成論考えるのが趣味\nダブルバトル派', '', '', 1),
        ('astrology_jp', 'luna🌙',           '@luna_hoshi',       None, None,
         '西洋占星術を独学中\n水星逆行のせいにしがち\n推しの星座はうお座\nホロスコープ読みます', '', '02/19', 1),
        ('ramen_guru',   'いっぺい',          '@ippei_ramen',      None, None,
         '年間300杯\n二郎系が主食\nラーメンの写真しか載せない\nカロリーは見ない主義', '全国のラーメン屋', '1988/12/01', 1),
        ('sleep_deprived','zZzZz',           '@zzz_nemui',        None, None,
         'ねむい', 'お布団', '', 1),
        # Chaotic new bots
        ('ohayo_bot',    'おは☀️',            '@ohayo_man',        None, None,
         'おはようしか言わない\n毎朝5時に起きてる(嘘)', '布団の中', '', 1),
        ('hakkyo_bot',   'ｱｱｱｱｱｱ',           '@aaaaaaa_a',        None, None,
         '', '限界', '', 1),
        ('hitorigoto',   'θ',                '@theta_void',       None, None,
         '虚空', '', '', 1),
        ('ogiri_mc',     '大喜利MC',           '@ogiri_master',     None, None,
         '突然大喜利を始める人\nお題は適当', '場末のステージ', '', 1),
        ('nagabun',      '長文太郎',           '@nagabun_taro',     None, None,
         'なんでも長文で語りたがる人\nすみません長いです', '', '', 1),
        # Music game themed bots
        ('dai_no_sei',    '今日も台のせい',       '@dai_no_sei',       None, None,
         '人の腕前を信じない', 'ゲーセン', '', 1),
        ('intai_sengen',  '音ゲー引退宣言',       '@intai_otoge',      None, None,
         '引退専門', '', '', 1),
        ('notes_kimochi', 'ノーツの気持ち',       '@notes_feeling',    None, None,
         '落ちてくる側の意見', '', '', 1),
        ('sara_kirai',    '皿に嫌われた男',       '@sara_man',         None, None,
         '回してるつもり', '', '', 1),
        ('gc_isu',        'ゲーセンの椅子',       '@gc_chair',         None, None,
         '全部見てる', 'あなたの後ろ', '', 1),
        ('otoge_begin',   '音ゲー初心者bot',      '@otoge_star3',      None, None,
         '☆3から', '', '', 1),
        ('hantei_lab',    '判定研究所',           '@hantei_lab',       None, None,
         'FAST研究', '', '', 1),
        ('tt_official',   'DJターンテーブル公式',  '@tt_official_',     None, None,
         '回される担当', '', '', 1),
        ('otoge_ogiri',   '音ゲー大喜利',         '@otoge_ogiri',      None, None,
         '', '', '', 1),
        ('kaerimichi_og', '帰り道の音ゲーマー',    '@kaerimichi_og',    None, None,
         '帰宅中', '', '', 1),
        # Impression farming bots
        ('imp_farm1',    '恋愛の教科書📖',        '@renai_textbook',   None, None,
         '恋愛心理を毎日発信💕\nフォローで恋愛偏差値UP⬆️', '', '', 1),
        ('imp_farm2',    'ビジネスの本質',        '@business_honshitsu', None, None,
         '20代で年商1億(自称)\nビジネスの本質を毎日発信🔥', '', '', 1),
        ('imp_farm3',    '人間関係の処方箋💊',     '@ningen_shohousen', None, None,
         '人間関係の悩みに効くツイート💊\nフォロバ100%', '', '', 1),
        ('imp_collapse', '有益情報まとめ🔥',       '@yueki_matome',     None, None,
         '有益な情報を毎日発信📌\n途中から何言ってるかわかんなくなるタイプ', '', '', 1),
    ]
    for bot in new_bots:
        c.execute('SELECT id FROM users WHERE username = ?', (bot[0],))
        if not c.fetchone():
            c.execute(
                'INSERT INTO users (username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                bot
            )

    # Migration: update existing bot bios, locations, and birthdays to new natural style
    bio_updates = [
        ('都内でSaaSを作ってます\nvim使い。ターミナルの方が落ち着く\n積読が∞に増えていく', '東京', '', 'techbot'),
        ('🐱🐱🐱と暮らしてる人\n帰ったら即モフ。TLは猫か飯しか流れてこない', '', '', 'catlover99'),
        ('何でも実況してしまう癖\n元マスコミ志望だったけど挫折して今は普通の会社員\n誤報だったらすまん', '大阪', '1997/03/22', 'newsflash'),
        ('夜の方が頭が回る\ncoffee & cigarettes\n問いだけ投げて寝ます', '', '', 'philobot'),
        ('BP120 SQ160 DL180\n減量期つらい。チョコ味のプロテインだけが救い\nleg day is everything', 'ジム', '1995/08/14', 'muscle_log'),
        ('自炊の記録用アカウント📝\n残り物で何か作る∞チャレンジ\n味噌汁だけはガチ。事故ったら正直に載せる', '名古屋', '', 'jishou_chef'),
        ('⚰️全通⚰️\n円盤3積みは当たり前\n新ビジュで感情がぐちゃぐちゃになる人\nCDJ当落まだ？？？', '推しの心臓の近く', '12/25', 'oshi_genkai'),
        ('気象予報士の卵です☁️\nCb(積乱雲)の写真をひたすら集めてる\n天気でしか会話できない日がある', '仙台', '', 'tenki_niki'),
        ('写ルンです。Nikon FM2。\n夕方と深夜のコンビニ専門\n撮って出し派。加工はしない主義', '京都', '2000/04/10', 'emoi_photo'),
        ('FPS/格ゲー\nランクマ回す日々。APEXダイヤ\n配信はしない派。黙々とやるタイプ', '', '', 'gameotaku'),
        ('年間500冊読む人\nジャンプ+とマガポケは毎日チェック\n完結済みを一気読みする幸福感は異常', '埼玉', '', 'manga_yomu'),
        ('47都道府県制覇まであと3つ🗾\n一人旅・安宿・サウナ\n地方のチェーン店に詳しい', '旅先', '1998/11/03', 'travel_log'),
        ('🐕柴犬こむぎ(3歳♂)の飼い主\n散歩は1日2回。ドッグランの常連です\nこむぎの写真を載せるだけのアカウント', '千葉', '', 'inu_suki'),
        ('DTM / Lo-Fi / beats\nトラックメイカー見習い\nSoundCloud週1投稿が目標(未達成)', '', '', 'music_dj'),
        ('社会人3年目の勉強垢✏️\nTOEIC900目標(現在785)\n朝活はじめました。えらい', '福岡', '1999/07/20', 'study_gram'),
        ('プロセカAP勢💮\n音ゲー歴8年の親指勢\nイベラン走りすぎて腱鞘炎になりました', '', '', 'otoge_haijin'),
        ('FF14民です。暁月クリア済\n固定PT募集中…\nログイン時間が睡眠時間を超えた', 'エオルゼア', '', 'netoge_waste'),
        ('量産型→地雷にクラスチェンジした\n歌舞伎町によくいます\nメンヘラじゃないよ？？ほんとだよ？？', '歌舞伎町', '05/13', 'jirai_chan'),
        ('ジェンダー平等について考える\n社会学専攻→社会人\n映画と本が好き。差別にはNOと言う\nshe/her', '東京', '', 'feminist_jp'),
        ('元SE、今フリーランス2年目\nリモートワーク最高だけど確定申告こわい\n月収は聞かないで', 'リモート', '1993/02/28', 'datsusara'),
        ('2歳男の子のママ👦\nワンオペ育児の日々\n離乳食のレシピ探してます\n寝かしつけは戦争', '横浜', '', 'mama_account'),
        ('日本酒が好きすぎる人🍶\n居酒屋巡り。獺祭より地酒派\n週5で飲んでるけど肝臓の声は聞こえない', '新宿', '1990/10/10', 'sake_lover'),
        ('Jリーグ⚽プレミア⚽\n戦術厨です。DAZNが親友\nにわかに厳しい(自覚はある)', '', '', 'soccer_otaku'),
        ('Vtuber箱推し🎐\nスパチャは生活費から出してる\n切り抜き職人(自称)\n寝落ち配信で一緒に寝る', '', '', 'vtuber_fan'),
        ('乗り鉄🚃\n撮り鉄もやるけどマナーは守る派\n時刻表を読むのが趣味\n青春18きっぷの季節がそわそわする', '品川', '', 'train_otaku'),
        ('24卒。ESを書きすぎて自己PRを暗記した\nお祈りメール収集家\n内定ください🙏', '都内の大学', '2001/09/15', 'uni_student'),
        ('株と米国ETF📈\n含み損は確定しなければ損じゃない(震え声)\n長期投資と言い聞かせて毎日チャート見てる', '', '', 'stock_trader'),
        ('真実を追求してます\nメディアは信じない\nDYOR\n陰謀論じゃなくて陰謀「事実」', '東京', '', 'conspiracy_jp'),
        ('仮面ライダー全作品視聴済み\nスーパー戦隊はゴレンジャーから\n日曜朝は聖域', '', '1992/05/05', 'tokusatsu_love'),
        ('持ち物は100個以下\n部屋に物がない方が落ち着く\n断捨離は人生の整理', '都内1K', '', 'minimalist_jp'),
        ('', '', '', 'anti_social'),
        ('ポケモン対戦勢\nレート2000↑\n育成論考えるのが趣味\nダブルバトル派', '', '', 'poke_trainer'),
        ('西洋占星術を独学中\n水星逆行のせいにしがち\n推しの星座はうお座\nホロスコープ読みます', '', '02/19', 'astrology_jp'),
        ('年間300杯\n二郎系が主食\nラーメンの写真しか載せない\nカロリーは見ない主義', '全国のラーメン屋', '1988/12/01', 'ramen_guru'),
        ('ねむい', 'お布団', '', 'sleep_deprived'),
        ('おはようしか言わない\n毎朝5時に起きてる(嘘)', '布団の中', '', 'ohayo_bot'),
        ('', '限界', '', 'hakkyo_bot'),
        ('虚空', '', '', 'hitorigoto'),
        ('突然大喜利を始める人\nお題は適当', '場末のステージ', '', 'ogiri_mc'),
        ('なんでも長文で語りたがる人\nすみません長いです', '', '', 'nagabun'),
    ]
    for bio, loc, bday, uname in bio_updates:
        c.execute(
            'UPDATE users SET bio = ?, location = ?, birthday = ? WHERE username = ? AND is_bot = 1',
            (bio, loc, bday, uname)
        )

    # Migration: update display_names for renamed bots on existing DBs
    display_name_updates = [
        ('k̸ōhei',        'techbot'),
        ('𝗻𝗮𝗻𝗮',        'catlover99'),
        ('タケ/tḁke',    'newsflash'),
        ('海(umi)',        'philobot'),
        ('ÐΛIKI',        'muscle_log'),
        ('sᴀᴄʜɪ.',       'jishou_chef'),
        ('꧁める꧂',      'oshi_genkai'),
        ('ʏᴀᴍᴀᴛᴏ',       'tenki_niki'),
        ('𝘴𝘩𝘪𝘰𝘳𝘪 35mm', 'emoi_photo'),
        ('.',             'anti_social'),
        ('zZzZz',        'sleep_deprived'),
    ]
    for dname, uname in display_name_updates:
        c.execute(
            'UPDATE users SET display_name = ? WHERE username = ? AND is_bot = 1',
            (dname, uname)
        )

    # Seed bot-to-bot follows (only if follows table is empty)
    c.execute('SELECT COUNT(*) FROM follows')
    if c.fetchone()[0] == 0:
        c.execute('SELECT id FROM users WHERE is_bot = 1')
        bot_ids = [r['id'] for r in c.fetchall()]
        for bot_id in bot_ids:
            # Each bot follows 3-8 random other bots
            others = [bid for bid in bot_ids if bid != bot_id]
            follow_count = min(random.randint(3, 8), len(others))
            targets = random.sample(others, follow_count)
            for target_id in targets:
                c.execute('INSERT OR IGNORE INTO follows (follower_id, following_id) VALUES (?, ?)',
                          (bot_id, target_id))

    seed_bot_interactions(conn, c)

    conn.commit()
    conn.close()
