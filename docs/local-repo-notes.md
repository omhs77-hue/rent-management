# ローカルリポジトリの場所とリモート設定メモ

## ローカルディレクトリの確認
- Google Drive 同期環境で作業する場合、既存のリポジトリは以下のパスに存在する：
  - `~/Library/CloudStorage/GoogleDrive-omhs77@gmail.com/マイドライブ/賃貸管理事業化検討/.git`
- `ls ~/Library/CloudStorage/GoogleDrive-omhs77@gmail.com/マイドライブ/賃貸管理事業化検討` で内容を確認し、`.git` ディレクトリがあることを確かめる。

## リモートの確認と設定
1. 現状のリモート確認：
   - `git -C ~/Library/CloudStorage/GoogleDrive-omhs77@gmail.com/マイドライブ/賃貸管理事業化検討 remote -v`
2. リモート未設定の場合の追加例：
   - SSH: `git -C ~/Library/CloudStorage/GoogleDrive-omhs77@gmail.com/マイドライブ/賃貸管理事業化検討 remote add origin git@github.com:<org>/<repo>.git`
   - HTTPS: `git -C ~/Library/CloudStorage/GoogleDrive-omhs77@gmail.com/マイドライブ/賃貸管理事業化検討 remote add origin https://github.com/<org>/<repo>.git`
3. 既存ブランチを push する際は upstream 設定も兼ねて以下を実行する：
   - `git -C ~/Library/CloudStorage/GoogleDrive-omhs77@gmail.com/マイドライブ/賃貸管理事業化検討 push -u origin <branch>`
4. リモート URL を変更したい場合：
   - `git -C ~/Library/CloudStorage/GoogleDrive-omhs77@gmail.com/マイドライブ/賃貸管理事業化検討 remote set-url origin git@github.com:<org>/<repo>.git`

## 補足
- Google Drive 直下での git 運用時は、同期が完了していることを確認してから push/pull を行う。
- 同期エラー回避のため、特に大量のファイル操作後は Google Drive のステータスが正常になるまで待機する。
