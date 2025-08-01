import serial
import time
import csv
from datetime import datetime
import threading
import queue

# CONFIG
SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
MAX_RUNTIME_MIN = 30
MAX_REWARD_COUNT = 300
TRIAL_TIMEOUT = 15.0
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = f"data/tone_trial_log_{timestamp_str}.csv"

# Queue for passing trial results
trial_result_queue = queue.Queue()

def open_serial(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=0.1)
        time.sleep(2)
        print(f"[✓] Serial connected on {port}")
        return ser
    except serial.SerialException as e:
        print(f"[✗] Failed to open serial port: {e}")
        exit(1)

def send_trial(ser):
    ser.write(b'1')

def lick_listener(ser):
    buffer = b""
    while True:
        try:
            data = ser.read(ser.in_waiting or 1)
            if data:
                buffer += data
                if b'\n' in buffer:
                    lines = buffer.split(b'\n')
                    for line in lines[:-1]:
                        decoded = line.decode(errors='ignore').strip()
                        if decoded.startswith("Lick"):
                            print(f"[👅] {decoded}")
                        elif decoded.startswith("Tone"):
                            trial_result_queue.put(decoded)
                    buffer = lines[-1]
            time.sleep(0.001)
        except Exception as e:
            print(f"[⚠️] Listener error: {e}")

def log_trial(csv_writer, trial_num, result_string, elapsed_ms, reward_count):
    try:
        tone_type, reward_status, lick_info = result_string.split(",")
        lick_count = int(lick_info.split(":")[1])
    except Exception as e:
        print(f"[!] Parse error: {e}")
        tone_type, reward_status, lick_count = "Unknown", "None", 0

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    csv_writer.writerow([trial_num, tone_type, reward_status, timestamp, elapsed_ms, lick_count])

    elapsed_min = int(elapsed_ms // 60000)
    elapsed_sec = int((elapsed_ms % 60000) // 1000)
    reward_note = f" | Reward #{reward_count}" if reward_status == "Reward" else ""
    print(f"[✓] Trial {trial_num}: {tone_type} | Reward: {reward_status} | LickCount: {lick_count}{reward_note} | Elapsed: {elapsed_min}m{elapsed_sec:02d}s")

    return tone_type, reward_status, lick_count

def main():
    ser = open_serial(SERIAL_PORT, BAUD_RATE)

    threading.Thread(target=lick_listener, args=(ser,), daemon=True).start()

    experiment_start = time.time()
    reward_licks = []
    no_reward_licks = []
    reward_count = 0
    trial_num = 1

    with open(LOG_PATH, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Trial', 'ToneType', 'RewardGiven', 'Timestamp', 'Elapsed_ms', 'LickCount'])

        try:
            while True:
                elapsed_time = time.time() - experiment_start
                if elapsed_time > MAX_RUNTIME_MIN * 60:
                    print("[⏱️] Time limit reached.")
                    break
                if reward_count >= MAX_REWARD_COUNT:
                    print("[🎯] Max reward count reached.")
                    break

                print(f"\n--- Trial {trial_num} ---")
                send_trial(ser)

                try:
                    response = trial_result_queue.get(timeout=TRIAL_TIMEOUT)
                except queue.Empty:
                    response = "TIMEOUT,None,LickCount:0"

                elapsed_ms = int((time.time() - experiment_start) * 1000)
                tone_type, reward_status, lick_count = log_trial(writer, trial_num, response, elapsed_ms, reward_count + 1)

                if reward_status == "Reward":
                    reward_licks.append(lick_count)
                    reward_count += 1
                elif reward_status == "None":
                    no_reward_licks.append(lick_count)

                trial_num += 1
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n[!] Experiment manually interrupted.")

        def average(lst):
            return sum(lst) / len(lst) if lst else 0

        avg_reward = average(reward_licks)
        avg_noreward = average(no_reward_licks)
        ratio = avg_reward / avg_noreward if avg_noreward != 0 else float('inf')

        print("\n=== Lick Summary ===")
        print(f"Reward trials:    avg = {avg_reward:.2f} licks")
        print(f"No-reward trials: avg = {avg_noreward:.2f} licks")
        print(f"Reward/No-reward ratio: {ratio:.2f}")

        writer.writerow([])
        writer.writerow(['SUMMARY'])
        writer.writerow(['Reward Avg Lick', 'No-Reward Avg Lick', 'Reward/No-reward Ratio'])
        writer.writerow([f"{avg_reward:.2f}", f"{avg_noreward:.2f}", f"{ratio:.2f}"])

    ser.close()
    print(f"\n[✔] Experiment finished. Data saved to: {LOG_PATH}")

if __name__ == "__main__":
    main()
