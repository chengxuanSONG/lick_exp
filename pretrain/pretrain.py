import serial
import time
import csv
import threading
from datetime import datetime

# === CONFIG ===
SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
CALM_DOWN_MS = 1500
MAX_RUNTIME_MIN = 30
MAX_PUMP_COUNT = 100
NO_LICK_TIMEOUT = 15  # seconds

# === Timestamp and file paths ===
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
LICK_PATH = f"lick_log_{timestamp_str}.csv"
PUMP_PATH = f"pump_log_{timestamp_str}.csv"

# === Serial setup ===
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
time.sleep(2)

# === Shared state
lick_log = []
pump_count = 0
start_time = time.time()
last_lick_time = 0
auto_pumped_this_trial = False
exit_flag = threading.Event()
lock = threading.Lock()

def send_pump():
    ser.write(b'P')

def wait_for_calm_down(trial, lick_writer):
    global last_lick_time
    print("[Calm Down] Waiting for 1.5s without licks...")
    last_lick = time.time() - start_time
    while True:
        line = ser.readline().decode().strip()
        now = time.time() - start_time
        if line == "LICK":
            print(f"[LICK] {now:.3f}")
            lick_writer.writerow([trial, f"{now:.3f}"])
            last_lick = now
            with lock:
                last_lick_time = now
        if now - last_lick >= CALM_DOWN_MS / 1000:
            print("[Calm Down Complete]")
            break

def auto_pump_monitor(pump_writer):
    global last_lick_time, pump_count, auto_pumped_this_trial
    while not exit_flag.is_set():
        time.sleep(0.5)
        now = time.time() - start_time
        with lock:
            since_last = now - last_lick_time
        if since_last >= NO_LICK_TIMEOUT:
            print(f"[AUTO] {NO_LICK_TIMEOUT}s no lick. Sending pump at {now:.3f}")
            pump_writer.writerow(["Auto",f"{now:.3f}", "AUTO"])  
            send_pump()
            wait_start = time.time()
            while time.time() - wait_start < 0.2:
                line = ser.readline().decode().strip()
                now = time.time() - start_time
                if line == "PUMP_DONE":
                    print(f"[AUTO] Got PUMP_DONE at {now:.3f}")
                    with lock:
                        last_lick_time = now
                        pump_count += 1
                        auto_pumped_this_trial = True
                    break
            else:
                with lock:
                    last_lick_time = time.time() - start_time


def main():
    global pump_count, last_lick_time, auto_pumped_this_trial

    trial = 0
    print("[System Ready] Waiting for licks...")

    with open(LICK_PATH, 'w', newline='') as lick_f, open(PUMP_PATH, 'w', newline='') as pump_f:
        lick_writer = csv.writer(lick_f)
        pump_writer = csv.writer(pump_f)
        lick_writer.writerow(['Trial', 'LickTime'])
        pump_writer.writerow(['Trial', 'PumpTime', 'Source'])

        last_lick_time = time.time() - start_time

        # Start auto pump background thread
        thread = threading.Thread(target=auto_pump_monitor, args=(pump_writer,), daemon=True)
        thread.start()

        while True:
            now = time.time() - start_time
            elapsed_min = now / 60
            if elapsed_min >= MAX_RUNTIME_MIN:
                print("[Max runtime reached. Exiting.]")
                break
            if pump_count >= MAX_PUMP_COUNT:
                print("[Max pump count reached. Exiting.]")
                break

            trial += 1
            print(f"\n--- Trial {trial} Start ---")

            # Check if auto pump happened
            with lock:
                skip_lick = auto_pumped_this_trial
                auto_pumped_this_trial = False

            if skip_lick:
                print("[AUTO] Skipping lick wait due to auto pump")
            else:
                # Wait for LICK
                while True:
                    line = ser.readline().decode().strip()
                    now = time.time() - start_time
                    if line == "LICK":
                        print(f"[LICK] {now:.3f}")
                        lick_writer.writerow([trial, f"{now:.3f}"])
                        with lock:
                            last_lick_time = now
                        send_pump()
                        break

                # Wait for PUMP_DONE
                while True:
                    line = ser.readline().decode().strip()
                    now = time.time() - start_time
                    if line == "PUMP_DONE":
                        print(f"[PUMP] {now:.3f}")
                        pump_writer.writerow([trial, f"{now:.3f}", "TRIAL"])
                        with lock:
                            pump_count += 1
                        break

            wait_for_calm_down(trial, lick_writer)
            lick_f.flush()
            pump_f.flush()

    exit_flag.set()
    print(f"\n[Finished] Trials: {trial} | Pumps: {pump_count}")
    print(f"LICK log: {LICK_PATH}")
    print(f"PUMP log: {PUMP_PATH}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit_flag.set()
        print("\n[Interrupted] Exiting gracefully.")
