# アプリケーションの使い方

> 🏁 **Le Mans Ultimate 専用**

[![ダウンロード .EXE](https://img.shields.io/badge/⬇️%20ダウンロード%20.EXE-v1.0--beta-brightgreen?style=for-the-badge)](https://github.com/RomarioSantos-Oficial/SectorFlow-Setups/releases/tag/v1.0-beta)

**👉 [SectorFlowSetups.exe をダウンロード（Python 不要）](https://github.com/RomarioSantos-Oficial/SectorFlow-Setups/releases/tag/v1.0-beta)**

1. 上のリンクを開く
2. **Assets** セクションまでスクロール
3. `SectorFlowSetups.exe` をクリックしてダウンロード・実行

> Windows にブロックされた場合: 右クリック → プロパティ → **ブロックの解除** にチェック → OK

---

このガイドでは、Sector Flow Setups をユーザーとして使う手順を説明します。

## 1. このアプリでできること

1. Le Mans Ultimate のテレメトリをリアルタイムで読み取る
2. 車の挙動を分析する
3. ヒューリスティクスと AI によるセットアップ提案を受ける
4. ベースファイルを変更せずに新しい .svm を作成する
5. 走行データから継続的に学習する

## 2. 開始前の準備

### オプション A — .exe を使う（推奨・Python 不要）

| 要件 | 詳細 |
|---|---|
| 🖥️ OS | Windows 10 または 11（64-bit） |
| 🎮 ゲーム | **Le Mans Ultimate がインストール済み・起動中** |
| 📁 ベースファイル | LMU の `.svm` セットアップファイル |

[こちらから .exe をダウンロード](https://github.com/RomarioSantos-Oficial/SectorFlow-Setups/releases/tag/v1.0-beta)して、ダブルクリックで実行。

### オプション B — ソースから実行（開発者向け）

Python 3.10+ が必要:

```bash
pip install -r requirements.txt
python main.py
```

## 3. 手順

### 手順 1. アプリを起動する

**オプション A（推奨）:** `SectorFlowSetups.exe` をダブルクリック

**オプション B（開発者）:**
```bash
python main.py
```

### 手順 2. ゲーム接続を待つ

画面上部に LMU、AI、DB の状態が表示されます。

### 手順 3. ベースセットアップを読み込む

Setup タブで:

1. Load .svm をクリックする
2. ファイルを選ぶ
3. 読み込み完了を確認する

### 手順 4. コースを走る

何周か走ってテレメトリを集めます。

### 手順 5. テレメトリを確認する

Telemetry タブでは、ラップタイム、タイヤ、燃料、天候、ブレーキを確認できます。

### 手順 6. 提案を依頼する

方法は 3 つあります。

1. Setup チャットに入力する
2. AI 提案ボタンを使う
3. Heuristics ボタンを使う

### 手順 7. 提案を確認する

提案は Setup タブ右側に表示され、調整量と警告を確認できます。

### 手順 8. 詳細フィードバックを送る

Feedback タブでは、アンダーステア、オーバーステア、ブレーキ、トラクション、剛性、タイヤ摩耗を細かく伝えられます。

### 手順 9. 新しいセットアップを作成する

1. Create Setup をクリックする
2. モードを選ぶ
3. 天候条件を選ぶ
4. 作成を確定する

### 手順 10. 既存セットアップを編集する

1. Edit Setup をクリックする
2. .svm ファイルを選ぶ
3. バックアップ作成を確認する
4. 提案を依頼する
5. 調整を適用する

## 4. 言語対応

英語、スペイン語、日本語、中国語で表示することは可能ですが、現在の GUI テキストはまだポルトガル語で固定されています。

実装に必要なもの:

1. すべての UI 文言を一箇所に集約する
2. 翻訳ファイルを作る
3. 言語選択メニューを追加する
4. 選択した言語でラベルとメッセージを切り替える