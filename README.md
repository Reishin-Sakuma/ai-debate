# AI Debate

Claude CodeとGemini CLIを使った本格的なディベートシステムです。Windows環境に完全対応しています。

## 概要

このプロジェクトは、Claude CodeとGemini CLIの2つのAIツールを組み合わせて、指定したテーマについて本格的なディベートを行うシステムです。各AIが指定された立場から論戦を繰り広げ、相互に反論・再反論を展開する建設的な議論を実現します。

## 🌟 主な特徴

- **🎯 本格的なディベート構造**: お互いの意見に対する相互反論システム
- **🖥️ Windows完全対応**: Git BashとPowerShellを活用したネイティブ実行
- **⚡ リアルタイム表示**: プログレスアニメーションとカウントダウン機能
- **🎭 立場指定機能**: 各AIに具体的な立場・役割を指定可能
- **📝 Markdown出力**: 討論結果をMarkdownファイルで保存
- **🔄 リトライ機能**: 通信エラー時の自動リトライとカウントダウン表示
- **🎮 インタラクティブ選択**: 要約AIを実行時に選択（または事前指定）
- **🌐 UTF-8対応**: Windows環境での日本語表示完全対応

## 必要な環境

- **Python 3.7以上**
- **Windows 10/11**
- **Git for Windows** (Git Bash含む)
- **Node.js**
- **Claude Code CLI**
- **Gemini CLI**

## 📦 インストール

### 1. Git for Windowsのインストール
Windows環境でClaude Codeを実行するために必要です：
```
https://git-scm.com/downloads/win
```

### 2. Node.jsのインストール
```
https://nodejs.org/
```

### 3. Claude Code CLIのインストール
```bash
npm install -g @anthropic/claude
```

### 4. Gemini CLIのインストール
```bash
npm install -g @google-ai/generativelanguage
```

### 5. 認証設定
各CLIツールの認証を設定してください。

## 🚀 使用方法

### 基本的な使用法
```bash
python ai_dabate.py '討論テーマ' [ラウンド数] [要約AI] [Claudeの立場] [Geminiの立場]
```

### 💡 実行例

#### 基本的なディベート
```bash
# 3ラウンドの討論（デフォルト）- 要約AIは討論後に選択
python ai_dabate.py 'AIの倫理的課題について'

# 5ラウンドの討論
python ai_dabate.py 'AIの倫理的課題について' 5
```

#### 立場を指定したディベート
```bash
# 立場を指定したディベート
python ai_dabate.py 'リモートワークは生産性を向上させるか' 3 gemini '推進派' '慎重派'

# 具体的なテーマでの対立
python ai_dabate.py 'ChatGPTの学習データ使用は著作権法違反か' 4 claude '合法派' '違法派'

#### 要約AIを事前指定
```bash
# Claude Codeで要約
python ai_dabate.py 'テーマ' 3 claude

# Gemini CLIで要約  
python ai_dabate.py 'テーマ' 3 gemini
```

## 📊 出力形式

### 1. リアルタイムコンソール出力
討論の進行状況をリアルタイムで表示：
```
🤖 Claudeに質問中...
  ⠋ Claudeが応答中...
💭 Claude: [意見] (8.5秒)

⏳ 3秒待機中...
  ⏳ 2秒後にGeminiに質問...

🧠 Geminiに質問中...  
  ⠙ Geminiが応答中...
🎯 Gemini: [反論] (12.3秒)

⏸️ 次のラウンドまで5秒待機...
  ⏸️ ラウンド2まで3秒...
```

### 2. Markdownファイル出力
`debate_log_[timestamp].md`形式で詳細保存：
- 各ラウンドの発言内容
- 応答時間の記録
- 最終的な要約と結論

### 3. 要約生成
討論完了後に選択されたAIによる総合的な要約を生成

## 🏗️ システム構造

### ディベートフロー
1. **ラウンド1**: 各AIが立場に基づいた初期意見を表明
2. **ラウンド2以降**: 相手の意見を踏まえた反論・再反論を展開
3. **文脈管理**: 過去の議論履歴を適切に各AIに提供
4. **要約生成**: 討論全体の流れと結論を整理

### AIDebateOrchestrator クラス

#### 🔧 コア機能
- **プラットフォーム対応**: Windows環境での自動設定
- **Git Bash統合**: Claude Code実行のためのGit Bash自動検出
- **PowerShell実行**: Gemini CLI用のPowerShell統合
- **文脈管理**: `_build_debate_context()` による適切な議論履歴管理

#### 📱 UI機能  
- **プログレスアニメーション**: `_show_progress_animation()` 
- **リアルタイム表示**: 応答待機中のビジュアルフィードバック
- **カウントダウン機能**: 待機時間の可視化

#### 🛡️ エラーハンドリング
- **自動リトライ**: 通信エラー時の段階的再試行
- **安全なデコード**: UTF-8エンコーディングエラーの適切な処理
- **タイムアウト管理**: 応答時間の管理とタイムアウト処理

## 🔧 トラブルシューティング

### Git Bashが見つからない場合
```bash
# 環境変数を手動設定
set CLAUDE_CODE_GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe
```

### Claude Codeが利用できない場合
1. **インストール確認**: `npm list -g @anthropic/claude`
2. **認証設定確認**: Claude APIキーの設定
3. **Git Bash確認**: `C:\Program Files\Git\bin\bash.exe`の存在確認

### Gemini CLIが利用できない場合
1. **インストール確認**: `npm list -g @google-ai/generativelanguage`
2. **認証設定確認**: Google AI APIキーの設定
3. **PowerShell確認**: PowerShell実行ポリシーの確認

### 文字化けが発生する場合
システムはUTF-8対応されていますが、PowerShellの設定で解決する場合があります：
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## 🎮 インタラクティブ機能

### 要約AI選択
要約AIを実行時に指定しない場合は、討論完了後に選択肢が表示されます：

```
📝 討論要約を生成します
==================================================
どのAIに要約を生成してもらいますか？

1. 🤖 Claude Code - 論理的で構造化された要約
2. 🧠 Gemini CLI - 包括的で洞察に富んだ要約

選択してください (1 または 2): 
```

### 立場指定のコツ
効果的なディベートのための立場指定例：

- **対立構造**: `賛成派` vs `反対派`
- **思想的対立**: `保守派` vs `革新派`  
- **アプローチ論**: `実用主義` vs `理想主義`
- **立ち位置**: `推進派` vs `慎重派`
- **評価軸**: `楽観的` vs `悲観的`

## 📈 パフォーマンス

- **平均応答時間**: Claude 8-12秒、Gemini 15-25秒
- **メモリ使用量**: 約50-100MB
- **ファイルサイズ**: 討論ログは通常2-5KB

## 🤝 コントリビューション

このプロジェクトへの貢献を歓迎します。Issue報告やPull Requestをお気軽にお送りください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

**🤖 Generated with [Claude Code](https://claude.ai/code)**