# Aruku — 散歩ログ & GPS

![Demo Screenshot](screen_image.png)

## 📖 概要
美しく設計されたシンプルな散歩トラッキング Web アプリです。ブラウザの Geolocation API と Leaflet を使って現在地取得、ルート記録、写真の位置付け、履歴保存（localStorage）を行います。

## ✨ 主な機能
- リアルタイムでの現在地取得（`getCurrentPosition` / `watchPosition`）
- ルートのポリライン描画（Leaflet）
- 写真を撮って地図上にサムネイルを保存
- 履歴の保存・一覧表示（localStorage）
- モバイルファーストでレスポンシブ対応


## 🛠 前提条件・インストール

**環境**
- Node.js 18 以上
- npm または yarn

**インストール手順**
1. リポジトリをクローンまたはダウンロード
   ```powershell
   git clone https://dubro2019.github.io/my-vibe-agravs/walkings-app.git
   cd walking-app
   ```
2. 依存パッケージをインストール
   ```bash
   npm install
   ```

## 🚀 起動・使い方

### 1. GitHub Pages で開く（推奨）
以下の URL にアクセスしてください。
- https://dubro2019.github.io/my-vibe-agravs/walking-app/

### 2. 開発サーバーを起動
```bash
npm run dev
```

その後、ブラウザで `http://localhost:5173` にアクセスします。

### 3. 本番ビルド（任意）
```bash
npm run build

または `live-server`（npm） を使用:
```bash
npm install -g live-server
live-server .
```

ビルド後は `dist/` 内の静的ファイルを任意のサーバーで配信できます。


### すぐに試す
1. リポジトリをクローンまたはワークスペースに移動
2. `index.html` をブラウザで直接開く（簡単なオプション）

推奨：簡易ローカルサーバーで起動すると位置情報やマップの挙動が安定します。

## 🧰 テックスタック

- 主要ファイル:
  - [index.html](index.html) — アプリ本体の HTML
  - [script.js](script.js) — 全てのクライアントロジック（Geolocation、Leaflet、localStorage）
  - [style.css](style.css) — レイアウトとスタイル

- 外部依存:
  - Leaflet（CDN 経由で読み込み）
  - Google Fonts（CDN）

## 📂 ディレクトリ構成

```
walking-app/
├─ index.html
├─ script.js
├─ style.css
└─ README.md
```

## 既知の注意点と推奨改善
- ブラウザの位置情報許可が必要です。許可がない場合は機能が制限されます。
- オフライン対応やルートのサーバー保存（同期）、GPX/GeoJSON エクスポートは将来的な改善案です。


## 📄 ライセンス
MIT ライセンス。自由に改変・再配布できます。

---
**Powered by Antigravity** – your AI‑assisted development partner.

