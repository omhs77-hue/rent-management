# 自主管理大家コンテンツ用クローラ

ブログ記事や YouTube 字幕をローカル JSONL に収集し、RAG 向けのコーパスとして利用するための Python プロジェクトです。

## ディレクトリ構成（`paths.data_root` 配下）

```
<data_root>/
  raw/
    blogs/            # YYYY-MM-DD-<site>.jsonl
    youtube/          # YYYY-MM-DD-<channel>.jsonl
  processed/
    chunks/           # 将来の前処理用プレースホルダ
  logs/
    crawl-blogs.log
    crawl-youtube.log
```

`data_root` は Git 管理対象外で、スクリプト実行時に自動生成されます。

## 使い方（概要）
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp config/settings.example.yml config/settings.yml` を編集（`paths.data_root` や `domains` のウェイト係数など）。
4. `seeds/blogs.yml` と `seeds/youtube_channels.yml` に対象サイト・チャンネルを追記。テンプレートとして自主管理系のサイト/チャンネルをあらかじめ記述済みです。
5. YouTube Data API キーを取得し、`export YOUTUBE_API_KEY=...` で環境変数にセット。
6. ブログ収集: `python -m src.pipelines.crawl_blogs`
7. YouTube 収集: `python -m src.pipelines.crawl_youtube`

各パイプラインは robots.txt を尊重し、レスポンスサイズに応じて 0.5〜3 秒程度の human-like ウェイトを入れながらクロールします。取得データは `config/settings.yml` で指定した `data_root` 以下に JSONL として保存されます。ローカル専用データのため Git には含めません。

取得データは `config/settings.yml` で指定した `data_root` 以下に JSONL として保存されます。ローカル専用データのため Git には含めません。

## 家賃市場調査 CLI (`python -m rent_survey`)

賃貸サイト（HOME'S / SUUMO を想定）から類似条件の募集事例を取得し、家賃+共益費の統計を表示するコマンドラインツールを追加しています。Robots.txt と利用規約を尊重し、人間がブラウザで操作する程度のペース（デフォルト 1.2 秒間隔）でアクセスします。User-Agent は macOS Safari 相当をデフォルトにしつつ `RENT_SURVEY_USER_AGENT` 環境変数または `--user-agent` オプションで変更可能です。

### 使い方

```bash
python -m rent_survey \
  --station "東武練馬" \
  --minutes 10 \
  --area 25 \
  --madori 1K \
  --subject-built 2015-03 \
  --age-max 20 \
  --age-diff 5 \
  --building-type アパート \
  --auto-lock any \
  --bath-toilet any \
  --aspect any \
  --max-listings 50 \
  --sites homes,suumo \
  --output-format csv
```

- `--max-listings` はサイトごとの取得上限です。
- `--output-path` 未指定時は `outputs/` 以下に `rent-survey-YYYYmmdd-HHMMSS.(csv|jsonl)` を自動生成します。
- `--brand-new-separate-stats` を付けると、新築（築年数<1年相当）を除いた統計も合わせて表示します。
- SUUMO/HOME'S 以外のサイトは `rent_survey/sites/` に `SiteClient` 実装を追加し `SITE_REGISTRY` に登録するだけで拡張できます。

### 出力と統計

- ファイル：1 行 1 物件で、賃料・共益費・total_rent・面積・築年情報・設備（オートロック/バストイレ別/採光向き）・最寄駅徒歩分・取得日時 `collected_at` を含みます。
- 標準出力：サイト別件数、重複除去後件数、賃料/total_rent/㎡単価の平均・中央値・最小/最大、築年差別グループ、オートロック有無別、バストイレ別、採光向き別件数などを表示します。
- 現状の重複判定は「物件名 + 面積 + 賃料/管理費 + 駅徒歩」をキーにした単純なものです。TODO コメントの通り、将来的に間取りや部屋番号を含むより高度な重複検出・AI 判定に差し替える前提で実装しています。

### 制限事項

- SUUMO と HOME'S の検索パラメータは公開 UI をベースに想定値で構成しています。検索画面の仕様変更時は `rent_survey/sites/` 配下のクエリ生成・パースロジックを調整してください。
- 法人ネットワークやプロキシ環境によっては 403 (Forbidden) が返る場合があります。その際はブラウザから UI 仕様を再確認しつつ、User-Agent やアクセス間隔を調整してください。
- 取得失敗時は該当サイト名と理由を標準出力（JSON）に表示し、処理を続行します。
