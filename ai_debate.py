#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code と Gemini CLI の統合用討論システム
Windows専用CLIモード
"""

import asyncio
import subprocess
import sys
import time
import os
import threading
from typing import Dict, Any, Tuple, Callable

# Windows環境でのUTF-8対応
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

class DebateError(Exception):
    """討論中のカスタムエラー"""
    pass

class AIDebateOrchestrator:
    def __init__(self, claude_stance: str = None, gemini_stance: str = None, log_callback: Callable[[str], None] = None):
        # まず最初にlog_callbackを設定
        self.log_callback = log_callback
        self.claude_stance = claude_stance
        self.gemini_stance = gemini_stance
        
        # Git Bash環境変数を設定
        self._setup_git_bash_env()
        
        # ツール検出（Windows専用）
        self.claude_available = self._check_command_available("claude")
        self.gemini_available = self._check_command_available("gemini")

    def _log(self, message: str):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def _setup_git_bash_env(self):
        """Git Bash環境変数を設定"""
        if 'CLAUDE_CODE_GIT_BASH_PATH' not in os.environ:
            # 一般的なGit Bashの場所を確認
            possible_paths = [
                r'C:\Program Files\Git\bin\bash.exe',
                r'C:\Program Files (x86)\Git\bin\bash.exe',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    os.environ['CLAUDE_CODE_GIT_BASH_PATH'] = path
                    self._log(f"Git Bash環境変数を設定: {path}")
                    break

    def _check_command_available(self, command: str) -> bool:
        """コマンドが利用可能かチェック"""
        try:
            # Windowsでは.cmdファイルを使用
            cmd_file = f"{command}.cmd"
            
            # whereコマンドでパスを確認
            result = subprocess.run(["where", cmd_file], capture_output=True, timeout=10)
            if result.returncode == 0:
                path = self._safe_decode(result.stdout).split('\n')[0].strip()
                if os.path.exists(path):
                    self._log(f"✅ {command}コマンドが利用可能です: {path}")
                    return True
            
            self._log(f"❌ {command}コマンドが利用できません")
            return False
        except Exception as e:
            self._log(f"❌ {command}コマンドが利用できません: {str(e)}")
            return False

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


    def _show_progress_animation(self, ai_name: str, stop_event: threading.Event):
        """AIの応答中にプログレスアニメーションを表示"""
        animation_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        idx = 0
        
        while not stop_event.is_set():
            sys.stdout.write(f"\r  {animation_chars[idx]} {ai_name}が応答中...")
            sys.stdout.flush()
            idx = (idx + 1) % len(animation_chars)
            time.sleep(0.1)
        
        # アニメーションをクリア
        sys.stdout.write("\r" + " " * 50 + "\r")
        sys.stdout.flush()

    async def _ask_ai_with_retry(self, ai_name: str, command_args: list[str], stdin_prompt: str, max_retries: int = 3) -> Tuple[str, float]:
        """AIに質問し、応答と所要時間を返す（リトライ機能付き）"""
        start_time = time.monotonic()
        last_error = ""

        for attempt in range(max_retries):
            try:
                # プログレスアニメーション開始
                stop_event = threading.Event()
                animation_thread = threading.Thread(target=self._show_progress_animation, args=(ai_name, stop_event))
                animation_thread.start()
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        *command_args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    # 応答待機
                    stdout, stderr = await process.communicate(stdin_prompt.encode())
                finally:
                    # アニメーション停止
                    stop_event.set()
                    animation_thread.join()
                
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
                
                # 再試行待機のカウントダウン表示
                for remaining in range(wait_time, 0, -1):
                    sys.stdout.write(f"\r  ⏳ {remaining}秒後に再試行...")
                    sys.stdout.flush()
                    await asyncio.sleep(1)
                sys.stdout.write("\r" + " " * 30 + "\r")
                sys.stdout.flush()

        raise DebateError(f"{ai_name}に複数回接続できませんでした。最終エラー: {last_error}")

    async def ask_claude(self, prompt: str) -> Tuple[str, float]:
        """Claude Codeに質問"""
        if not self.claude_available:
            raise DebateError("Claude Codeが利用できません")
        
        # Claude CodeはGit Bashで実行
        git_bash_path = os.environ.get('CLAUDE_CODE_GIT_BASH_PATH', r'C:\Program Files\Git\bin\bash.exe')
        if not os.path.exists(git_bash_path):
            # 一般的なgit-bashの場所を試す
            possible_paths = [
                r'C:\Program Files\Git\bin\bash.exe',
                r'C:\Program Files (x86)\Git\bin\bash.exe',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    git_bash_path = path
                    break
        
        # Git Bashでclaudeコマンドを実行
        escaped_prompt = prompt.replace('"', '\\"')
        command_args = [git_bash_path, "-c", f'claude --print "{escaped_prompt}"']
        return await self._ask_ai_with_retry("Claude", command_args, "")

    async def ask_gemini(self, prompt: str) -> Tuple[str, float]:
        """Gemini CLIに質問"""
        if not self.gemini_available:
            raise DebateError("Gemini CLIが利用できません")
        
        # WindowsでgeminiコマンドをPowerShellで実行
        # PowerShellでコマンドを実行
        escaped_prompt = prompt.replace('"', '""')  # PowerShellのエスケープ
        command_args = ["powershell", "-Command", f'gemini --prompt "{escaped_prompt}"']
        return await self._ask_ai_with_retry("Gemini", command_args, "")

    def _build_debate_context(self, exchanges: list, round_num: int, for_claude: bool) -> str:
        """ディベートの文脈を構築"""
        if round_num == 1:
            return ""
        
        context = "これまでの討論:\n"
        for i, exchange in enumerate(exchanges, 1):
            context += f"\nラウンド {i}:\n"
            if for_claude:
                context += f"あなた(Claude): {exchange['claude']}\n"
                context += f"相手(Gemini): {exchange['gemini']}\n"
            else:
                context += f"相手(Claude): {exchange['claude']}\n"
                context += f"あなた(Gemini): {exchange['gemini']}\n"
        
        return context

    async def conduct_debate(self, topic: str, rounds: int = 3, summary_ai: str = None) -> Dict[str, Any]:
        """討論を実行"""
        debate_log = {"topic": topic, "rounds": rounds, "exchanges": [], "summary": ""}

        self._log(f"🎯 討論開始: {topic}")
        self._log(f"📊 ラウンド数: {rounds}")
        self._log("=" * 50)

        try:
            for round_num in range(1, rounds + 1):
                self._log(f"\n🔥 ラウンド {round_num}")
                
                # Claudeのコンテキスト構築
                claude_context = self._build_debate_context(debate_log["exchanges"], round_num, for_claude=True)
                
                # Claudeのプロンプト生成
                claude_stance_instruction = f"あなたは「{self.claude_stance}」の立場で討論してください。\n" if self.claude_stance else ""
                
                if round_num == 1:
                    claude_instruction = "まず、あなたの立場から初期意見を述べてください。"
                else:
                    claude_instruction = "相手の意見を踏まえて、あなたの立場から反論・追加論点を述べてください。"
                
                claude_prompt = f'{claude_stance_instruction}討論テーマ: {topic}\n\nラウンド {round_num} / {rounds}\n\n{claude_context}\n\n{claude_instruction}\n簡潔で論理的な意見を150-200文字で述べてください。'
                
                print(f"🤖 Claudeに質問中...")
                claude_response, claude_time = await self.ask_claude(claude_prompt)
                print(f"💭 Claude: {claude_response} ({claude_time:.2f}秒)")

                print("⏳ 3秒待機中...")
                for i in range(3, 0, -1):
                    sys.stdout.write(f"\r  ⏳ {i}秒後にGeminiに質問...")
                    sys.stdout.flush()
                    await asyncio.sleep(1)
                sys.stdout.write("\r" + " " * 40 + "\r")
                sys.stdout.flush()

                # Geminiのコンテキスト構築（Claudeの最新意見を含む）
                gemini_context = self._build_debate_context(debate_log["exchanges"], round_num, for_claude=False)
                
                # Geminiのプロンプト生成
                gemini_stance_instruction = f"あなたは「{self.gemini_stance}」の立場で討論してください。\n" if self.gemini_stance else ""
                
                if round_num == 1:
                    gemini_instruction = "相手の意見に対して、あなたの立場から反論・対抗意見を述べてください。"
                else:
                    gemini_instruction = "相手の最新の反論を踏まえて、あなたの立場から再反論・追加論点を述べてください。"
                
                gemini_prompt = f'{gemini_stance_instruction}討論テーマ: {topic}\n\n{gemini_context}\n\n相手(Claude)の最新意見: {claude_response}\n\n{gemini_instruction}\n簡潔で論理的な意見を150-200文字で述べてください。'
                
                print(f"🧠 Geminiに質問中...")
                gemini_response, gemini_time = await self.ask_gemini(gemini_prompt)
                print(f"🎯 Gemini: {gemini_response} ({gemini_time:.2f}秒)")

                # 現在のラウンドの結果を記録
                debate_log["exchanges"].append({
                    "round": round_num,
                    "claude": claude_response, "claude_time": claude_time,
                    "gemini": gemini_response, "gemini_time": gemini_time
                })

                if round_num < rounds:
                    print(f"\n⏸️ 次のラウンドまで5秒待機...")
                    for i in range(5, 0, -1):
                        sys.stdout.write(f"\r  ⏸️ ラウンド{round_num + 1}まで{i}秒...")
                        sys.stdout.flush()
                        await asyncio.sleep(1)
                    sys.stdout.write("\r" + " " * 40 + "\r")
                    sys.stdout.flush()

            # 要約AI選択がされていない場合はインタラクティブに選択
            if summary_ai is None:
                summary_ai = self._get_interactive_summary_choice()
            
            print("\n📝 討論要約を生成中...")
            summary_prompt = f'以下は「{topic}」についての討論です。\n\n{self._format_debate_for_summary(debate_log)}\n\nこの討論の要約と結論を300文字程度で述べてください。'
            
            if summary_ai.lower() == "claude":
                print("🤖 Claudeが要約を生成中...")
                summary, summary_time = await self.ask_claude(summary_prompt)
                print(f"✅ 要約生成完了 ({summary_time:.2f}秒)")
            else:
                print("🧠 Geminiが要約を生成中...")
                summary, summary_time = await self.ask_gemini(summary_prompt)
                print(f"✅ 要約生成完了 ({summary_time:.2f}秒)")
            
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


async def run_cli(topic: str, rounds: int, summary_ai: str = None, claude_stance: str = None, gemini_stance: str = None):
    """CLIモードで討論を実行"""
    orchestrator = AIDebateOrchestrator(claude_stance=claude_stance, gemini_stance=gemini_stance)
    
    # 実行環境を表示
    print(f"🖥️ 実行環境: Windows")
    
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
        print("使用方法: python ai_debate.py '討論テーマ' [ラウンド数] [要約AI] [Claudeの立場] [Geminiの立場]")
        print("例: python ai_debate.py 'AIの倫理的課題について' 5 claude 賛成派 反対派")
        print("要約AI: claude または gemini (省略時は討論後に選択)")
        print("立場例: 賛成派/反対派、保守派/革新派、実用主義/理想主義")
        sys.exit(1)
    
    topic = sys.argv[1]
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    summary_ai = sys.argv[3] if len(sys.argv) > 3 else None
    claude_stance = sys.argv[4] if len(sys.argv) > 4 else None
    gemini_stance = sys.argv[5] if len(sys.argv) > 5 else None
    
    if summary_ai is not None and summary_ai.lower() not in ["claude", "gemini"]:
        print("❌ 要約AIは 'claude' または 'gemini' を指定してください")
        sys.exit(1)
    
    asyncio.run(run_cli(topic, rounds, summary_ai, claude_stance, gemini_stance))

if __name__ == "__main__":
    main()