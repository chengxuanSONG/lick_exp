import serial
import time
import csv
import threading
import queue
from datetime import datetime

# ==== CONFIG ====
SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
MAX_RUNTIME_MIN = 30
MAX_REWARD_COUNT = 300
TRIAL_TIMEOUT = 10.0

# ==== LOG FILES ====
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
TRIAL_LOG_PATH = f"data/trial_log_{timestamp_str}.csv"
LICK_LOG_PATH = f"data/lick_log_{timestamp_str}.csv"

# ==== GLOBAL STATE ====
trial_result_queue = queue.Queue()
lick_log = []
trial_active = False
lick_count_in_trial = 0
last_lick_time = 0
trial_num = 1
ttl_triggered = threading.Event()
lock = threading.Lock()

# ==== SERIAL ====
def open_serial(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=0.1)
        time.sleep(2)
        print(f"[✓] Serial connected on {port}")
        return ser
    except serial.SerialException as e:
        print(f"[✗] Serial error: {e}")
        exit(1)

def send_trial(ser):
    ser.write(b'1')

def send_reset(ser):
    ser.write(b'r')
    print("[↩] Sent reset signal to Arduino.")

# ==== LICK LISTENER ====
def lick_listener(ser):
    global trial_active, lick_count_in_trial, last_lick_time, trial_num
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
                        #print(f"[DEBUG] Received line: {repr(decoded)}") 
                        now = time.time()

                        if decoded.startswith("Lick"):
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            print(f"[👅]{decoded}")
                            lick_log.append([ts, decoded])
                            with lock:
                                if trial_active:
                                    lick_count_in_trial += 1

                        elif decoded.startswith("Tone"):
                            trial_result_queue.put(decoded)

                        elif decoded.startswith("TRIAL_START"):
                            with lock:
                                lick_count_in_trial = 0
                                trial_active = True
                            print(f"\n-- Trial {trial_num} --")

                        elif decoded.startswith("x✅"):
                            print(f"[🚀] TTL triggered by: {repr(decoded)}")
                            ttl_triggered.set()

                    buffer = lines[-1]
            time.sleep(0.001)
        except Exception as e:
            print(f"[⚠️] Listener error: {e}")

# ==== LOGGING ====
def log_trial(writer, trial_num, result_string, elapsed_ms, reward_count, lick_count):
    try:
        tone_type, reward_status, _ = result_string.split(",")
    except Exception as e:
        print(f"[!] Parse error: {e}")
        tone_type, reward_status = "Unknown", "None"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    writer.writerow([trial_num, tone_type, reward_status, timestamp, elapsed_ms, lick_count])

    elapsed_min = int(elapsed_ms // 60000)
    elapsed_sec = int((elapsed_ms % 60000) // 1000)
    reward_note = f" | Reward #{reward_count}" if reward_status == "Reward" else ""
    print(f"[✓] Trial {trial_num}: {tone_type} | Reward: {reward_status} | Licks: {lick_count}{reward_note} | Elapsed: {elapsed_min}m{elapsed_sec:02d}s")

    return tone_type, reward_status, lick_count

def save_lick_log():
    with open(LICK_LOG_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Event'])
        writer.writerows(lick_log)
    print(f"[💾] All licks saved to {LICK_LOG_PATH}")

# ==== MODE SELECTION ====
def choose_mode():
    while True:
        print("Select mode:")
        print("1 - recording (wait for TTL trigger)")
        print("2 - testing   (start immediately)")
        choice = input("Enter choice [1/2]: ").strip()
        if choice == '1':
            return "recording"
        elif choice == '2':
            return "testing"
        else:
            print("Invalid input. Please enter 1 or 2.\n")


# ==== MAIN ====
def main():
    global trial_active, lick_count_in_trial, trial_num

    mode = choose_mode()  # 🆕 select mode
    ser = open_serial(SERIAL_PORT, BAUD_RATE)
    threading.Thread(target=lick_listener, args=(ser,), daemon=True).start()

    if mode == "recording":
        print("[⌛] Waiting for TTL trigger...")
        try:
            while not ttl_triggered.wait(timeout=0.1):  #
                pass
        except KeyboardInterrupt:
            print("\n[🛑] Interrupted while waiting for TTL. Exiting.")
            send_reset(ser)
            ser.close()
            exit(0)
    
    else:
        print("[🧪] Testing mode: starting immediately.")
        ser.write(b't')  #
        time.sleep(0.5)

    experiment_start = time.time()
    reward_count = 0
    reward_licks = []
    no_reward_licks = []

    with open(TRIAL_LOG_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Trial', 'ToneType', 'RewardGiven', 'Timestamp', 'Elapsed_ms', 'LickCount'])

        try:
            while True:
                elapsed_time = time.time() - experiment_start
                if elapsed_time > MAX_RUNTIME_MIN * 60:
                    print("[⏱️] Max runtime reached.")
                    break
                if reward_count >= MAX_REWARD_COUNT:
                    print("[🎯] Max reward count reached.")
                    break

                send_trial(ser)

                try:
                    result = trial_result_queue.get(timeout=TRIAL_TIMEOUT)
                except queue.Empty:
                    result = "TIMEOUT,None,LickCount:0"

                with lock:
                    trial_active = False
                    this_trial_licks = lick_count_in_trial

                elapsed_ms = int((time.time() - experiment_start) * 1000)
                tone, reward, count = log_trial(writer, trial_num, result, elapsed_ms, reward_count + 1, this_trial_licks)

                if reward == "Reward":
                    reward_count += 1
                    reward_licks.append(this_trial_licks)
                else:
                    no_reward_licks.append(this_trial_licks)

                trial_num += 1
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n[🛑] Interrupted by user.")
        finally:
            send_reset(ser)

    # Summary
    def avg(x): return sum(x) / len(x) if x else 0
    print("\n=== Summary ===")
    print(f"Avg reward licks: {avg(reward_licks):.2f}")
    print(f"Avg no-reward licks: {avg(no_reward_licks):.2f}")
    print(f"Ratio: {avg(reward_licks) / avg(no_reward_licks) if no_reward_licks else float('inf'):.2f}")

    save_lick_log()
    ser.close()
    print(f"[✔] Trial data saved to {TRIAL_LOG_PATH}")

if __name__ == "__main__":
    main()
