#!/usr/bin/env python3
"""
Claude Code と Gemini CLI の統合用MCPサーバー
初心者向けシンプル版
"""

import asyncio
import subprocess
import json
import sys
import time
from typing import Dict, Any, Tuple

class DebateError(Exception):
    """討論中のカスタムエラー"""
    pass

class AIDebateOrchestrator:
    def __init__(self):
        self.claude_available = self._check_command("claude")
        self.gemini_available = self._check_command("gemini")
        
    def _check_command(self, command: str) -> bool:
        """コマンドが利用可能かチェック"""
        try:
            subprocess.run([command, "--help"], 
                         capture_output=True, 
                         check=True, 
                         timeout=10)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
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
                
                stdout, stderr = await process.communicate(stdin_prompt.encode())
                
                if process.returncode == 0 and stdout:
                    response = stdout.decode().strip()
                    end_time = time.monotonic()
                    return response, end_time - start_time
                else:
                    stderr_msg = stderr.decode().strip()
                    if stderr_msg:
                        last_error = f"{ai_name}エラー: {stderr_msg}"
                    else:
                        last_error = f"{ai_name}エラー: プロセスが不明なエラーで終了しました (コード: {process.returncode})。標準エラーは空です。"

            except Exception as e:
                last_error = f"{ai_name}実行エラー: {str(e)}"

            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                print(f"  ⚠️ {ai_name}への接続に失敗しました。エラー: {last_error}")
                print(f"  ➡️ {wait_time}秒後に再試行します... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)

        raise DebateError(f"{ai_name}に複数回接続できませんでした。最終エラー: {last_error}")

    async def ask_claude(self, prompt: str) -> Tuple[str, float]:
        """Claude Codeに質問"""
        if not self.claude_available:
            raise DebateError("Claude Codeが利用できません")
        return await self._ask_ai_with_retry("Claude", ["claude", "-p", prompt], "")

    async def ask_gemini(self, prompt: str) -> Tuple[str, float]:
        """Gemini CLIに質問"""
        if not self.gemini_available:
            raise DebateError("Gemini CLIが利用できません")
        return await self._ask_ai_with_retry("Gemini", ["gemini", "-p", prompt], "")

    async def conduct_debate(self, topic: str, rounds: int = 3) -> Dict[str, Any]:
        """討論を実行"""
        debate_log = {
            "topic": topic,
            "rounds": rounds,
            "exchanges": [],
            "summary": ""
        }
        
        claude_context = ""
        gemini_context = ""
        
        print(f"🎯 討論開始: {topic}")
        print(f"📊 ラウンド数: {rounds}")
        print("=" * 50)
        
        try:
            for round_num in range(1, rounds + 1):
                print(f"\n🔥 ラウンド {round_num}")
                
                claude_prompt = f"""討論テーマ: {topic}\n\nラウンド {round_num} / {rounds}\n\n{claude_context}\n\n簡潔で論理的な意見を150-200文字で述べてください。"""
                print("🤖 Claude Code の応答を待機中...")
                claude_response, claude_time = await self.ask_claude(claude_prompt)
                print(f"💭 Claude: {claude_response[:100]}... ({claude_time:.2f}秒)")
                
                await asyncio.sleep(3)
                
                gemini_prompt = f"""討論テーマ: {topic}\n\nClaude Codeの意見: {claude_response}\n\n{gemini_context}\n\nClaude Codeとは異なる視点から、簡潔で論理的な意見を150-200文字で述べてください。"""
                print("🧠 Gemini CLI の応答を待機中...")
                gemini_response, gemini_time = await self.ask_gemini(gemini_prompt)
                print(f"🎯 Gemini: {gemini_response[:100]}... ({gemini_time:.2f}秒)")
                
                debate_log["exchanges"].append({
                    "round": round_num,
                    "claude": claude_response,
                    "claude_time": claude_time,
                    "gemini": gemini_response,
                    "gemini_time": gemini_time
                })
                
                claude_context = f"前のラウンドでGeminiは: {gemini_response}"
                gemini_context = f"あなたの前の意見: {gemini_response}"
                
                if round_num < rounds:
                    print("⏳ 次のラウンドまで5秒待機...")
                    await asyncio.sleep(5)
            
            print("\n📝 討論要約を生成中...")
            summary_prompt = f"""以下は「{topic}」についての討論です。\n\n{self._format_debate_for_summary(debate_log)}\n\nこの討論の要約と結論を300文字程度で述べてください。"""
            summary, _ = await self.ask_gemini(summary_prompt)
            debate_log["summary"] = summary

        except DebateError as e:
            print(f"\n❌ 討論が中断されました: {e}")
            debate_log["summary"] = f"討論はエラーにより中断されました: {e}"
        
        print(f"\n🎉 討論完了！")
        if debate_log["summary"]:
            print(f"📄 要約: {debate_log['summary']}")
        
        return debate_log
    
    def _format_debate_for_summary(self, debate_log: Dict[str, Any]) -> str:
        """討論ログを要約用にフォーマット"""
        formatted = ""
        for exchange in debate_log["exchanges"]:
            formatted += f"ラウンド {exchange['round']}:\n"
            formatted += f"Claude: {exchange['claude']}\n"
            formatted += f"Gemini: {exchange['gemini']}\n\n"
        return formatted
    
    def save_debate_log_as_markdown(self, debate_log: Dict[str, Any], filename: str = None):
        """討論ログをMarkdownファイルに保存"""
        if filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debate_log_{timestamp}.md"
        
        markdown_content = f"# 討論ログ: {debate_log['topic']}\n\n"
        
        for exchange in debate_log['exchanges']:
            markdown_content += f"## ラウンド {exchange['round']}\n\n"
            markdown_content += f"### 🤖 Claudeの意見\n"
            markdown_content += f"> {exchange['claude']}\n\n"
            markdown_content += f"*応答時間: {exchange['claude_time']:.2f}秒*\n\n"
            markdown_content += f"### 🧠 Geminiの意見\n"
            markdown_content += f"> {exchange['gemini']}\n\n"
            markdown_content += f"*応答時間: {exchange['gemini_time']:.2f}秒*\n\n"
            markdown_content += "---\n\n"
            
        markdown_content += f"## 📄 要約\n\n"
        markdown_content += f"{debate_log['summary']}\n"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"💾 討論ログをMarkdownで保存しました: {filename}")

async def main():
    """メイン実行関数"""
    if len(sys.argv) < 2:
        print("使用方法: python ai_debate.py '討論テーマ' [ラウンド数]")
        print("例: python ai_debate.py 'AIの倫理的課題について' 5")
        sys.exit(1)
    
    topic = sys.argv[1]
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    orchestrator = AIDebateOrchestrator()
    
    if not orchestrator.claude_available:
        print("⚠️  Claude Codeが利用できません。インストールと認証を確認してください。")
    
    if not orchestrator.gemini_available:
        print("⚠️  Gemini CLIが利用できません。インストールと認証を確認してください。")
    
    if not (orchestrator.claude_available and orchestrator.gemini_available):
        print("❌ 両方のツールが必要です。")
        sys.exit(1)
    
    try:
        debate_log = await orchestrator.conduct_debate(topic, rounds)
        orchestrator.save_debate_log_as_markdown(debate_log)
        
    except KeyboardInterrupt:
        print("\n⏹️  討論が中断されました。")
    except Exception as e:
        print(f"❌ 予期せぬエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())