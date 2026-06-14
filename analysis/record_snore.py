import serial
import datetime
import csv
import time

PORT = "COM7"          # ← M5GOのCOMポート番号（前回COM7でしたよね）
BAUD = 115200          # ← UIFlow2のデフォルト通信速度
THRESHOLD = 2500       # ← ここは後で調整。いびき判定の仮の閾値

print(f"記録開始... {PORT} で接続中")
print("Ctrl+C で停止")

filename = datetime.datetime.now().strftime("snore_%Y%m%d_%H%M%S.csv")

with open(filename, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "level", "snoring"])  # ヘッダー

    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        while True:
            try:
                line = ser.readline().decode("utf-8").strip()
                if line.isdigit():
                    level = int(line)
                    snoring = 1 if level > THRESHOLD else 0
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    writer.writerow([ts, level, snoring])
                    f.flush()   # ← 即座にファイルに書く（途中で止めても消えない）
                    print(f"{ts}  音量:{level:6d}  いびき:{snoring}")
            except KeyboardInterrupt:
                print("記録終了")
                break
            except Exception:
                pass

print(f"保存完了: {filename}")