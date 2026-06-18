# 割り勘計算機 (Warikan Calculator)

![Demo Screenshot](placeholder.png)

## 📖 概要
このシンプルなウェブアプリは、**上司と部下の人数を考慮した割り勘計算** を行います。総額を入力し、上司と部下それぞれの人数を指定するだけで、上司の支払額・部下の支払額・余り（積立金）を自動計算します。UI は iOS のデザイン言語を参考にした **モダンで洗練された** 見た目です。

## ✨ 主な機能
- 総額、上司人数、部下人数の入力
- 上司は部下より **1000円多く** 支払うロジック（日本の慣例に合わせた）
- 人数が 0 人の場合は自動で該当項目を非表示
- 100円単位に切り上げ、余りを自動算出し表示
- 入力値のバリデーション（負数・未入力チェック）
- スムーズなスクロール＆アニメーションで結果表示

## 🛠 前提条件・インストール
**環境**
- Windows 10/11（PowerShell が利用できること）
- 任意のモダンブラウザ（Chrome, Edge, Firefox など）
- Node.js (optional, only if you want to run a local dev server)

**インストール手順**
1. リポジトリをクローンまたはダウンロード
   ```powershell
   git clone https://github.com/your-user/warikan-app.git
   cd warikan-app
   ```
2. （オプション）ローカルサーバーで開発したい場合は npm を初期化
   ```powershell
   npm init -y
   npm install -D http-server   # 任意のローカルサーバー
   ```
3. 依存関係は特にありません。HTML、CSS、JS のファイルだけで完結しています。

## 🚀 ローカル起動・使い方
### 1. 手軽にブラウザで開く（推奨）
`warikan-app` ディレクトリで以下のファイルを直接開くだけです。
- `index.html`
- `style.css`
- `script.js`

```powershell
start .\index.html   # PowerShell でデフォルトブラウザが立ち上がります
```

### 2. ローカルサーバーで起動（開発向け）
```powershell
npx http-server . -p 8080
# または
npx -y http-server . -p 8080   # 事前インストールが不要な場合
```
ブラウザで `http://localhost:8080` にアクセスするとアプリが表示されます。

### 使用例
1. **総額** に `15000` を入力
2. **上司の人数** に `2`、**部下の人数** に `3` を入力
3. **計算する** ボタンをクリック

結果例:
- 上司の支払額: **5,000 円**（上司 2 人）
- 部下の支払額: **3,000 円**（部下 3 人）
- 余り（積立金）: **0 円**

## 🧰 テックスタック
| カテゴリ | 使用技術 |
|----------|-----------|
| 言語 | HTML5, CSS3, JavaScript (ES6) |
| フレームワーク | なし（Vanilla） |
| ビルドツール | なし（シンプル構成） |
| デザイン | カスタム CSS、Google Fonts (Noto Sans JP) |
| テスト | 手動テスト（ブラウザ） |

## 📂 ディレクトリ構成
```
warikan-app/
├─ index.html      # メイン HTML
├─ style.css       # UI スタイル（iOS テーマ）
└─ script.js       # 計算ロジック & UI 制御
```

## 📄 ライセンス
MIT ライセンス。自由に改変・再配布が可能です。

---
**Powered by Antigravity** – your AI‑assisted development partner.
