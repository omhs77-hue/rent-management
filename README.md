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
