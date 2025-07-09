# AI Debate

Claude CodeとGemini CLIを使った自動討論システムです。WSL環境で動作します。

## 概要

このプロジェクトは、Claude CodeとGemini CLIの2つのAIツールを組み合わせて、指定したテーマについて自動的に討論を行うシステムです。各AIが異なる視点から意見を述べ、建設的な議論を展開します。

## 特徴

- **自動討論**: 2つのAIが自動的に討論を進行
- **WSL最適化**: WSL環境での実行に最適化
- **Markdown出力**: 討論結果をMarkdownファイルで保存
- **リトライ機能**: 通信エラー時の自動リトライ
- **動的パス検出**: Node.jsやCLIツールのパスを自動検出

## 必要な環境

- Python 3.7以上
- WSL/Linux環境
- Node.js
- Claude Code CLI
- Gemini CLI

## インストール

1. Claude Code CLIをインストール:
```bash
npm install -g @anthropic-ai/claude-code
```

2. Gemini CLIをインストール:
```bash
npm install -g @google/gemini-cli
```

3. 各CLIツールの認証を設定してください。

## 使用方法

```bash
python ai_dabate.py '討論テーマ' [ラウンド数]
```

### 例

```bash
# 3ラウンドの討論（デフォルト）
python ai_dabate.py 'AIの倫理的課題について'

# 5ラウンドの討論
python ai_dabate.py 'AIの倫理的課題について' 5
```

## 出力

討論の結果は以下の形式で出力されます：

1. **コンソール出力**: リアルタイムで討論の進行状況を表示
2. **Markdownファイル**: `debate_log_[timestamp].md`形式で詳細な討論ログを保存

## 主な機能

### AIDebateOrchestrator クラス

- **動的パス検出**: WSL環境でのNode.jsやCLIツールのパスを自動検出
- **エラーハンドリング**: 通信エラー時の自動リトライ機能
- **安全なデコード**: 文字エンコーディングエラーの適切な処理
- **討論管理**: 複数ラウンドの討論進行とログ管理

### 主要メソッド

- `conduct_debate()`: 討論の実行
- `ask_claude()`: Claude Codeへの質問
- `ask_gemini()`: Gemini CLIへの質問
- `save_debate_log_as_markdown()`: 討論ログのMarkdown保存

## トラブルシューティング

### Claude Codeが利用できない場合

1. インストールを確認: `npm list -g @anthropic-ai/claude-code`
2. 認証設定を確認
3. パスが正しく設定されているか確認

### Gemini CLIが利用できない場合

1. インストールを確認: `npm list -g @google/gemini-cli`
2. 認証設定を確認
3. パスが正しく設定されているか確認

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。