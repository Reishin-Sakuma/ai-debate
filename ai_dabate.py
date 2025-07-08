#!/usr/bin/env python3
"""
Claude Code と Gemini CLI の統合用MCPサーバー
初心者向けシンプル版
"""

import asyncio
import subprocess
import json
import sys
from typing import Dict, Any

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
    
    async def ask_claude(self, prompt: str) -> str:
        """Claude Codeに質問"""
        if not self.claude_available:
            return "Claude Codeが利用できません"
        
        try:
            # 非対話モードでClaude Codeを実行
            process = await asyncio.create_subprocess_exec(
                "claude", "--non-interactive",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(prompt.encode())
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                return f"Claude Codeエラー: {stderr.decode()}"
                
        except Exception as e:
            return f"Claude Code実行エラー: {str(e)}"
    
    async def ask_gemini(self, prompt: str) -> str:
        """Gemini CLIに質問"""
        if not self.gemini_available:
            return "Gemini CLIが利用できません"
        
        try:
            # 非対話モードでGemini CLIを実行
            process = await asyncio.create_subprocess_exec(
                "gemini", "-p", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                return f"Gemini CLIエラー: {stderr.decode()}"
                
        except Exception as e:
            return f"Gemini CLI実行エラー: {str(e)}"
    
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
        
        for round_num in range(1, rounds + 1):
            print(f"\n🔥 ラウンド {round_num}")
            
            # Claude Codeの意見取得
            claude_prompt = f"""討論テーマ: {topic}
            
ラウンド {round_num} / {rounds}

{claude_context}

簡潔で論理的な意見を150-200文字で述べてください。"""

            print("🤖 Claude Code の応答を待機中...")
            claude_response = await self.ask_claude(claude_prompt)
            print(f"💭 Claude: {claude_response[:100]}...")
            
            # 少し待機
            await asyncio.sleep(3)
            
            # Gemini CLIの意見取得
            gemini_prompt = f"""討論テーマ: {topic}

Claude Codeの意見: {claude_response}

{gemini_context}

Claude Codeとは異なる視点から、簡潔で論理的な意見を150-200文字で述べてください。"""

            print("🧠 Gemini CLI の応答を待機中...")
            gemini_response = await self.ask_gemini(gemini_prompt)
            print(f"🎯 Gemini: {gemini_response[:100]}...")
            
            # 討論ログに記録
            debate_log["exchanges"].append({
                "round": round_num,
                "claude": claude_response,
                "gemini": gemini_response
            })
            
            # 次のラウンドのコンテキスト更新
            claude_context = f"前のラウンドでGeminiは: {gemini_response}"
            gemini_context = f"あなたの前の意見: {gemini_response}"
            
            # ラウンド間の待機
            if round_num < rounds:
                print("⏳ 次のラウンドまで5秒待機...")
                await asyncio.sleep(5)
        
        # 討論の要約生成
        print("\n📝 討論要約を生成中...")
        summary_prompt = f"""以下は「{topic}」についての討論です。

{self._format_debate_for_summary(debate_log)}

この討論の要約と結論を300文字程度で述べてください。"""
        
        summary = await self.ask_gemini(summary_prompt)
        debate_log["summary"] = summary
        
        print(f"\n🎉 討論完了！")
        print(f"📄 要約: {summary}")
        
        return debate_log
    
    def _format_debate_for_summary(self, debate_log: Dict[str, Any]) -> str:
        """討論ログを要約用にフォーマット"""
        formatted = ""
        for exchange in debate_log["exchanges"]:
            formatted += f"ラウンド {exchange['round']}:\n"
            formatted += f"Claude: {exchange['claude']}\n"
            formatted += f"Gemini: {exchange['gemini']}\n\n"
        return formatted
    
    def save_debate_log(self, debate_log: Dict[str, Any], filename: str = None):
        """討論ログをファイルに保存"""
        if filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debate_log_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(debate_log, f, ensure_ascii=False, indent=2)
        
        print(f"💾 討論ログを保存しました: {filename}")

async def main():
    """メイン実行関数"""
    if len(sys.argv) < 2:
        print("使用方法: python ai_debate.py '討論テーマ' [ラウンド数]")
        print("例: python ai_debate.py 'AIの倫理的課題について' 5")
        sys.exit(1)
    
    topic = sys.argv[1]
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    orchestrator = AIDebateOrchestrator()
    
    # 利用可能性チェック
    if not orchestrator.claude_available:
        print("⚠️  Claude Codeが利用できません。インストールと認証を確認してください。")
    
    if not orchestrator.gemini_available:
        print("⚠️  Gemini CLIが利用できません。インストールと認証を確認してください。")
    
    if not (orchestrator.claude_available and orchestrator.gemini_available):
        print("❌ 両方のツールが必要です。")
        sys.exit(1)
    
    # 討論実行
    try:
        debate_log = await orchestrator.conduct_debate(topic, rounds)
        orchestrator.save_debate_log(debate_log)
        
    except KeyboardInterrupt:
        print("\n⏹️  討論が中断されました。")
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())