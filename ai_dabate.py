#!/usr/bin/env python3
"""
Claude Code と Gemini CLI の統合用MCPサーバー
WSL内で完結するCLIモード
"""

import asyncio
import subprocess
import sys
import time
from typing import Dict, Any, Tuple, Callable

class DebateError(Exception):
    """討論中のカスタムエラー"""
    pass

class AIDebateOrchestrator:
    def __init__(self, log_callback: Callable[[str], None] = None):
        # まず最初にlog_callbackを設定
        self.log_callback = log_callback
        
        # ツール検出（WSL内で直接実行）
        self.node_path = self._get_command_path("node")
        self.claude_path = self._get_command_path("claude")
        self.gemini_path = self._get_command_path("gemini")
        self.claude_available = self.claude_path is not None
        self.gemini_available = self.gemini_path is not None

    def _log(self, message: str):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def _safe_decode(self, byte_data: bytes) -> str:
        """バイトデータを安全にデコード"""
        if not byte_data:
            return ""
        
        # UTF-8でデコード
        try:
            return byte_data.decode('utf-8').strip()
        except UnicodeDecodeError:
            # 失敗した場合はerrorsパラメータを使用
            return byte_data.decode('utf-8', errors='replace').strip()


    def _get_command_path(self, command: str) -> str:
        """コマンドのフルパスを取得（WSL内で実行）"""
        approaches = [
            ["bash", "-l", "-c", f"which {command}"],
            ["which", command],
            ["bash", "-c", f"source ~/.bashrc && which {command}"],
            ["bash", "-c", f"ls ~/.nvm/versions/node/*/bin/{command} 2>/dev/null | head -1"],
        ]
        
        for cmd_args in approaches:
            try:
                result = subprocess.run(cmd_args, capture_output=True, check=True, timeout=10)
                full_path = self._safe_decode(result.stdout)
                if full_path and full_path != "":
                    self._log(f"✅ {command}のパスを発見: {full_path}")
                    return full_path
            except:
                continue
        
        self._log(f"❌ {command}のパスを取得できませんでした")
        return None


    async def _ask_ai_with_retry(self, ai_name: str, command_args: list[str], stdin_prompt: str, max_retries: int = 3) -> Tuple[str, float]:
        """AIに質問し、応答と所要時間を返す（リトライ機能付き）"""
        start_time = time.monotonic()
        last_error = ""

        for attempt in range(max_retries):
            try:
                
                process = await asyncio.create_subprocess_exec(
                    *command_args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # 応答待機
                stdout, stderr = await process.communicate(stdin_prompt.encode())
                
                stdout_msg = self._safe_decode(stdout)
                stderr_msg = self._safe_decode(stderr)
                
                if process.returncode == 0 and stdout:
                    response = stdout_msg
                    end_time = time.monotonic()
                    return response, end_time - start_time
                else:
                    if stderr_msg:
                        last_error = f"{ai_name}エラー: {stderr_msg}"
                    else:
                        last_error = f"{ai_name}エラー: プロセスが不明なエラーで終了しました (コード: {process.returncode})。標準出力: {stdout_msg[:100]}"
            except Exception as e:
                last_error = f"{ai_name}実行エラー: {str(e)}"

            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                self._log(f"  ⚠️ {ai_name}への接続に失敗。{wait_time}秒後に再試行...")
                await asyncio.sleep(wait_time)

        raise DebateError(f"{ai_name}に複数回接続できませんでした。最終エラー: {last_error}")

    async def ask_claude(self, prompt: str) -> Tuple[str, float]:
        """Claude Codeに質問"""
        if not self.claude_available:
            raise DebateError("Claude Codeが利用できません")
        
        # WSL内で直接実行
        if self.node_path:
            # Node.jsの絶対パスを使用して実行
            escaped_prompt = prompt.replace('"', '\\"')  # ダブルクォートをエスケープ
            command_args = ["bash", "-l", "-c", f'"{self.node_path}" "{self.claude_path}" --print "{escaped_prompt}"']
        else:
            # Node.jsパスが見つからない場合は環境変数読み込みを試行
            escaped_prompt = prompt.replace("'", "'\"'\"'")
            command_args = ["bash", "-l", "-c", f"{self.claude_path} --print '{escaped_prompt}'"]
        
        return await self._ask_ai_with_retry("Claude", command_args, "")

    async def ask_gemini(self, prompt: str) -> Tuple[str, float]:
        """Gemini CLIに質問"""
        if not self.gemini_available:
            raise DebateError("Gemini CLIが利用できません")
        
        # WSL内で直接実行
        if self.node_path:
            # Node.jsの絶対パスを使用して実行
            escaped_prompt = prompt.replace('"', '\\"')  # ダブルクォートをエスケープ
            command_args = ["bash", "-l", "-c", f'"{self.node_path}" "{self.gemini_path}" --prompt "{escaped_prompt}"']
        else:
            # Node.jsパスが見つからない場合は環境変数読み込みを試行
            escaped_prompt = prompt.replace("'", "'\"'\"'")
            command_args = ["bash", "-l", "-c", f"{self.gemini_path} --prompt '{escaped_prompt}'"]
        
        return await self._ask_ai_with_retry("Gemini", command_args, "")

    async def conduct_debate(self, topic: str, rounds: int = 3, summary_ai: str = None) -> Dict[str, Any]:
        """討論を実行"""
        debate_log = {"topic": topic, "rounds": rounds, "exchanges": [], "summary": ""}
        claude_context = ""
        gemini_context = ""

        self._log(f"🎯 討論開始: {topic}")
        self._log(f"📊 ラウンド数: {rounds}")
        self._log("=" * 50)

        try:
            for round_num in range(1, rounds + 1):
                self._log(f"\n🔥 ラウンド {round_num}")
                claude_prompt = f'討論テーマ: {topic}\n\nラウンド {round_num} / {rounds}\n\n{claude_context}\n\n簡潔で論理的な意見を150-200文字で述べてください。'
                claude_response, claude_time = await self.ask_claude(claude_prompt)
                self._log(f"💭 Claude: {claude_response} ({claude_time:.2f}秒)")

                await asyncio.sleep(3)

                gemini_prompt = f'討論テーマ: {topic}\n\nClaude Codeの意見: {claude_response}\n\n{gemini_context}\n\nClaude Codeとは異なる視点から、簡潔で論理的な意見を150-200文字で述べてください。'
                gemini_response, gemini_time = await self.ask_gemini(gemini_prompt)
                self._log(f"🎯 Gemini: {gemini_response} ({gemini_time:.2f}秒)")

                debate_log["exchanges"].append({
                    "round": round_num,
                    "claude": claude_response, "claude_time": claude_time,
                    "gemini": gemini_response, "gemini_time": gemini_time
                })
                claude_context = f"前のラウンドでGeminiは: {gemini_response}"
                gemini_context = f"あなたの前の意見: {gemini_response}"

                if round_num < rounds:
                    await asyncio.sleep(5)

            # 要約AI選択がされていない場合はインタラクティブに選択
            if summary_ai is None:
                summary_ai = self._get_interactive_summary_choice()
            
            self._log("\n📝 討論要約を生成中...")
            summary_prompt = f'以下は「{topic}」についての討論です。\n\n{self._format_debate_for_summary(debate_log)}\n\nこの討論の要約と結論を300文字程度で述べてください。'
            
            if summary_ai.lower() == "claude":
                self._log("🤖 Claudeが要約を生成中...")
                summary, _ = await self.ask_claude(summary_prompt)
            else:
                self._log("🧠 Geminiが要約を生成中...")
                summary, _ = await self.ask_gemini(summary_prompt)
            
            debate_log["summary"] = summary

        except DebateError as e:
            self._log(f"\n❌ 討論が中断されました: {e}")
            debate_log["summary"] = f"討論はエラーにより中断されました: {e}"

        self._log(f"\n🎉 討論完了！")
        if debate_log["summary"]:
            self._log(f"📄 要約: {debate_log['summary']}")

        return debate_log

    def _format_debate_for_summary(self, debate_log: Dict[str, Any]) -> str:
        """討論ログを要約用にフォーマット"""
        formatted = ""
        for exchange in debate_log["exchanges"]:
            formatted += f"ラウンド {exchange['round']}:\n"
            formatted += f"Claude: {exchange['claude']}\n"
            formatted += f"Gemini: {exchange['gemini']}\n\n"
        return formatted

    def _get_interactive_summary_choice(self) -> str:
        """インタラクティブに要約AIを選択"""
        print("\n" + "="*50)
        print("📝 討論要約を生成します")
        print("="*50)
        print("どのAIに要約を生成してもらいますか？")
        print("")
        print("1. 🤖 Claude Code - 論理的で構造化された要約")
        print("2. 🧠 Gemini CLI - 包括的で洞察に富んだ要約")
        print("")
        
        while True:
            try:
                choice = input("選択してください (1 または 2): ").strip()
                if choice == "1":
                    print("\n✅ Claude Codeが要約を生成します。\n")
                    return "claude"
                elif choice == "2":
                    print("\n✅ Gemini CLIが要約を生成します。\n")
                    return "gemini"
                else:
                    print("❌ 1 または 2 を選択してください。")
            except (EOFError, KeyboardInterrupt):
                print("\n\n⏹️  デフォルトでGeminiを選択します。")
                return "gemini"
    
    def save_debate_log_as_markdown(self, debate_log: Dict[str, Any], filename: str = None):
        """討論ログをMarkdownファイルに保存"""
        if filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debate_log_{timestamp}.md"
        
        markdown_content = f"# 討論ログ: {debate_log['topic']}\n\n"
        for exchange in debate_log['exchanges']:
            markdown_content += f"## ラウンド {exchange['round']}\n\n"
            markdown_content += f"### 🤖 Claudeの意見\n> {exchange['claude']}\n\n*応答時間: {exchange['claude_time']:.2f}秒*\n\n"
            markdown_content += f"### 🧠 Geminiの意見\n> {exchange['gemini']}\n\n*応答時間: {exchange['gemini_time']:.2f}秒*\n\n---\n\n"
        markdown_content += f"## 📄 要約\n\n{debate_log['summary']}\n"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        self._log(f"💾 討論ログをMarkdownで保存しました: {filename}")


async def run_cli(topic: str, rounds: int, summary_ai: str = None):
    """CLIモードで討論を実行"""
    orchestrator = AIDebateOrchestrator()
    
    # 実行環境を表示
    print(f"🖥️ 実行環境: WSL/Linux")
    
    # ツールの状態をチェック
    if not orchestrator.claude_available:
        print(f"⚠️  Claude Codeが利用できません。インストールと認証を確認してください。")
    if not orchestrator.gemini_available:
        print(f"⚠️  Gemini CLIが利用できません。インストールと認証を確認してください。")
    if not (orchestrator.claude_available and orchestrator.gemini_available):
        print("❌ 両方のツールが必要です。")
        sys.exit(1)
    
    try:
        debate_log = await orchestrator.conduct_debate(topic, rounds, summary_ai)
        orchestrator.save_debate_log_as_markdown(debate_log)
    except KeyboardInterrupt:
        print("\n⏹️  討論が中断されました。")
    except Exception as e:
        print(f"❌ 予期せぬエラーが発生しました: {str(e)}")

def main():
    """CLIモードのみで実行"""
    if len(sys.argv) < 2:
        print("使用方法: python ai_debate.py '討論テーマ' [ラウンド数] [要約AI]")
        print("例: python ai_debate.py 'AIの倫理的課題について' 5 claude")
        print("要約AI: claude または gemini (省略時は討論後に選択)")
        sys.exit(1)
    
    topic = sys.argv[1]
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    summary_ai = sys.argv[3] if len(sys.argv) > 3 else None
    
    if summary_ai is not None and summary_ai.lower() not in ["claude", "gemini"]:
        print("❌ 要約AIは 'claude' または 'gemini' を指定してください")
        sys.exit(1)
    
    asyncio.run(run_cli(topic, rounds, summary_ai))

if __name__ == "__main__":
    main()