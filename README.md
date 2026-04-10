# Multi-Poster Desktop

PC用デスクトップアプリで、複数のTikTokアカウントに動画を投稿できます。

## 機能

- ✅ マルチアカウント管理（追加・削除・切替）
- ✅ OAuth認証（安全なログイン）
- ✅ チャンク分割アップロード（TikTok API準拠）
- ✅ 投稿状況リアルタイム表示
- ✅ プライバシー設定（公開・友達・非公開）
- ✅ 自動トークン更新
- ✅ Sandboxモード対応（審査前テスト用）

## 必要条件

- Python 3.11+
- TikTok Developer アカウント＆アプリ

## セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/bellemotto03/multi-poster-desktop.git
cd multi-poster-desktop
```

### 2. 仮想環境を作成（推奨）

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# または
venv\Scripts\activate     # Windows
```

### 3. 依存関係をインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数を設定

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```env
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret
TIKTOK_REDIRECT_URI=http://localhost:8080/callback
```

### 5. TikTok Developerアプリ設定

1. [TikTok for Developers](https://developers.tiktok.com/) にログイン
2. アプリを作成
3. 以下のスコープを追加：
   - `user.info.basic`
   - `video.upload`
   - `video.publish`
4. Redirect URIに `http://localhost:8080/callback` を追加
5. Sandboxまたは本番環境でご利用ください

### 6. アプリを起動

```bash
python main.py
```

## 使い方

1. **Sandboxモード切り替え**: デフォルトON（テスト用）
2. **アカウント追加**: 「＋ Add Account」をクリックし、ブラウザでTikTokにログイン
3. **動画選択**: 「Browse」ボタンでMP4ファイルを選択
4. **説明入力**: 動画の説明（キャプション）を入力（最大2,200文字）
5. **プライバシー設定**: 公開範囲を選択
6. **アカウント選択**: 投稿したいアカウントにチェック
7. **アップロード**: 「Upload to Selected Accounts」をクリック

## アーキテクチャ

```
multi-poster-desktop/
├── core/
│   ├── api.py               # TikTok APIクライアント
│   ├── auth.py              # OAuth認証フロー
│   └── account_manager.py   # マルチアカウント管理
├── gui/
│   └── main.py              # CustomTkinter GUI
├── docs/                    # GitHub Pages（公式サイト）
├── config/
│   └── accounts.json        # アカウント情報（暗号化保存）
├── main.py                  # エントリーポイント
└── requirements.txt
```

## 公式サイト

- https://bellemotto03.github.io/multi-poster-desktop/
- [Privacy Policy](https://bellemotto03.github.io/multi-poster-desktop/privacy.html)
- [Terms of Service](https://bellemotto03.github.io/multi-poster-desktop/tos.html)

## 注意事項

- Sandboxモードは非公開投稿（SELF_ONLY）のみ対応
- 動画形式: MP4 (H.264推奨)、最大10分、最大4GB
- チャンクサイズ: 5MB〜64MB（最終チャンク最大128MB）

## ライセンス

MIT
