# TikTok Multi-Poster

PC用デスクトップアプリで、複数のTikTokアカウントに動画を投稿できます。

## 機能

- ✅ マルチアカウント管理（追加・削除・切替）
- ✅ OAuth認証（安全なログイン）
- ✅ チャンク分割アップロード（TikTok API準拠）
- ✅ 投稿状況リアルタイム表示
- ✅ プライバシー設定（公開・友達・非公開）
- ✅ 自動トークン更新

## 必要条件

- Python 3.11+
- TikTok Developer アカウント＆アプリ（本番環境）

## セットアップ

### 1. 依存関係をインストール

```bash
cd tiktok-multi-poster
pip install -r requirements.txt
```

### 2. 環境変数を設定

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```env
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret
TIKTOK_REDIRECT_URI=http://localhost:8080/callback
```

### 3. TikTok Developerアプリ設定

1. [TikTok for Developers](https://developers.tiktok.com/) にログイン
2. アプリを作成
3. 以下のスコープを追加：
   - `user.info.basic`
   - `video.upload`
   - `video.publish`
4. Redirect URIに `http://localhost:8080/callback` を追加
5. 本番環境に設定（審査を通過）

### 4. アプリを起動

```bash
python main.py
```

## 使い方

1. **アカウント追加**: 「＋ Add Account」をクリックし、ブラウザでTikTokにログイン
2. **動画選択**: 「Browse」ボタンでMP4ファイルを選択
3. **説明入力**: 動画の説明（キャプション）を入力（最大2,200文字）
4. **プライバシー設定**: 公開範囲を選択
5. **アカウント選択**: 投稿したいアカウントにチェック
6. **アップロード**: 「Upload to Selected Accounts」をクリック

## アーキテクチャ

```
tiktok-multi-poster/
├── core/
│   ├── api.py               # TikTok APIクライアント
│   ├── auth.py              # OAuth認証フロー
│   └── account_manager.py   # マルチアカウント管理
├── gui/
│   └── main.py              # CustomTkinter GUI
├── config/
│   └── accounts.json        # アカウント情報（暗号化保存）
├── main.py                  # エントリーポイント
└── requirements.txt
```

## 注意事項

- TikTok Developerアプリの審査通過が必要です
- 動画形式: MP4 (H.264推奨)、最大10分、最大4GB
- チャンクサイズ: 5MB〜64MB（最終チャンク最大128MB）

## ライセンス

MIT
