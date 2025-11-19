# 自主管理大家コンテンツ用クローラ

ブログ記事や YouTube 字幕をローカル JSONL に収集し、RAG 向けのコーパスとして利用するための Python プロジェクトです。

## 使い方（概要）
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp config/settings.example.yml config/settings.yml` を編集し、`paths.data_root` などを環境に合わせて設定します。
4. `seeds/` 配下の YAML に対象サイトやチャンネルを記入します。
5. ブログ: `python -m src.pipelines.crawl_blogs`
6. YouTube: `python -m src.pipelines.crawl_youtube`

取得データは `config/settings.yml` で指定した `data_root` 以下に JSONL として保存されます。ローカル専用データのため Git には含めません。
