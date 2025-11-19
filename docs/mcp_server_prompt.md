# MCP サーバー作成用プロンプト

以下のブロックを **そのまま** Codex に貼り付けると、GitHub ローカルクローンとクロールデータ(JSONL)を Model Context Protocol で扱うサーバーを作るための指示になります。

```
このリポジトリ（または現在のフォルダ）に「GitHubのローカルクローン」と「クロールデータ(JSONL)」を
Model Context Protocol (MCP) 経由で参照できるサーバーを作りたいです。

前提：
- GitHub リポジトリはローカルに clone 済み（例: /Users/USER/dev/selfmanaged-corpus）
- クロールデータもローカルに存在（例: /Users/USER/data/selfmanaged-corpus）
- ChatGPT から MCP 経由で、
  - Git リポジトリ内の md / py などを開く
  - クロールJSONLを検索・閲覧する
  ことをしたいです。

Node.js + TypeScript と @modelcontextprotocol/sdk を使って MCP サーバーを実装してください。

## 1. プロジェクトのゴール

- 「selfmanaged-mcp-server」という MCP サーバーを作る。
- サーバーは 2 つの「ルート」を扱える：
  - REPO_ROOT: GitHub リポジトリのローカルパス
  - DATA_ROOT: クロールデータのローカルパス
- MCP のツールとして、次を提供してほしい：

1. `list_files`
   - 引数:
     - `source`: "repo" | "corpus"
     - `pattern`: 省略可、`**/*.md` のような glob
   - 機能:
     - 指定 source に応じて root を切り替える
     - glob にマッチする相対パス一覧を返す（最大100件くらい）

2. `read_file`
   - 引数:
     - `source`: "repo" | "corpus"
     - `path`: root からの相対パス
   - 機能:
     - ファイル内容を text として返す
     - サイズが大きすぎる場合は先頭 N KB だけ返し、末尾を省略した旨をメタ情報に入れる

3. `search_text`
   - 引数:
     - `source`: "repo" | "corpus"
     - `query`: string
     - `max_results`: number（デフォルト 20）
   - 機能:
     - 指定 source 配下のテキストファイルを対象に、単純な全文検索を行う
       - repo: .md, .py, .ts, .txt 等
       - corpus: .jsonl, .txt 等
     - grep 的な実装でよい（インデックス不要）
     - マッチしたファイルパスと、いくつかのスニペット（該当行前後）を返す

- REPO_ROOT / DATA_ROOT は環境変数から取得できるようにする：
  - `MCP_REPO_ROOT` 例: `/Users/USER/dev/selfmanaged-corpus`
  - `MCP_DATA_ROOT` 例: `/Users/USER/data/selfmanaged-corpus`

## 2. 技術スタックとセットアップ

- Node.js (最新版でOK)
- TypeScript
- @modelcontextprotocol/sdk

やってほしいこと：

1. package.json / tsconfig.json を作成
2. `src/server.ts` に MCP サーバー本体を実装
3. `npm run build` / `npm start` でローカル起動できるようにする
4. `mcp.json`（または ChatGPT クライアントで使う MCP設定例）を出力してほしい
   - 例:
     - name: "selfmanaged-mcp-server"
     - command: "node"
     - args: ["dist/server.js"]
     - env: MCP_REPO_ROOT, MCP_DATA_ROOT をユーザーが設定できるようにコメントで説明

## 3. 実装仕様の詳細

### 3-1. ディレクトリ構成

次のような構成を想定して TypeScript コードを配置してください。

- package.json
- tsconfig.json
- src/
  - server.ts
  - tools/
    - listFiles.ts
    - readFile.ts
    - searchText.ts
  - utils/
    - fsHelpers.ts
- dist/ （ビルド結果）

### 3-2. 共通ヘルパー

`utils/fsHelpers.ts` に次のようなものを用意してください。

- `getRoot(source: "repo" | "corpus"): string`
  - 環境変数 MCP_REPO_ROOT / MCP_DATA_ROOT からパスを取る
  - 設定されていない場合はエラーを投げる
- `safeJoin(root: string, relPath: string): string`
  - path.join で結合しつつ、root の外に出ないようにチェック（ディレクトリトラバーサル防止）
- `listFilesWithGlob(root: string, pattern: string): Promise<string[]>`
  - fast-glob 等のライブラリを使って実装してよい

### 3-3. 各ツールのインターフェース

@modelcontextprotocol/sdk の標準的なパターンに従ってください。
TypeScript で型定義し、ツール登録時に名前・説明・引数スキーマを指定してください。

例: （ざっくりイメージだけ）

- list_files
  - parameters (JSON Schema):
    - source: enum ["repo", "corpus"]
    - pattern: string, optional
- read_file
  - parameters:
    - source: enum ["repo", "corpus"]
    - path: string
- search_text
  - parameters:
    - source: enum ["repo", "corpus"]
    - query: string
    - max_results: integer, optional

レスポンスは JSON で構造化しつつ、MCPクライアント側が見やすいように
- path
- snippets
- truncatedフラグ
などを含めてください。

### 3-4. server.ts

- @modelcontextprotocol/sdk のサーバーを初期化し、上記3つのツールを登録してください。
- ログ出力は最低限でOK（起動時に REPO_ROOT / DATA_ROOT を表示する程度）。
- エラー時はユーザーにわかりやすいメッセージを返してください（例:"MCP_DATA_ROOT が未設定です" など）。

## 4. ChatGPT から使うイメージ

最終的に、ChatGPT 側からは次のような使い方を想定しています。

- 「`source=repo` で `docs/meetings/20251018.md` を read_file して」
- 「`source=corpus` で `raw/blogs` 以下を search_text(query='保証会社') して」

これらができるようになればOKです。

---

以上の仕様にしたがって、MCPサーバーのコード一式と、
`npm install` → `npm run build` → `npm start` で動かすための手順、
および ChatGPT クライアント用の MCP 設定例を作成してください。

🧩 補足：この MCP が動くと何が変わるか
GitHubローカルクローン
→ ChatGPT が list_files / read_file / search_text で
直接 md / コードを読みにいける
クロールJSONL / ログ
→ source=corpus で検索・閲覧できるので
「保証会社について書いてあるところ全部洗って」みたいなことが自然にできる
これができれば、
「いちいちファイルを貼らなくても、ChatGPT があなたのローカル知識ベースをそのまま参照しながら壁打ち」
みたいな世界にかなり近づきます。
このプロンプトで Codex に MCPサーバーを作らせてみて、
出てきたコード or エラーがあれば、それをここに貼ってくれれば一緒に直していきます。
```
