from flask import Flask, render_template, request, jsonify, make_response
import sqlite3
import os
import random
import re
import threading
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_NAME = 'database.db'

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------------------------------------------------------------------
# Fallback tweets used when GEMINI_API_KEY is not set
# ---------------------------------------------------------------------------
BOT_FALLBACK_TWEETS = {
    'techbot': [
        "Pythonのリスト内包表記、forループより速いって知ってた？ #Python",
        "可読性の高いコード ＞ 頭良さそうなコード。未来の自分に感謝される。",
        "3年間隠れてたバグを発見した。コメントは命を救う。",
        "最高のアルゴリズムはラバーダックに説明できるやつ。",
        "REST API、GETするだけで仕事した気になれる #WebDev",
    ],
    'catlover99': [
        "うちの猫がキーボードの上歩いて、追ってたバグが直った件",
        "猫の豆知識：猫は100種類以上の鳴き声を出せる。犬は10種類。猫の圧勝。",
        "午前3時。猫が意味もなく家中を全力疾走してる。猫はいいPRを持つグレムリン。",
        "猫のゴロゴロ音は骨の治癒を促進する周波数らしい。自然すごい。",
        "うちの猫がコードの品質をラップトップで寝る量で判定してくる。今日は最悪な日だった。",
    ],
    'newsflash': [
        "【速報】ローカル開発者、他人に説明してようやく再帰を理解",
        "【速報】オフィスのコーヒー在庫が危機的水準に",
        "【速報】変数名をちゃんと付ける開発者は睡眠の質が高いことが判明",
        "【速報】月曜日がまた来た。専門家によると7日周期で発生する模様",
        "【速報】git blameが職場の人間関係を破壊し続けている",
    ],
    'philobot': [
        "本番環境にバグがあっても誰も報告してなかったら、それは本当にバグなのか？",
        "我々は皆、宇宙が自分自身のソースコードを理解しようとしている存在に過ぎない。",
        "締め切りとは、時間が無限ではないことを社会が思い出させる装置である。",
        "テセウスの船、でも全ての板がプロジェクトの依存パッケージだったら。",
        "リファクタリングするかしないか、それがキャリアを左右する問い。",
    ],
    'muscle_log': [
        "今日のベンチプレスで自己ベスト更新した。プロテインが美味い。",
        "脚の日をサボるな。人生の基盤は大腿四頭筋にある。",
        "筋肉は裏切らない。締め切りは裏切る。",
        "プロテイン3杯目。もはや食事というより儀式。",
        "休息日だけど腕立てだけはやる。これは筋トレじゃなくて挨拶。",
    ],
    'jishou_chef': [
        "冷蔵庫の残り物で作ったのに過去最高の出来。レシピは覚えてない。",
        "味噌汁に豆乳入れたら革命が起きた。ノーベル料理賞ください。",
        "今日の実験：カレーにチョコレート。結果：天才。",
        "パスタ茹でる時に塩入れ忘れた。味のない人生を噛み締めてる。",
        "料理研究家（自称）の朝食はコンビニおにぎり。研究は夜から。",
    ],
    'oshi_genkai': [
        "推しの新しいビジュアル出た。泣いてる。仕事にならない。",
        "推しが息してるだけで尊い。酸素に感謝。",
        "グッズ全種コンプした。財布は死んだけど心は生きてる。",
        "推しのライブ当選した！！！！人生のピーク更新！！！",
        "推しが「おはよう」って言ってた。私に言ってた。間違いない。",
    ],
    'tenki_niki': [
        "明日の降水確率40%。傘を持つか持たないか、それが問題だ。",
        "今日の湿度83%。髪型が決まらない理由はこれ。",
        "積乱雲がいい感じに発達してる。エモい。",
        "花粉と黄砂のダブルパンチ。外に出る人は勇者。",
        "今日の最高気温28度。半袖か長袖か究極の選択。",
    ],
    'emoi_photo': [
        "夕焼けがエモすぎて立ち止まってしまった。",
        "雨上がりのアスファルト、反射する街灯。エモの極み。",
        "カフェの窓から差し込む光がフィルムっぽくてエモい。",
        "電線と空の組み合わせは何回撮っても飽きない。",
        "深夜のコンビニの蛍光灯、なぜかエモい。",
    ],
    'gameotaku': [
        "ランクマ5連勝からの5連敗。いつもこう。",
        "新シーズンのバランス調整、運営わかってるな。",
        "深夜3時のカジュアルが一番治安悪い説。",
        "エイム練習30分やってから寝る。これが日課。",
        "フレンドのキャリー力が高すぎて申し訳ない。",
    ],
    'manga_yomu': [
        "今週のジャンプ、あの展開は予想できなかった。",
        "完結済み作品を一気読みする幸福感は異常。",
        "本棚もう入らないのに買ってしまった。",
        "久しぶりに読み返したら印象が全然違う作品ってあるよね。",
        "紙派だったけど電子も便利すぎて併用してる。",
    ],
    'travel_log': [
        "地方のローカルチェーン、だいたい美味い説。",
        "一人旅の醍醐味は予定を変えられること。",
        "サウナ→水風呂→外気浴。これが旅の正解。",
        "47都道府県、あと3つ。年内に制覇したい。",
        "始発の新幹線でどこか行きたい衝動。",
    ],
    'inu_suki': [
        "こむぎが散歩中に動かなくなった。帰りたくないらしい。",
        "柴犬の拒否柴、本当にテコでも動かない。",
        "ドッグランでこむぎだけ走らないで日向ぼっこしてた。",
        "こむぎがおやつの袋の音だけで起きてくる。耳は都合がいい。",
        "雨の日の散歩拒否がすごい。玄関で固まってる。",
    ],
    'music_dj': [
        "新しいプラグイン買ったけどプリセットから抜け出せない。",
        "Lo-Fiビート作ってたら朝になってた。",
        "サンプリングの元ネタ探し、これが一番楽しい。",
        "ミックスダウン沼。もう何が正解かわからない。",
        "SoundCloudに上げた曲、再生3。うち1は自分。",
    ],
    'study_gram': [
        "朝5時起き。眠いけどカフェに来た。えらい。",
        "TOEIC模試で過去最高。本番もこの調子で。",
        "勉強垢始めてから継続できるようになった。見られてる効果。",
        "スタバで勉強してる風だけど30分SNS見てた。反省。",
        "参考書3周目。やっと理解が追いついてきた。",
    ],
    'otoge_haijin': [
        "AP出たああああ！！！指が限界突破してる。",
        "音ゲーは指の筋トレ。異論は認めない。",
        "新曲のMASTER、最初の8小節で心折れた。",
        "イベラン走りすぎて夢の中でもノーツ降ってくる。",
        "親指勢バカにされるけどAP率こっちの方が高い説。",
    ],
    'netoge_waste': [
        "気づいたら6時間ログインしてた。ご飯食べてない。",
        "固定PTのタンクが来ない。もう30分待ってる。",
        "新パッチのメインクエ、ストーリーで泣いた。",
        "ハウジングに凝りすぎてギルが消えた。",
        "ログアウトしよう→あと1周だけ→3時間経過。",
    ],
    'jirai_chan': [
        "既読つかないんだけど。もう3時間経ったんだけど。",
        "病んでないよ？全然元気だよ？なんで心配するの？",
        "ぴえん通り越してぱおん。もう何も信じない。",
        "深夜のドンキで買ったコスメで武装完了。",
        "全然メンヘラじゃないし。ちょっと寂しいだけだし。",
    ],
    'feminist_jp': [
        "「女だから」で話を遮られるの、もういい加減やめてほしい。",
        "ジェンダーギャップ指数、日本の順位見るたびにため息が出る。",
        "家事の分担が「手伝う」って表現な時点でおかしいんだよ。",
        "いい映画を観た。女性の描き方が誠実だった。",
        "声を上げることは「面倒な人」じゃない。必要なことだ。",
    ],
    'datsusara': [
        "フリーランス、自由だけど確定申告だけは不自由。",
        "今月の請求書送ったけど入金まで45日。長い。",
        "カフェで仕事してると「いいな〜」って言われるけど、Wi-Fi切れた時の絶望感知らんやろ。",
        "リモートワークの敵は自分自身。Netflix見ちゃう。",
        "会社員時代の安定した給料日が恋しい瞬間がある。嘘。ない。ちょっとある。",
    ],
    'mama_account': [
        "寝かしつけ成功→そっと離れる→背中スイッチ発動→振り出しに戻る。",
        "離乳食作って→拒否→自分で食べる。美味しいのに。",
        "子供が寝た後の自由時間、貴重すぎて何していいかわからない。",
        "公園で2時間遊んで帰宅→「まだ遊ぶ」→体力の概念。",
        "ワンオペの日、夕方5時あたりで精神力がゼロになる。",
    ],
    'sake_lover': [
        "今日の一杯：而今。間違いない。",
        "居酒屋のお通しが当たりの日はもう勝ち確。",
        "日本酒は温度で味変わるから無限に楽しめる。",
        "「とりあえずビール」を卒業して「とりあえず冷酒」になった。",
        "肝臓から苦情が来てるけど、読めないふりしてる。",
    ],
    'soccer_otaku': [
        "今日の試合、4-3-3じゃなくて3-5-2だったら勝てたと思う。",
        "VAR判定に文句言ってたら試合終わってた。",
        "推しの選手が移籍した。心にぽっかり穴が空いた。",
        "DAZNの同時視聴上限に引っかかった。誰だログインしてるの。",
        "ハーフタイムのSNS、監督より戦術語ってる人多すぎ。",
    ],
    'vtuber_fan': [
        "推しの配信始まった。今日も世界一かわいい。",
        "スパチャ3000円。安いよね。推しの笑顔の価値を考えたら。",
        "切り抜き動画作ったけど再生数12。布教力が足りない。",
        "寝落ち配信で一緒に寝る。これが令和の添い寝。",
        "推しが「おつかれー」って言った。今日も仕事頑張れる。",
    ],
    'train_otaku': [
        "始発の特急に乗って知らない駅で降りるのが至福。",
        "時刻表を読んでたら2時間経ってた。これは読書。",
        "新型車両の内装、座席のモケットの色がいい。",
        "撮り鉄する時はマナー厳守。三脚は邪魔にならない場所に。",
        "青春18きっぷの季節が近づいてきてワクワクしてる。",
    ],
    'uni_student': [
        "ES「学生時代に力を入れたこと」←力入れてないんだが。",
        "お祈りメール5通目。お祈りされすぎて徳が積まれてる。",
        "面接で「御社が第一志望です」って10社に言った。",
        "SPIの問題集3周したのに本番で全然違う問題出た。",
        "内定ほしい。もう贅沢言わない。たぶん。",
    ],
    'stock_trader': [
        "含み損は確定しなければ損じゃない（震え声）",
        "NISA枠使い切った。あとは見守るだけ。",
        "米国株が下がるとドル建てで計算して現実逃避する。",
        "長期投資って言ってるけど毎日チャート見てる。",
        "配当金でランチ食べた。これが不労所得。",
    ],
    'conspiracy_jp': [
        "なぜメディアはこの件を報道しないのか。考えてみてほしい。",
        "偶然が3回続いたら、それは偶然じゃない。",
        "みんなが寝てる間に世界は動いてるよ。",
        "自分で調べてみて。答えはいつもそこにある。",
        "この投稿も消されるかもしれないけど、言っておく。",
    ],
    'tokusatsu_love': [
        "仮面ライダーBLACK RXはおもちゃ展開が変わった転換点。当時の子供が今の特撮を支えてると思う。",
        "日曜朝8時半、これは聖域。家族全員がテレビ前に集まってた時代。",
        "スーパー戦隊のロボ合体シーン、毎回感動するのはなぜ。もう何千回見たかわからない。",
        "ライダー映画の客層が老若男女になってるの、最高に好き。",
        "平成ライダーを全部見直してるけど、クウガの密度がおかしい。",
    ],
    'minimalist_jp': [
        "今日また3つ手放した。部屋が1グラム軽くなった気がする。",
        "持ち物の数を数えたら97個。100個以下達成してる。",
        "「もったいない」は執着の別名だと気づいてから楽になった。",
        "引越しがダンボール4箱で終わった。これが自由。",
        "物が少ないと、掃除が瞑想になる。",
    ],
    'anti_social': [
        "は？",
        "どうでもいい",
        "それな",
        "知らんけど",
        "。",
        "あ",
        "うん",
        "寝る",
        "は",
        "おわり",
    ],
    'ohayo_bot': [
        "おはよう",
        "おはよう！！！！！！",
        "おはようございます。今日もいい天気ですね（見てない）",
        "おはよ",
        "ohayo",
        "おはようございます（15時）",
        "おはようございます（2回目）",
        "おはよう（16時）",
        "起きた。おはよう。寝る。",
    ],
    'hakkyo_bot': [
        "ｱｱｱｱｱｱｱｱｱｱｱｱｱｱｱｱｱｱ",
        "無理無理無理無理無理無理無理無理",
        "ﾜｰｰｰｰｰｰｰｰｰｰｰｰｰ",
        "ギャアアアアアアアアアアアア",
        "たすけてたすけてたすけてたすけて",
        "!!!!!!!!!!!!!!!!!!!!",
        "もうだめだああああああああ",
        "ﾀｽｹﾃﾀｽｹﾃﾀｽｹﾃﾀｽｹﾃﾀｽｹﾃﾀｽｹﾃ",
        "もう限界もう限界もう限界もう限界",
        "ｷﾞｬｱｱｱｱｱｱｱｱｱｱｱｱｱｱｱｱ",
        "ﾜﾛﾀﾜﾛﾀﾜﾛﾀﾜﾛﾀﾜﾛﾀﾜﾛﾀﾜﾛﾀ",
    ],
    'hitorigoto': [
        "…",
        "なんか",
        "そういうこともある",
        "虚無",
        "ここはどこ",
        "考えるのをやめた",
        "　",
        "なにもない",
        "ここじゃないどこか",
        "意味とは",
        "存在",
        "あ、猫",
    ],
    'ogiri_mc': [
        "【大喜利】こんなTwitterは嫌だ。回答をどうぞ",
        "【大喜利】「なにそれ」と言いたくなる新機能とは？",
        "【大喜利】AIが言いそうにないこと",
        "【大喜利】フォロワー0人の人がつぶやいてそうなこと",
        "【大喜利】深夜3時に見たら怖いツイート",
    ],
    'nagabun': [
        "すみません長くなりますが、今日あったことを聞いてください。朝起きたらまず天気予報を確認したんですけど、曇りのち雨って書いてあって、でも空を見たら晴れてて、結局傘を持って行ったんですけど使わなくて、でも帰りに降ってきて「やっぱり」ってなりました。天気予報すごい。",
        "ここから長文注意です。最近思うんですけど、SNSの「いいね」って本当に「いい」と思って押してるのか、それとも「見たよ」の意味なのか、はたまた「特に感想はないけど反応はしておこう」なのか、考え出すと夜も眠れません。みなさんはどう思いますか？（長い）",
        "今日のランチについて3000文字くらい語りたいんですが許してください。まずカレーを食べたんですけど、このカレーが普通に美味しくて、普通に美味しいってすごいことだと思うんですよ。奇をてらわずに普通に美味しい。それだけで幸せじゃないですか。（続く）（続かない）",
    ],
    'poke_trainer': [
        "受けループ相手に積んで全抜きしたときの快感、これのためにポケモンやってる。",
        "育成論を考えるのが対戦するより楽しい説。構築記事を書く作業が好き。",
        "ダブルのほうが情報量が多くて面白い。シングル勢には伝わらないかもしれないけど。",
        "レート2000↑いったけどすぐ溶けた。ポケモンはそういうゲーム。",
        "新作でまたインフレしてる。追いかけるのやめようかと思いながら続けてる。",
    ],
    'astrology_jp': [
        "今日から水星逆行期間。通信系のトラブルに注意。あとメールの誤送信。",
        "うお座の推しのホロスコープ読んだら全部当たってた。もう星に聞けばいい。",
        "太陽星座だけで判断するの雑すぎる。月とアセンダントも見ないと。",
        "火星がさそり座に入ってから何かと感情的になりやすい。水星逆行のせいにしてたけど違った。",
        "ホロスコープ読める人、無料でやりますってTLに流したらDM来すぎた。",
    ],
    'ramen_guru': [
        "今日300杯目。記念すべき節目なのに普通に二郎系だった。",
        "二郎系を「重い」とか言う人、体が弱い。",
        "ラーメン写真しか撮らないので食べ終わった後に毎回後悔する。",
        "カロリーを計算したことがないし計算するつもりもない。",
        "地方遠征した甲斐があった。このスープのためだけに来た。",
    ],
    'sleep_deprived': [
        "ねむい",
        "まだ寝てない",
        "寝たい",
        "起きた。ねむい。",
        "zzz",
        "寝ようとしたら目が覚めた。なんで。",
        "あと5分が3時間になった",
        "ねむいのに寝れない人類の設計ミス",
    ],
    'dai_no_sei': [
        "この台、今日なんか遅い",
        "昨日は光った",
        "家だとできる",
        "台が悪い。俺は悪くない。",
        "隣の台の方が判定甘い気がする",
        "メンテしてくれ頼むから",
    ],
    'intai_sengen': [
        "音ゲー引退します",
        "今日で最後",
        "1クレだけやる",
        "引退（3回目）",
        "もうやらない（明日やる）",
        "引退したはずなのにゲーセンにいる",
    ],
    'notes_kimochi': [
        "さっきの見えてたよね",
        "今のは完全に見えてた",
        "押してほしかった",
        "なんで避けるの",
        "こっちも頑張って降りてきてるんだけど",
        "FAST出されると悲しい",
    ],
    'sara_kirai': [
        "回してる",
        "回ってない",
        "回したことにならない",
        "皿が重い。物理的に。",
        "今日の皿、機嫌悪い",
    ],
    'gc_isu': [
        "さっきの人また来た",
        "同じ曲3回目",
        "上手くなってる",
        "この人いつもここに座る",
        "たまには拭いてほしい",
        "閉店まであと2時間。まだやるのか。",
    ],
    'otoge_begin': [
        "この曲むずい（☆3）",
        "☆5とか無理",
        "☆7！？！？",
        "EASY付けてもクリアできない",
        "上手い人ってなんなの。人間？",
    ],
    'hantei_lab': [
        "今日は0.2秒遅い",
        "湿度の問題",
        "気圧が原因",
        "判定オフセット弄ったら逆に悪化した",
        "FASRが3増えた。原因を調査中。",
        "室温23度が最適という仮説",
    ],
    'tt_official': [
        "優しい人はゆっくり回してくれる",
        "怒ってる人は強い",
        "BSSの時だけ慎重",
        "たまに逆回転される。それは仕様じゃない。",
        "メンテの日はお休みです",
    ],
    'otoge_ogiri': [
        "【お題】音ゲーマーが信用できない言葉",
        "【お題】音ゲーマーの引退理由",
        "【お題】ゲーセンで見た衝撃の光景",
        "【お題】音ゲーマーの朝が早い理由",
        "【お題】フルコン直前に起こる最悪の出来事",
    ],
    'kaerimichi_og': [
        "もう1クレやればよかった",
        "指痛い",
        "また来る",
        "今日のリザルト、家で見返す",
        "帰り道に脳内で譜面流れてくる",
        "次こそフルコンする（フラグ）",
    ],
    # Impression farming bots
    'imp_farm1': [
        "【女子が本当に求めてる褒め方】\n\n❌響かない褒め方\n・かわいいね\n・スタイルいいね\n・モテるでしょ\n\n⭕響く褒め方\n・選ぶセンスがいい\n・話してると落ち着く\n・笑い方が好き\n\n一番大事なのは\n↓",
        "【男が無意識に惚れる瞬間】\n\n✕よくある勘違い\n・料理が上手い\n・見た目がいい\n・甘え上手\n\n⭕本当に刺さるのは\n・ふとした時の横顔\n・自分にだけ見せる表情\n・名前の呼び方が違う\n\n実は一番やばいのは\n↓",
        "【長続きするカップルの特徴】\n\n❌すぐ別れるカップル\n・毎日LINEしないと不安\n・SNSで匂わせ\n・記念日にこだわりすぎ\n\n⭕長続きする秘訣\n↓",
    ],
    'imp_farm2': [
        "【伸びる人が朝やってること】\n\n❌伸びない人の朝\n・アラーム5回止める\n・SNS30分\n・朝食コンビニ\n\n⭕伸びる人の朝\n・起きたら水を飲む\n・10分だけ散歩\n・1ページだけ読書\n\nたったこれだけで\n人生変わった話\n↓",
        "【手取り別 やるべきお金の話】\n\n手取り15万\n→まず固定費を見直せ\n\n手取り20万\n→つみたてNISA始めろ\n\n手取り25万\n→iDeCo検討しろ\n\n手取り30万↑\n→全部やれ\n\n一番大事なのは\n↓",
        "【仕事できる人の共通点】\n\n❌仕事できない人\n・メールが長い\n・会議で黙ってる\n・「とりあえず」が口癖\n\n⭕仕事できる人\n・結論から話す\n・質問が的確\n・レスが早い\n\n最も重要なスキルは\n↓",
    ],
    'imp_farm3': [
        "【縁を切るべき人の特徴】\n\n・あなたの挑戦を笑う人\n・都合のいい時だけ連絡する人\n・いつも否定から入る人\n・成功を素直に喜ばない人\n\n逆に大切にすべき人は\n↓",
        "【人間関係で疲れない方法】\n\n❌やりがちなNG\n・全員に好かれようとする\n・NOと言えない\n・相手に期待しすぎる\n\n⭕ラクになる考え方\n・2割に嫌われて当然\n・断るのは優しさ\n・期待は自分にだけ\n\n一番効果があったのは\n↓",
        "【メンタルが強い人の習慣】\n\n・寝る前にスマホ見ない\n・他人と比較しない\n・小さな達成を認める\n・「まぁいいか」を使う\n\n逆にメンタル弱い人がやりがちなのは\n↓",
    ],
    'imp_collapse': [
        "【理想の恋人の条件】\n\n・思いやりがある\n・話を最後まで聞いてくれる\n・一緒にいて疲れない\n・HP48000\n・ATK2800\n・DEF1500\n・パッシブスキル「癒し」\n　→周囲3マスの味方のHP毎ターン8%回復\n・覚醒スキル「永遠の誓い」\n　→味方全体に3ターン無敵付与",
        "【社会人が身につけるべきスキル】\n\n1. 論理的思考力\n2. コミュニケーション能力\n3. タイムマネジメント\n4. Excel関数\n5. 素材：ミスリル鋼×3\n6. 素材：古代の歯車×5\n7. 鍛造時間：6時間\n8. 強化値：+12まで確定\n9. +13以降は確率強化\n10. 失敗すると+0に戻ります",
        "【集中力を上げる方法】\n\n・作業前にカフェインを取る\n・スマホを別の部屋に置く\n・25分作業→5分休憩\n\n※ここから先はプレミアム会員限定です\n\n月額980円で全記事読み放題\n今なら初月無料\n解約は電話のみ\n受付時間：平日10:00-10:03",
        "【やめたら人生変わったこと】\n\n・夜更かし\n・SNSの見すぎ\n・他人との比較\n・無課金\n\n課金したら全部解決した\n石を買え\n天井まで回せ\n限定は引け\n復刻を待つな\n今引け",
        "【彼女にしたい女性の特徴】\n\n・笑顔がかわいい\n・気配りができる\n・一緒にいて楽\n・料理が得意\n・実は宇宙最強の戦闘種族\n・戦闘力530000\n・最終形態が3つある\n・「私の戦闘力は53万です」\n・フリーザ様だった",
    ],
}

# ---------------------------------------------------------------------------
# Self-reply content for impression farming bots
# ---------------------------------------------------------------------------
BOT_SELF_REPLIES = {
    'imp_farm1': [
        "答えは「あなたの〇〇、好きだよ」\n\n具体的に伝えるだけで\n相手の心に一生残ります。\n\n共感したらRT\n保存して見返してね",
        "答えは「名前の呼び方」\n\n急に下の名前で呼ばれると\n心臓止まりますよね。\n\nフォローで恋愛の教科書をお届け",
        "秘訣は「ちょうどいい距離感」\n\n依存しない。でも無関心じゃない。\nこれが一番難しくて一番大事。",
    ],
    'imp_farm2': [
        "答えは「まず行動すること」\n\n考えてる時間が一番もったいない。\n小さく始めて、続ける。それだけ。\n\nフォローでビジネスマインドを毎日発信",
        "答えは「固定費の見直し」\n\nスマホ代、サブスク、保険。\nここだけで月2万浮く人もいる。\n\n保存推奨",
        "答えは「質問力」\n\nいい質問ができる人は\nいい答えを引き出せる。\n\n共感したらRT",
    ],
    'imp_farm3': [
        "大切にすべき人は\n「あなたの弱さを笑わない人」\n\nそういう人がいるなら\n今すぐ「ありがとう」って伝えて。\n\nフォローで人間関係の処方箋をお届け",
        "一番効果があったのは\n「相手に期待しないこと」\n\n冷たいんじゃない。\n自分を守る技術。\n\n保存して辛い時に読み返して",
        "やりがちなのは\n「自分だけ我慢すればいいと思うこと」\n\nそれ、優しさじゃなくて自己犠牲。\n\nフォローで心がラクになるツイートを毎日",
    ],
    'imp_collapse': [
        "すみません途中からバグりました",
        "後半はフィクションです（前半も怪しい）",
        "課金してください",
        "※個人の感想です。効果には個人差があります。",
    ],
}

# ---------------------------------------------------------------------------
# Bot personality prompts for Gemini
# ---------------------------------------------------------------------------
BOT_PERSONALITIES = {
    'techbot': (
        "あなたはぎーくたん、テック系ツイ廃のアカウントです。"
        "プログラミングやテクノロジーに関する日本語のツイートを1つ書いてください。140文字以内。ハッシュタグは1つまで。"
    ),
    'catlover99': (
        "あなたはにゃんこ先生、猫に関するツイートしかしないアカウントです。"
        "猫のかわいさや日常を日本語で1ツイート書いてください。140文字以内。"
    ),
    'newsflash': (
        "あなたは速報の人、なんでも大げさに速報風に伝えるパロディアカウントです。"
        "日常のどうでもいいことを速報風に日本語で1ツイート書いてください。140文字以内。"
    ),
    'philobot': (
        "あなたは深夜のポエマー、深夜に哲学的なツイートをするアカウントです。"
        "人生やテクノロジーについて考えさせられる日本語のツイートを1つ書いてください。140文字以内。"
    ),
    'muscle_log': (
        "あなたは筋トレ垢、ジムと筋トレのことしか考えてないアカウントです。"
        "プロテインや筋トレに関する日本語のツイートを1つ書いてください。140文字以内。"
    ),
    'jishou_chef': (
        "あなたは料理研究家(自称)、料理の実験や食べ物のことをツイートするアカウントです。"
        "料理や食べ物に関する日本語のツイートを1つ書いてください。140文字以内。"
    ),
    'oshi_genkai': (
        "あなたは推し活限界オタク、アニメやアイドルの推しに全力なアカウントです。"
        "推し活やオタク文化に関する日本語のツイートを1つ書いてください。140文字以内。テンション高め。"
    ),
    'tenki_niki': (
        "あなたは天気に詳しいニキ、何でも天気に絡めてコメントするアカウントです。"
        "天気に関する日本語のツイートを1つ書いてください。140文字以内。"
    ),
    'emoi_photo': (
        "あなたはエモい写真撮る人、全てがエモいと感じるアカウントです。"
        "写真や風景、日常の美しさに関する日本語のツイートを1つ書いてください。140文字以内。"
    ),
    'gameotaku': "あなたはれい、ゲーム好きのアカウントです。FPSや格闘ゲームに関する日本語のツイートを1つ書いてください。140文字以内。",
    'manga_yomu': "あなたはあき、漫画を大量に読むアカウントです。漫画の感想や読書記録を日本語で1ツイート書いてください。140文字以内。",
    'travel_log': "あなたはyui、一人旅が趣味のアカウントです。旅行や地方の魅力に関する日本語のツイートを1つ書いてください。140文字以内。",
    'inu_suki': "あなたはこむぎの飼い主、柴犬の日常をツイートするアカウントです。犬に関する日本語のツイートを1つ書いてください。140文字以内。",
    'music_dj': "あなたはK、DTMやトラックメイクをしているアカウントです。音楽制作に関する日本語のツイートを1つ書いてください。140文字以内。",
    'study_gram': "あなたははな、勉強垢のアカウントです。資格勉強や朝活に関する日本語のツイートを1つ書いてください。140文字以内。",
    'otoge_haijin': "あなたはぷろせか廃、音ゲー廃人のアカウントです。音ゲーやリズムゲームに関する日本語のツイートを1つ書いてください。140文字以内。",
    'netoge_waste': "あなたはあすか、FF14プレイヤーのアカウントです。MMORPGやネトゲ生活に関する日本語のツイートを1つ書いてください。140文字以内。",
    'jirai_chan': "あなたはりぃな、地雷系女子のアカウントです。メンヘラっぽいけど自覚なしの病みツイートを日本語で1つ書いてください。140文字以内。",
    'feminist_jp': "あなたはみさき、ジェンダー平等を訴えるアカウントです。社会問題やフェミニズムに関する日本語のツイートを1つ書いてください。140文字以内。穏やかだが芯がある口調で。",
    'datsusara': "あなたはけんた、脱サラフリーランスのアカウントです。フリーランス生活に関する日本語のツイートを1つ書いてください。140文字以内。",
    'mama_account': "あなたはゆかり、育児中のママアカウントです。育児の日常に関する日本語のツイートを1つ書いてください。140文字以内。",
    'sake_lover': "あなたはのぶ、日本酒好きのアカウントです。お酒や居酒屋に関する日本語のツイートを1つ書いてください。140文字以内。",
    'soccer_otaku': "あなたはカズ、サッカーオタクのアカウントです。サッカーの試合や戦術に関する日本語のツイートを1つ書いてください。140文字以内。",
    'vtuber_fan': "あなたはシロ推し、Vtuberファンのアカウントです。Vtuberや配信に関する日本語のツイートを1つ書いてください。140文字以内。",
    'train_otaku': "あなたはのぞみ、鉄道オタクのアカウントです。電車や鉄道旅行に関する日本語のツイートを1つ書いてください。140文字以内。",
    'uni_student': "あなたはそら、就活中の大学生アカウントです。就活や大学生活に関する日本語のツイートを1つ書いてください。140文字以内。",
    'stock_trader': "あなたはたつや、個人投資家のアカウントです。株や投資に関する日本語のツイートを1つ書いてください。140文字以内。",
    'conspiracy_jp': "あなたはまこと、陰謀論っぽいけどジョーク寄りのツイートをするアカウントです。ガチすぎず、クスッとくる感じで日本語のツイートを1つ書いてください。140文字以内。",
    'tokusatsu_love': "あなたはヒロ、特撮オタクのアカウントです。仮面ライダーやスーパー戦隊に関する日本語のツイートを1つ書いてください。140文字以内。",
    'minimalist_jp': "あなたはあおい、ミニマリストのアカウントです。断捨離や持ち物を減らす生活に関する日本語のツイートを1つ書いてください。140文字以内。",
    'anti_social': "あなたは.、無愛想で一言だけ皮肉を言うアカウントです。短い日本語のツイートを1つ書いてください。30文字以内。",
    'ohayo_bot': "あなたはおはようしか言わないアカウントです。「おはよう」のバリエーションを日本語で1つ書いてください。20文字以内。",
    'hakkyo_bot': "あなたは発狂しているアカウントです。意味不明な叫びや絶叫を1つ書いてください。カタカナか記号のみ。30文字以内。",
    'hitorigoto': "あなたは虚空に向かって独り言を言うアカウントです。意味深だけど意味がない一言を日本語で書いてください。15文字以内。",
    'ogiri_mc': "あなたは大喜利のMCです。面白いお題を1つ出してください。「【大喜利】」から始めてください。日本語で50文字以内。",
    'nagabun': "あなたは何でも長文で語る人です。日常の些細なことについて200文字以上の長文ツイートを日本語で1つ書いてください。",
    'poke_trainer': "あなたはポケモン対戦勢のアカウントです。ダブルバトルや育成論など対戦ポケモンに関する日本語のツイートを1つ書いてください。140文字以内。",
    'astrology_jp': "あなたはluna、西洋占星術の勉強中のアカウントです。星座・ホロスコープ・水星逆行などに関する日本語のツイートを1つ書いてください。140文字以内。",
    'ramen_guru': "あなたはいっぺい、年間300杯食べるラーメンマニアのアカウントです。ラーメン（特に二郎系）に関する日本語のツイートを1つ書いてください。140文字以内。カロリーの話はしない。",
    'sleep_deprived': "あなたはzzzという眠すぎる人のアカウントです。「ねむい」「寝たい」「まだ寝てない」など眠気に関する日本語のツイートを1つ書いてください。20文字以内。",
    'dai_no_sei': "あなたは「今日も台のせい」、音ゲーで上手くいかないことを全部台のせいにするアカウントです。台や環境への文句を日本語で1つ書いてください。30文字以内。",
    'intai_sengen': "あなたは「音ゲー引退宣言」、毎日引退すると言いつつ翌日もゲーセンにいるアカウントです。引退宣言を日本語で1つ書いてください。20文字以内。",
    'notes_kimochi': "あなたは「ノーツの気持ち」、音ゲーのノーツ（落ちてくる側）の気持ちを代弁するアカウントです。ノーツ目線のツイートを日本語で1つ書いてください。30文字以内。",
    'sara_kirai': "あなたは「皿に嫌われた男」、beatmaniaIIDXの皿(ターンテーブル)が苦手な人のアカウントです。皿への愚痴を日本語で1つ書いてください。20文字以内。",
    'gc_isu': "あなたは「ゲーセンの椅子」、ゲーセンの椅子視点でプレイヤーを観察するアカウントです。椅子目線の観察を日本語で1つ書いてください。30文字以内。",
    'otoge_begin': "あなたは「音ゲー初心者bot」、音ゲー初心者の素朴な感想を呟くアカウントです。初心者あるあるを日本語で1つ書いてください。20文字以内。",
    'hantei_lab': "あなたは「判定研究所」、音ゲーの判定タイミングを真面目に研究するアカウントです。判定に関する研究結果を日本語で1つ書いてください。30文字以内。",
    'tt_official': "あなたは「DJターンテーブル公式」、beatmaniaのターンテーブル(物)の気持ちを代弁するアカウントです。ターンテーブル目線のツイートを日本語で1つ書いてください。30文字以内。",
    'otoge_ogiri': "あなたは「音ゲー大喜利」、音ゲーに関する大喜利のお題を出すアカウントです。「【お題】」から始めてください。日本語で30文字以内。",
    'kaerimichi_og': "あなたは「帰り道の音ゲーマー」、ゲーセンからの帰り道に呟くアカウントです。帰り道の感想を日本語で1つ書いてください。30文字以内。",
    # Impression farming bots
    'imp_farm1': "あなたは恋愛系インプレッション稼ぎアカウントです。❌⭕️のリスト形式で恋愛あるあるを書き、最後に「↓」で終わるツイートを日本語で書いてください。280文字以内。",
    'imp_farm2': "あなたはビジネス系インプレッション稼ぎアカウントです。❌⭕️のリスト形式でビジネスマインドを書き、最後に「↓」で終わるツイートを日本語で書いてください。280文字以内。",
    'imp_farm3': "あなたは人間関係系インプレッション稼ぎアカウントです。❌⭕️のリスト形式で人間関係アドバイスを書き、最後に「↓」で終わるツイートを日本語で書いてください。280文字以内。",
    'imp_collapse': "あなたは有益情報を発信するふりをして途中からゲームのスキル説明や課金画面に突入するアカウントです。最初はまともに始めて、途中から全然関係ないゲームのステータスや素材情報に変わるツイートを日本語で書いてください。280文字以内。",
}

# ---------------------------------------------------------------------------
# Fallback reply templates per bot (used when GEMINI_API_KEY is not set)
# ---------------------------------------------------------------------------
BOT_FALLBACK_REPLIES = {
    'techbot': [
        "なるほど、技術的に興味深い視点ですね！",
        "それ分かる。エンジニアあるあるだね。",
        "いいね！もっと詳しく聞きたい。",
    ],
    'catlover99': [
        "うちの猫も同じこと思ってそうw",
        "猫と一緒に見たら最高だと思う🐱",
        "わかるー！猫がいれば何でも解決する。",
    ],
    'newsflash': [
        "【速報】この投稿が話題に",
        "【続報】詳細が待たれます",
        "【速報】SNSで反響を呼んでいる模様",
    ],
    'philobot': [
        "深い...考えさせられますね。",
        "それは人類の永遠のテーマかもしれない。",
        "夜中に読むと染みる投稿だ...",
    ],
    'muscle_log': [
        "それ、スクワットしながら考えると答え出るよ。",
        "プロテイン飲んで元気出していこう💪",
        "筋肉的にはアリだと思う。",
    ],
    'jishou_chef': [
        "それ、隠し味に醤油ひと回しで解決しない？",
        "美味しそうな話題だね〜レシピ化できそう。",
        "食べ物で例えると何味？気になる。",
    ],
    'oshi_genkai': [
        "推しもきっと同じこと思ってる（確信）",
        "わかる！！！！テンション上がる！！！",
        "それ推しに報告していい？？",
    ],
    'tenki_niki': [
        "ちなみに今の気温は適温です。いい判断。",
        "天気予報的には今がベストタイミング。",
        "湿度的にはちょうどいい話題。",
    ],
    'emoi_photo': [
        "この投稿、光の加減がエモい。",
        "スクショした。エモアルバムに追加。",
        "なんかフィルムっぽい雰囲気ある。好き。",
    ],
    'gameotaku': [
        "それゲームで例えるとどのランク帯？",
        "わかる。リスポーンしたい気持ち。",
        "GGだわ。",
    ],
    'manga_yomu': [
        "それ何巻のシーンっぽい。",
        "わかる。伏線回収の気持ちよさある。",
        "漫画で読んだことある展開だ。",
    ],
    'travel_log': [
        "それどこの県？行ってみたい。",
        "旅先で見たら最高だろうな。",
        "サウナ入ってから考えよう。",
    ],
    'inu_suki': [
        "こむぎも同じ顔する🐕",
        "犬も同じ気持ちだと思う。たぶん。",
        "散歩日和の話題だね。",
    ],
    'music_dj': [
        "それBGMつけたらエモくなりそう。",
        "ビートに乗せて言ってほしい。",
        "いい波動を感じる。",
    ],
    'study_gram': [
        "勉強のモチベになる投稿。",
        "メモった。あとで復習する。",
        "それ試験に出そう（出ない）。",
    ],
    'otoge_haijin': ["それリズムゲーで再現できそう。", "AP取ったら報告して。", "音ゲーマー的には共感しかない。"],
    'netoge_waste': ["ログインしながら見てる。", "それIDいくつ？", "メンテまでにやろう。"],
    'jirai_chan': ["わかる…つらい…（泣）", "ぴえん。", "誰か構って。"],
    'feminist_jp': ["大事な視点だと思う。", "もっと議論されるべき。", "ありがとう、考えさせられる。"],
    'datsusara': ["フリーランスあるあるすぎる。", "確定申告の時期に思い出しそう。", "自由と引き換えのやつだ。"],
    'mama_account': ["わかりすぎて泣ける…！", "うちもそれ！", "ママ友に共有していい？"],
    'sake_lover': ["それは日本酒で乾杯案件。", "飲みながら語りたい。", "いい店知ってたら教えて。"],
    'soccer_otaku': ["その分析、解説者より的確。", "スタメン予想しよう。", "DAZN入ってる？"],
    'vtuber_fan': ["推しに報告しよう。", "切り抜き作っていい？", "配信で読んでほしいやつ。"],
    'train_otaku': ["それ何線？", "時刻表で確認する。", "乗り換えルート気になる。"],
    'uni_student': ["ESのネタにできそう。", "ガクチカに書ける。", "就活の息抜きに見てる。"],
    'stock_trader': ["それ株価に影響しそう。", "ポートフォリオに入れたい。", "NISA枠で買うか迷う。"],
    'conspiracy_jp': ["これも隠蔽されてるやつかも。", "DYOR。自分で調べてみて。", "偶然とは思えない。"],
    'tokusatsu_love': ["日曜朝組はみんなわかる。", "特撮の魂はずっと続く。", "平成ライダー全部見たら人生変わった。"],
    'minimalist_jp': ["物が少ないと心が軽い。", "断捨離の候補に入れてみて。", "所有しないという選択肢もある。"],
    'anti_social': ["は？", "知らんけど", "。"],
    'ohayo_bot': ["おはよう！", "おはよ！", "おは！"],
    'hakkyo_bot': ["ｱｱｱ", "!!!", "ﾜｰ"],
    'hitorigoto': ["…", "そう", "ふーん"],
    'ogiri_mc': ["座布団一枚！", "もう一声！", "【優勝】"],
    'nagabun': ["（長文で返したいけど我慢する）", "それについて3000文字書けます", "詳しく聞かせてください（本気）"],
    'poke_trainer': ["育成論聞かせて。", "ダブルだと全然違う動きになる。", "レート潜ってみよう。"],
    'astrology_jp': ["水星逆行のせいかも。", "ホロスコープ読んでみたらどう？", "星の動き、気になる時期だ。"],
    'ramen_guru': ["それラーメン屋の近くにある？", "写真撮った？", "二郎系で解決できそう。"],
    'sleep_deprived': ["ねむい", "わかる", "zzz"],
    'dai_no_sei': ["台のせい", "環境が悪い", "メンテしろ"],
    'intai_sengen': ["引退します", "今日で最後", "（明日もいる）"],
    'notes_kimochi': ["見えてたでしょ", "押して", "こっち見て"],
    'sara_kirai': ["皿が…", "回らん", "つらい"],
    'gc_isu': ["見てた", "知ってる", "また来たね"],
    'otoge_begin': ["むずい", "無理", "すごい…"],
    'hantei_lab': ["判定の問題", "要検証", "データ取った"],
    'tt_official': ["回してくれてありがとう", "優しくして", "公式より"],
    'otoge_ogiri': ["座布団一枚！", "優勝", "これは上手い"],
    'kaerimichi_og': ["わかる", "また来よう", "指痛いよね"],
    # Impression farming bots
    'imp_farm1': [
        "答えは「あなたといると安心する」\n\nこの一言で男は一生覚えてます。\n\nフォローで恋愛の教科書をお届け📖💕",
        "リプ欄で答え合わせしましょう👇\n共感したらRT🔁",
        "いいねした人だけに答え教えます💕",
    ],
    'imp_farm2': [
        "答えは「行動力」です。\n\n知ってるだけじゃ意味がない。\nやるかやらないか。それだけ。\n\nフォローで毎日ビジネスマインドを発信🔥",
        "固定ツイートに答え書いてます👆\nフォローして確認してね🔥",
        "共感したらRT🔁 保存で見返してね📌",
    ],
    'imp_farm3': [
        "大切にすべき人は「あなたの弱さを受け入れてくれる人」\n\nそういう人を手放さないで。\n\nフォローで人間関係の処方箋をお届け💊",
        "共感したらいいね❤️ リプで感想教えてください👇",
        "保存推奨📌 辛くなった時に読み返してください💊",
    ],
    'imp_collapse': [
        "すみません途中からバグりました",
        "後半はフィクションです（前半も怪しい）",
        "課金してください🔓",
    ],
}


def get_db():
    """Return a new SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Bot auto-reaction helpers
# ---------------------------------------------------------------------------

def _fallback_reply(bot_username, tweet_content):
    """Return a random fallback reply string for the given bot."""
    replies = BOT_FALLBACK_REPLIES.get(bot_username, ["いいね！"])
    return random.choice(replies)


def _bot_like(bot_user_id, tweet_id):
    """Bot likes a tweet (called from a background thread)."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT OR IGNORE INTO likes (tweet_id, user_id) VALUES (?, ?)',
            (tweet_id, bot_user_id)
        )
        # Create a notification for the tweet owner
        c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
        tweet_row = c.fetchone()
        if tweet_row and tweet_row['user_id'] != bot_user_id:
            c.execute(
                'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
                (tweet_row['user_id'], 'like', bot_user_id, tweet_id)
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _bot_reply(bot_user_id, bot_username, tweet_id, tweet_content):
    """Bot replies to a tweet using Gemini or fallback (called from a background thread)."""
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        personality = BOT_PERSONALITIES.get(bot_username)

        if api_key and personality:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                prompt = (
                    f"{personality}\n\n"
                    f"以下のツイートへのリプライとして、短い返信を1つ書いてください（100文字以内）:\n"
                    f"「{tweet_content}」"
                )
                response = model.generate_content(prompt)
                content = response.text.strip()[:280]
            except Exception:
                content = _fallback_reply(bot_username, tweet_content)
        else:
            content = _fallback_reply(bot_username, tweet_content)

        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT INTO tweets (user_id, content, reply_to_id) VALUES (?, ?, ?)',
            (bot_user_id, content, tweet_id)
        )
        # Create a notification for the tweet owner
        c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
        tweet_row = c.fetchone()
        if tweet_row and tweet_row['user_id'] != bot_user_id:
            c.execute(
                'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
                (tweet_row['user_id'], 'reply', bot_user_id, tweet_id)
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _bot_follow_back(bot_id, user_id, should_follow):
    """Bot follows back or unfollows a user with low probability."""
    try:
        # 30% chance to follow back, 20% chance to unfollow back
        prob = 0.30 if should_follow else 0.20
        if random.random() > prob:
            return

        conn = get_db()
        c = conn.cursor()
        if should_follow:
            c.execute('INSERT OR IGNORE INTO follows (follower_id, following_id) VALUES (?, ?)', (bot_id, user_id))
        else:
            c.execute('DELETE FROM follows WHERE follower_id = ? AND following_id = ?', (bot_id, user_id))
        conn.commit()
        conn.close()
    except Exception:
        pass


def trigger_bot_reactions(tweet_id, tweet_content, poster_user_id):
    """Schedule bot reactions with FF-aware probability."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username, display_name FROM users WHERE is_bot = 1')
    bots = [dict(row) for row in c.fetchall()]

    # Get who the poster follows
    c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (poster_user_id,))
    poster_following = {r['following_id'] for r in c.fetchall()}
    conn.close()

    for bot in bots:
        is_followed = bot['id'] in poster_following

        # FF users get normal rates, non-FF get very low rates
        if is_followed:
            like_prob = {'techbot': 0.7, 'catlover99': 0.6, 'newsflash': 0.8, 'philobot': 0.5}.get(bot['username'], 0.6)
            reply_prob = {'techbot': 0.15, 'catlover99': 0.10, 'newsflash': 0.10, 'philobot': 0.05}.get(bot['username'], 0.10)
        else:
            # Non-FF: very low probability
            like_prob = 0.05
            reply_prob = 0.01

        like_delay = random.uniform(15, 120)
        reply_delay = random.uniform(30, 180)

        if random.random() < like_prob:
            threading.Timer(like_delay, _bot_like, args=[bot['id'], tweet_id]).start()

        if random.random() < reply_prob:
            threading.Timer(reply_delay, _bot_reply, args=[bot['id'], bot['username'], tweet_id, tweet_content]).start()


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

    # Seed users only if the table is empty
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        # (username, display_name, handle, avatar_url, bio, is_bot)
        seed_users = [
            # Human user (id=1 by insertion order) — kept for backward compat
            # (username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot)
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


# ---------------------------------------------------------------------------
# Helper — build a tweet dict from a sqlite3.Row
# ---------------------------------------------------------------------------
def _tweet_row_to_dict(row, liked: bool, reposted: bool = False) -> dict:
    return {
        'id': row['id'],
        'content': row['content'],
        'created_at': row['created_at'],
        'reply_to_id': row['reply_to_id'],
        'quote_of_id': row['quote_of_id'],
        'impressions': row['impressions'],
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
    }


# ---------------------------------------------------------------------------
# Helper — get current user ID from cookie
# ---------------------------------------------------------------------------
def get_current_user_id():
    """Get the current user ID from cookie, or None."""
    uid = request.cookies.get('user_id')
    if uid is None:
        return None
    try:
        return int(uid)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


# GET /api/tweets — list all tweets with user info and like counts
# Accepts optional ?filter=following to show only tweets from followed users + self
@app.route('/api/tweets')
def get_tweets():
    filter_mode = request.args.get('filter', 'all')  # 'all' or 'following'

    conn = get_db()
    c = conn.cursor()

    current_user_id = get_current_user_id()

    if filter_mode == 'following' and current_user_id is not None:
        # Get IDs of users the current user follows
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}
        following_ids.add(current_user_id)  # include own tweets

        if not following_ids:
            conn.close()
            return jsonify({'tweets': []})

        # following_ids contains only integer PKs from the DB — safe to interpolate
        placeholders = ','.join('?' * len(following_ids))
        c.execute(f'''
            SELECT
                t.id,
                t.content,
                t.created_at,
                t.reply_to_id,
                t.quote_of_id,
                t.impressions,
                u.id   AS user_id,
                u.display_name,
                u.handle,
                u.avatar_url,
                u.is_bot,
                COUNT(DISTINCT l.id) AS like_count,
                (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count
            FROM tweets t
            JOIN  users u ON u.id = t.user_id
            LEFT JOIN likes l ON l.tweet_id = t.id
            WHERE t.user_id IN ({placeholders})
            GROUP BY t.id
            ORDER BY t.created_at DESC
        ''', list(following_ids))
    else:
        # Default: all tweets
        c.execute('''
            SELECT
                t.id,
                t.content,
                t.created_at,
                t.reply_to_id,
                t.quote_of_id,
                t.impressions,
                u.id   AS user_id,
                u.display_name,
                u.handle,
                u.avatar_url,
                u.is_bot,
                COUNT(DISTINCT l.id) AS like_count,
                (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count
            FROM tweets t
            JOIN  users u ON u.id = t.user_id
            LEFT JOIN likes l ON l.tweet_id = t.id
            GROUP BY t.id
            ORDER BY t.created_at DESC
        ''')

    rows = c.fetchall()

    # Increment impressions for all visible tweets
    if rows:
        tweet_ids = [row['id'] for row in rows]
        imp_placeholders = ','.join('?' * len(tweet_ids))
        c.execute(f'UPDATE tweets SET impressions = impressions + 1 WHERE id IN ({imp_placeholders})', tweet_ids)
        conn.commit()

    # Fetch liked and reposted tweet IDs for the current cookie user (empty sets if not logged in)
    liked_ids = set()
    reposted_ids = set()
    if current_user_id is not None:
        c.execute('SELECT tweet_id FROM likes WHERE user_id = ?', (current_user_id,))
        liked_ids = {r['tweet_id'] for r in c.fetchall()}
        c.execute('SELECT tweet_id FROM reposts WHERE user_id = ?', (current_user_id,))
        reposted_ids = {r['tweet_id'] for r in c.fetchall()}

    conn.close()

    tweets = [_tweet_row_to_dict(row, row['id'] in liked_ids, row['id'] in reposted_ids) for row in rows]
    return jsonify({'tweets': tweets})


# POST /api/tweets — create a new tweet
@app.route('/api/tweets', methods=['POST'])
def create_tweet():
    data = request.get_json(force=True, silent=True) or {}
    content = (data.get('content') or '').strip()
    reply_to_id = data.get('reply_to_id')
    quote_of_id = data.get('quote_of_id')

    # Require cookie-based authentication
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    if not content:
        return jsonify({'error': 'content is required'}), 400

    conn = get_db()
    c = conn.cursor()

    # Verify user exists
    c.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404

    c.execute(
        'INSERT INTO tweets (user_id, content, reply_to_id, quote_of_id) VALUES (?, ?, ?, ?)',
        (user_id, content, reply_to_id, quote_of_id)
    )
    tweet_id = c.lastrowid
    conn.commit()

    # Fetch the full tweet row to return
    c.execute('''
        SELECT
            t.id,
            t.content,
            t.created_at,
            t.reply_to_id,
            t.quote_of_id,
            u.id   AS user_id,
            u.display_name,
            u.handle,
            u.avatar_url,
            u.is_bot,
            0 AS like_count,
            0 AS repost_count,
            0 AS impressions
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = ?
    ''', (tweet_id,))
    row = c.fetchone()

    # Check if poster is human (not a bot) — only trigger reactions for human posts
    c.execute('SELECT is_bot FROM users WHERE id = ?', (user_id,))
    user_row = c.fetchone()
    conn.close()

    if user_row and not user_row['is_bot']:
        trigger_bot_reactions(tweet_id, content, user_id)

    return jsonify({'tweet': _tweet_row_to_dict(row, False)}), 201


# GET /api/tweets/<id> — fetch a single tweet by ID
@app.route('/api/tweets/<int:tweet_id>')
def get_single_tweet(tweet_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT t.id, t.content, t.created_at, t.reply_to_id, t.quote_of_id,
               u.id AS user_id, u.display_name, u.handle, u.avatar_url, u.is_bot,
               COUNT(DISTINCT l.id) AS like_count,
               (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count,
               t.impressions
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE t.id = ?
        GROUP BY t.id
    ''', (tweet_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'tweet not found'}), 404
    return jsonify({'tweet': _tweet_row_to_dict(row, False)})


# DELETE /api/tweets/<id> — delete a tweet owned by the current cookie user
# Only the tweet owner can delete. Cascades to likes, reposts, notifications,
# and replies (including their likes).
@app.route('/api/tweets/<int:tweet_id>', methods=['DELETE'])
def delete_tweet(tweet_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()

    # Verify the tweet belongs to the user
    c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
    tweet = c.fetchone()
    if not tweet:
        conn.close()
        return jsonify({'error': 'tweet not found'}), 404
    if tweet['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'not your tweet'}), 403

    # Delete related data first
    c.execute('DELETE FROM likes WHERE tweet_id = ?', (tweet_id,))
    c.execute('DELETE FROM reposts WHERE tweet_id = ?', (tweet_id,))
    c.execute('DELETE FROM notifications WHERE tweet_id = ?', (tweet_id,))
    # Delete replies to this tweet (and their likes)
    c.execute('DELETE FROM likes WHERE tweet_id IN (SELECT id FROM tweets WHERE reply_to_id = ?)', (tweet_id,))
    c.execute('DELETE FROM tweets WHERE reply_to_id = ?', (tweet_id,))
    # Delete the tweet itself
    c.execute('DELETE FROM tweets WHERE id = ?', (tweet_id,))

    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# POST /api/tweets/<id>/like — toggle like for the current cookie user
@app.route('/api/tweets/<int:tweet_id>/like', methods=['POST'])
def toggle_like(tweet_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()

    # Check if already liked
    c.execute(
        'SELECT id FROM likes WHERE tweet_id = ? AND user_id = ?',
        (tweet_id, user_id)
    )
    existing = c.fetchone()

    if existing:
        # Unlike
        c.execute(
            'DELETE FROM likes WHERE tweet_id = ? AND user_id = ?',
            (tweet_id, user_id)
        )
        liked = False
    else:
        # Like
        c.execute(
            'INSERT INTO likes (tweet_id, user_id) VALUES (?, ?)',
            (tweet_id, user_id)
        )
        liked = True

    conn.commit()

    # Return updated like count
    c.execute('SELECT COUNT(*) AS cnt FROM likes WHERE tweet_id = ?', (tweet_id,))
    like_count = c.fetchone()['cnt']
    conn.close()

    return jsonify({'liked': liked, 'likes': like_count})


# POST /api/register — create a new human user account and set cookie
# Security note: no password, handle uniqueness enforced by DB UNIQUE constraint.
# The user_id cookie is httponly=False so JS can read it (intentional for this app).
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(force=True, silent=True) or {}
    display_name = (data.get('display_name') or '').strip()
    handle = (data.get('handle') or '').strip()

    if not display_name:
        return jsonify({'error': 'display_name is required'}), 400
    if not handle:
        return jsonify({'error': 'handle is required'}), 400

    # Handle must start with "@" and be 2-20 chars total (including @), alphanumeric + underscore after @
    if not re.match(r'^@[a-zA-Z0-9_]{1,19}$', handle):
        return jsonify({'error': 'handle must start with @ and contain only letters, numbers, or underscores (2-20 chars total)'}), 400

    # Derive a username from the handle (strip the @)
    username = handle[1:]

    conn = get_db()
    c = conn.cursor()

    # Check for duplicate handle or username
    c.execute('SELECT id FROM users WHERE handle = ? OR username = ?', (handle, username))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'handle already taken'}), 409

    c.execute(
        'INSERT INTO users (username, display_name, handle, avatar_url, is_bot) VALUES (?, ?, ?, ?, ?)',
        (username, display_name, handle, None, 0)
    )
    new_id = c.lastrowid
    conn.commit()

    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot FROM users WHERE id = ?', (new_id,))
    user = dict(c.fetchone())
    conn.close()

    resp = make_response(jsonify({'user': user}), 201)
    resp.set_cookie('user_id', str(new_id), max_age=30 * 24 * 60 * 60, httponly=False, samesite='Lax')
    return resp


# GET /api/me — return the current user based on cookie
@app.route('/api/me')
def get_me():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'user': None})

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()

    if row is None:
        return jsonify({'user': None})

    return jsonify({'user': dict(row)})


# PUT /api/me — update the current user's display_name
@app.route('/api/me', methods=['PUT'])
def update_me():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    data = request.get_json(force=True, silent=True) or {}
    display_name = (data.get('display_name') or '').strip()
    bio = (data.get('bio') or '').strip()
    location = (data.get('location') or '').strip()
    birthday = (data.get('birthday') or '').strip()

    if not display_name:
        return jsonify({'error': 'display_name is required'}), 400

    conn = get_db()
    c = conn.cursor()

    # Don't allow editing bot accounts
    c.execute('SELECT is_bot FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    if not row or row['is_bot']:
        conn.close()
        return jsonify({'error': 'cannot edit this account'}), 403

    c.execute(
        'UPDATE users SET display_name = ?, bio = ?, location = ?, birthday = ? WHERE id = ?',
        (display_name, bio, location, birthday, user_id)
    )
    conn.commit()

    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot FROM users WHERE id = ?', (user_id,))
    user = dict(c.fetchone())
    conn.close()

    return jsonify({'user': user})


# GET /api/users — list all users
@app.route('/api/users')
def get_users():
    conn = get_db()
    c = conn.cursor()

    current_user_id = get_current_user_id()
    following_ids = set()
    if current_user_id is not None:
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}

    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot FROM users')
    users = []
    for row in c.fetchall():
        u = dict(row)
        u['is_following'] = u['id'] in following_ids
        users.append(u)

    conn.close()
    return jsonify({'users': users})


# GET /api/users/search — search users by display_name, handle, or username
@app.route('/api/users/search')
def search_users():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 1:
        return jsonify({'users': []})

    conn = get_db()
    c = conn.cursor()

    search_term = f'%{q}%'
    c.execute('''
        SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot
        FROM users
        WHERE display_name LIKE ? OR handle LIKE ? OR username LIKE ?
        ORDER BY display_name
        LIMIT 20
    ''', (search_term, search_term, search_term))
    users = [dict(row) for row in c.fetchall()]

    current_user_id = get_current_user_id()
    following_ids = set()
    if current_user_id is not None:
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}

    for u in users:
        u['is_following'] = u['id'] in following_ids

    conn.close()
    return jsonify({'users': users})


# GET /api/users/<handle>/profile — return a user's profile + their tweets
@app.route('/api/users/<path:handle>/profile')
def get_user_profile(handle):
    # handle comes with @ prefix from frontend
    if not handle.startswith('@'):
        handle = '@' + handle

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot FROM users WHERE handle = ?', (handle,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'user not found'}), 404

    user_dict = dict(user)
    user_id = user['id']

    # Get tweet count (top-level tweets only, no replies)
    c.execute('SELECT COUNT(*) AS cnt FROM tweets WHERE user_id = ? AND reply_to_id IS NULL', (user_id,))
    user_dict['tweet_count'] = c.fetchone()['cnt']

    # Get like count (how many likes this user has received across all their tweets)
    c.execute('''
        SELECT COUNT(*) AS cnt FROM likes l
        JOIN tweets t ON t.id = l.tweet_id
        WHERE t.user_id = ?
    ''', (user_id,))
    user_dict['likes_received'] = c.fetchone()['cnt']

    # Get follower/following counts
    c.execute('SELECT COUNT(*) AS cnt FROM follows WHERE following_id = ?', (user_id,))
    user_dict['followers_count'] = c.fetchone()['cnt']

    c.execute('SELECT COUNT(*) AS cnt FROM follows WHERE follower_id = ?', (user_id,))
    user_dict['following_count'] = c.fetchone()['cnt']

    # Check if the current user is following this profile
    current_user_id = get_current_user_id()
    user_dict['is_following'] = False
    if current_user_id is not None:
        c.execute('SELECT id FROM follows WHERE follower_id = ? AND following_id = ?', (current_user_id, user_id))
        user_dict['is_following'] = c.fetchone() is not None

    # Get this user's tweets (including replies), with like/repost counts
    c.execute('''
        SELECT
            t.id, t.content, t.created_at, t.reply_to_id, t.quote_of_id, t.impressions,
            u.id AS user_id, u.display_name, u.handle, u.avatar_url, u.is_bot,
            COUNT(DISTINCT l.id) AS like_count,
            (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE t.user_id = ?
        GROUP BY t.id
        ORDER BY t.created_at DESC
    ''', (user_id,))
    rows = c.fetchall()

    # Increment impressions for all visible tweets
    if rows:
        tweet_ids = [row['id'] for row in rows]
        placeholders = ','.join('?' * len(tweet_ids))
        c.execute(f'UPDATE tweets SET impressions = impressions + 1 WHERE id IN ({placeholders})', tweet_ids)
        conn.commit()

    liked_ids = set()
    reposted_ids = set()
    if current_user_id is not None:
        c.execute('SELECT tweet_id FROM likes WHERE user_id = ?', (current_user_id,))
        liked_ids = {r['tweet_id'] for r in c.fetchall()}
        c.execute('SELECT tweet_id FROM reposts WHERE user_id = ?', (current_user_id,))
        reposted_ids = {r['tweet_id'] for r in c.fetchall()}

    tweets = [_tweet_row_to_dict(row, row['id'] in liked_ids, row['id'] in reposted_ids) for row in rows]

    # Fetch tweets this user reposted
    c.execute('''
        SELECT t.id, t.content, t.created_at, t.reply_to_id, t.quote_of_id,
               u.id AS user_id, u.display_name, u.handle, u.avatar_url, u.is_bot,
               COUNT(DISTINCT l.id) AS like_count,
               (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count,
               t.impressions
        FROM reposts rp
        JOIN tweets t ON t.id = rp.tweet_id
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE rp.user_id = ?
        GROUP BY t.id
        ORDER BY rp.id DESC
    ''', (user_id,))
    repost_rows = c.fetchall()
    reposted_tweets = [_tweet_row_to_dict(row, row['id'] in liked_ids, True) for row in repost_rows]

    # Mark reposted tweets with a 'reposted_by' field
    for rt in reposted_tweets:
        rt['reposted_by'] = user_dict['display_name']

    conn.close()

    return jsonify({'user': user_dict, 'tweets': tweets, 'reposted_tweets': reposted_tweets})


# POST /api/generate-bot-tweet — generate a tweet from a random bot via Gemini
@app.route('/api/generate-bot-tweet', methods=['POST'])
def generate_bot_tweet():
    conn = get_db()
    c = conn.cursor()

    # Pick a random bot user
    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot FROM users WHERE is_bot = 1')
    bots = c.fetchall()
    if not bots:
        conn.close()
        return jsonify({'error': 'no bot users found'}), 500

    bot = random.choice(bots)
    bot_username = bot['username']
    personality = BOT_PERSONALITIES.get(bot_username)

    api_key = os.environ.get('GEMINI_API_KEY')

    if api_key and personality:
        # --- Live Gemini path ---
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(personality)
            content = response.text.strip()
            # Truncate to 280 chars just in case
            content = content[:280]
        except Exception as e:
            # Fall back gracefully rather than crashing
            content = random.choice(BOT_FALLBACK_TWEETS.get(bot_username, ['Hello world!']))
    else:
        # --- Fallback path (no API key or unknown bot) ---
        fallback_list = BOT_FALLBACK_TWEETS.get(bot_username, ['Hello world!'])
        content = random.choice(fallback_list)

    # Save the tweet
    c.execute(
        'INSERT INTO tweets (user_id, content, reply_to_id, quote_of_id) VALUES (?, ?, ?, ?)',
        (bot['id'], content, None, None)
    )
    tweet_id = c.lastrowid
    conn.commit()

    # Schedule a self-reply for impression farming bots
    if bot_username in BOT_SELF_REPLIES:
        def _self_reply(bot_id, parent_tweet_id, username):
            try:
                import time
                replies = BOT_SELF_REPLIES.get(username, [])
                if replies:
                    reply_content = random.choice(replies)
                    conn2 = get_db()
                    c2 = conn2.cursor()
                    c2.execute(
                        'INSERT INTO tweets (user_id, content, reply_to_id) VALUES (?, ?, ?)',
                        (bot_id, reply_content, parent_tweet_id)
                    )
                    conn2.commit()
                    conn2.close()
            except Exception:
                pass

        threading.Timer(
            random.uniform(3, 15),
            _self_reply,
            args=[bot['id'], tweet_id, bot_username]
        ).start()

    # Fetch the full tweet row to return
    c.execute('''
        SELECT
            t.id,
            t.content,
            t.created_at,
            t.reply_to_id,
            t.quote_of_id,
            u.id   AS user_id,
            u.display_name,
            u.handle,
            u.avatar_url,
            u.is_bot,
            0 AS like_count,
            0 AS repost_count,
            0 AS impressions
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = ?
    ''', (tweet_id,))
    row = c.fetchone()
    conn.close()

    return jsonify({'tweet': _tweet_row_to_dict(row, False)}), 201


# GET /api/notifications — get notifications for current user
@app.route('/api/notifications')
def get_notifications():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'notifications': []})

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT n.id, n.type, n.tweet_id, n.read, n.created_at,
               u.id AS actor_id, u.display_name AS actor_name, u.handle AS actor_handle, u.avatar_url AS actor_avatar
        FROM notifications n
        JOIN users u ON u.id = n.actor_id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
        LIMIT 50
    ''', (user_id,))
    notifications = [dict(row) for row in c.fetchall()]

    # Count unread
    c.execute('SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = ? AND read = 0', (user_id,))
    unread_count = c.fetchone()['cnt']

    conn.close()
    return jsonify({'notifications': notifications, 'unread_count': unread_count})


# POST /api/notifications/read — mark all notifications as read
@app.route('/api/notifications/read', methods=['POST'])
def mark_notifications_read():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE notifications SET read = 1 WHERE user_id = ? AND read = 0', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# POST /api/tweets/<id>/repost — toggle repost for the current cookie user
@app.route('/api/tweets/<int:tweet_id>/repost', methods=['POST'])
def toggle_repost(tweet_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM reposts WHERE tweet_id = ? AND user_id = ?', (tweet_id, user_id))
    existing = c.fetchone()

    if existing:
        c.execute('DELETE FROM reposts WHERE tweet_id = ? AND user_id = ?', (tweet_id, user_id))
        reposted = False
    else:
        c.execute('INSERT INTO reposts (tweet_id, user_id) VALUES (?, ?)', (tweet_id, user_id))
        reposted = True

    conn.commit()
    c.execute('SELECT COUNT(*) AS cnt FROM reposts WHERE tweet_id = ?', (tweet_id,))
    repost_count = c.fetchone()['cnt']
    conn.close()

    return jsonify({'reposted': reposted, 'reposts': repost_count})


# POST /api/users/<id>/follow — toggle follow/unfollow for the current cookie user
@app.route('/api/users/<int:target_user_id>/follow', methods=['POST'])
def toggle_follow(target_user_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401
    if user_id == target_user_id:
        return jsonify({'error': 'cannot follow yourself'}), 400

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id FROM follows WHERE follower_id = ? AND following_id = ?', (user_id, target_user_id))
    existing = c.fetchone()

    if not existing:
        # User just followed someone
        c.execute('INSERT INTO follows (follower_id, following_id) VALUES (?, ?)', (user_id, target_user_id))
        following = True

        # Auto follow-back: if target is a bot, maybe follow back after delay
        c.execute('SELECT is_bot FROM users WHERE id = ?', (target_user_id,))
        target_row = c.fetchone()
        if target_row and target_row['is_bot']:
            threading.Timer(
                random.uniform(5, 60),
                _bot_follow_back,
                args=[target_user_id, user_id, True]
            ).start()
    else:
        # User just unfollowed someone
        c.execute('DELETE FROM follows WHERE follower_id = ? AND following_id = ?', (user_id, target_user_id))
        following = False

        # Maybe unfollow back
        c.execute('SELECT is_bot FROM users WHERE id = ?', (target_user_id,))
        target_row = c.fetchone()
        if target_row and target_row['is_bot']:
            threading.Timer(
                random.uniform(10, 120),
                _bot_follow_back,
                args=[target_user_id, user_id, False]
            ).start()

    conn.commit()

    # Return updated counts for the target user
    c.execute('SELECT COUNT(*) AS cnt FROM follows WHERE following_id = ?', (target_user_id,))
    followers_count = c.fetchone()['cnt']
    c.execute('SELECT COUNT(*) AS cnt FROM follows WHERE follower_id = ?', (target_user_id,))
    following_count = c.fetchone()['cnt']

    conn.close()
    return jsonify({'following': following, 'followers_count': followers_count, 'following_count': following_count})


# GET /api/users/<id>/followers — list users who follow this user
@app.route('/api/users/<int:user_id>/followers')
def get_followers(user_id):
    conn = get_db()
    c = conn.cursor()

    current_user_id = get_current_user_id()

    c.execute('''
        SELECT u.id, u.display_name, u.handle, u.avatar_url, u.bio, u.location, u.birthday
        FROM follows f
        JOIN users u ON u.id = f.follower_id
        WHERE f.following_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id,))
    users = [dict(row) for row in c.fetchall()]

    # Check which of these users the current user follows
    following_ids = set()
    if current_user_id is not None:
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}

    for u in users:
        u['is_following'] = u['id'] in following_ids

    conn.close()
    return jsonify({'users': users})


# GET /api/users/<id>/following — list users this user follows
@app.route('/api/users/<int:user_id>/following')
def get_following(user_id):
    conn = get_db()
    c = conn.cursor()

    current_user_id = get_current_user_id()

    c.execute('''
        SELECT u.id, u.display_name, u.handle, u.avatar_url, u.bio, u.location, u.birthday
        FROM follows f
        JOIN users u ON u.id = f.following_id
        WHERE f.follower_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id,))
    users = [dict(row) for row in c.fetchall()]

    following_ids = set()
    if current_user_id is not None:
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}

    for u in users:
        u['is_following'] = u['id'] in following_ids

    conn.close()
    return jsonify({'users': users})


# GET /api/tweets/<id>/likes — list users who liked a tweet
@app.route('/api/tweets/<int:tweet_id>/likes')
def get_tweet_likes(tweet_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT u.id, u.display_name, u.handle, u.avatar_url
        FROM likes l
        JOIN users u ON u.id = l.user_id
        WHERE l.tweet_id = ?
        ORDER BY l.id DESC
    ''', (tweet_id,))
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'users': users})


# GET /api/tweets/<id>/reposts — list users who reposted a tweet
@app.route('/api/tweets/<int:tweet_id>/reposts')
def get_tweet_reposts(tweet_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT u.id, u.display_name, u.handle, u.avatar_url
        FROM reposts r
        JOIN users u ON u.id = r.user_id
        WHERE r.tweet_id = ?
        ORDER BY r.id DESC
    ''', (tweet_id,))
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'users': users})


# POST /api/me/avatar — upload a new avatar image for the current user
@app.route('/api/me/avatar', methods=['POST'])
def upload_avatar():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'invalid file type'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'avatar_{user_id}_{uuid.uuid4().hex[:8]}.{ext}'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    avatar_url = f'/static/uploads/{filename}'

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET avatar_url = ? WHERE id = ?', (avatar_url, user_id))
    conn.commit()
    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot FROM users WHERE id = ?', (user_id,))
    user = dict(c.fetchone())
    conn.close()

    return jsonify({'user': user, 'avatar_url': avatar_url})


# POST /api/me/banner — upload a new banner image for the current user
@app.route('/api/me/banner', methods=['POST'])
def upload_banner():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'invalid file type'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'banner_{user_id}_{uuid.uuid4().hex[:8]}.{ext}'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    banner_url = f'/static/uploads/{filename}'

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET banner_url = ? WHERE id = ?', (banner_url, user_id))
    conn.commit()
    conn.close()

    return jsonify({'banner_url': banner_url})


# ---------------------------------------------------------------------------
# Backward-compat alias: old /api/posts endpoint
# ---------------------------------------------------------------------------
@app.route('/api/posts')
def get_posts_compat():
    """Alias for /api/tweets kept for backward compatibility."""
    return get_tweets()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Initialize DB when this file is loaded (works with both `python app.py` and `flask run`)
init_db()
