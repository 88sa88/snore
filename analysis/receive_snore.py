"""WiFi経由でM5Stackの音量データを受信してCSVに記録する（フェーズ0：生データ収集）.

仕組み:
  M5Stack --WiFi(HTTP POST)--> Windows:8000 --netsh portproxy--> WSL:8000 (このサーバー)

実行（WSL側）:
  uv run python analysis/receive_snore.py

M5側はHTTPのPOST本文に音量の整数値を1行で送る想定（例: "2731"）。
CSVは record_snore.py と同じ形式なので、既存のノートブックでそのまま解析できる。
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import datetime
import csv

HOST = "0.0.0.0"   # ← 127.0.0.1 だと portproxy 経由で届かないので注意
PORT = 8000

# フェーズ0は「生データを貯める」のが目的なので、snoring列は仮の閾値で埋める。
# 本当の閾値はフェーズ1でCSVを解析してから決める（この値は後で無視してOK）。
PROVISIONAL_THRESHOLD = 2500

# 実行場所に関係なく、プロジェクト直下の data/ に保存する。
# （このファイルは analysis/ にあるので、親の親 = プロジェクトルート）
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

filename = DATA_DIR / datetime.datetime.now().strftime("snore_%Y%m%d_%H%M%S.csv")
_f = open(filename, "w", newline="")
_writer = csv.writer(_f)
_writer.writerow(["timestamp", "level", "snoring"])
_f.flush()

print(f"受信開始... {HOST}:{PORT} で待ち受け中")
print(f"保存先: {filename}")
print("Ctrl+C で停止")


class SnoreHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8").strip()
            # 本文が「数字だけ」のときのみ記録（不正データは捨てる）
            if body.lstrip("-").isdigit():
                level = int(body)
                snoring = 1 if level > PROVISIONAL_THRESHOLD else 0
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _writer.writerow([ts, level, snoring])
                _f.flush()  # 途中で止めても消えないよう即書き込み
                print(f"{ts}  音量:{level:6d}  いびき(仮):{snoring}")
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            print(f"受信エラー: {e}")
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass  # アクセスログを抑制（音量ログだけ見せる）


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), SnoreHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n記録終了")
    finally:
        server.server_close()
        _f.close()
        print(f"保存完了: {filename}")
