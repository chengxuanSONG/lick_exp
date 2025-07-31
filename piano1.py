import serial
import time
import csv
from datetime import datetime

# ========== CONFIG ==========
SERIAL_PORT = 'COM5'
BAUD_RATE = 115200
MAX_RUNTIME_MIN = 30            # Max runtime in minutes
MAX_REWARD_COUNT = 300          # Max number of rewards to give
TRIAL_TIMEOUT = 10.0            # Max time to wait for Arduino response

# Log file with timestamp
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = f"Data/m71/tone_trial_log_{timestamp_str}.csv"
# ============================

def open_serial(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)
        print(f"[✓] Serial connected on {port}")
        return ser
    except serial.SerialException as e:
        print(f"[✗] Failed to open serial port: {e}")
        exit(1)

def send_trial(ser):
    ser.write(b'1')  # Send start trial command

def wait_for_arduino_response(ser, timeout_sec=TRIAL_TIMEOUT):
    ser.flushInput()
    t_start = time.time()
    lick_events = []
    result_line = None

    while True:
        if ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()

            # Record up to 2 lick events
            if line.startswith("Lick"):
                lick_events.append(line)
                print(f"[👅] {line}")

            # Final result of trial
            if line.startswith("Tone"):
                result_line = line
                break

        if time.time() - t_start > timeout_sec:
            result_line = "TIMEOUT,None,LickCount:0"
            break

    return result_line


def log_trial(csv_writer, trial_num, result_string, elapsed_ms, reward_count):
    try:
        tone_type, reward_status, lick_info = result_string.split(",")
        lick_count = int(lick_info.split(":")[1])
    except Exception as e:
        print(f"[!] Parse error: {e}")
        tone_type, reward_status, lick_count = "Unknown", "None", 0

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    csv_writer.writerow([trial_num, tone_type, reward_status, timestamp, elapsed_ms, lick_count])

    # Show formatted trial output
    elapsed_min = int(elapsed_ms // 60000)
    elapsed_sec = int((elapsed_ms % 60000) // 1000)
    reward_note = f" | Reward #{reward_count}" if reward_status == "Reward" else ""
    print(f"[✓] Trial {trial_num}: {tone_type} | Reward: {reward_status} | LickCount: {lick_count}{reward_note} | Elapsed: {elapsed_min}m{elapsed_sec:02d}s")

    return tone_type, reward_status, lick_count

def main():
    ser = open_serial(SERIAL_PORT, BAUD_RATE)
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
                response = wait_for_arduino_response(ser)
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

        # === Summary Statistics ===
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
