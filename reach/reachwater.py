import serial
import time
import random
import csv
from datetime import datetime

# === CONFIGURATION ===
SERIAL_PORT = 'COM5'
BAUD_RATE = 115200
PRE_TONE_SILENCE = 1
TONE_DURATION = 0.2
RESPONSE_WINDOW = 7.0
FLEX_POST_LICK = 1
TRIAL_INTERVAL_RANGE = (1.0, 3.0)

# === LOG FILE SETUP ===
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = f"Data/m10/lick_log_{timestamp_str}.csv"

def wait_for_silence(ser, duration):
    #print(f"[FLEX] Waiting for {duration}s silence...")
    silent_start = time.time()
    while True:
        if ser.in_waiting:
            line = ser.readline().decode().strip()
            if "Lick" in line:
                
                silent_start = time.time()
        if time.time() - silent_start > duration:
            #print("[FLEX] Silence complete")
            return

def listen_for_lick(ser, timeout, t_start, all_lick_log, trial_lick_log):
    #print(f"[RESPOND] Listening for lick ({timeout}s)...")
    lick_count = 0
    start = time.time()
    while time.time() - start < timeout:
        if ser.in_waiting:
            line = ser.readline().decode().strip()
            if "Lick" in line:
                timestamp = time.time() - t_start
                all_lick_log.append(timestamp)
                trial_lick_log.append(timestamp)
                print(f"[RESPOND] Lick,{timestamp:.3f}")
                lick_count += 1
    return lick_count

def main():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print("[✓] Connected to Arduino")

    all_lick_timestamps = []
    trial_records = []
    reach_count = 0
    trial = 0
    t_start = time.time()

    try:
        while True:
            trial += 1
            #print(f"\n=== Trial {trial} Start ===")

            # 1. TTL
            ser.write(b's')

            # 2. Pre-tone flex silence
            wait_for_silence(ser, PRE_TONE_SILENCE)

            # 3. Tone
            ser.write(b't')
            time.sleep(TONE_DURATION + 0.1)

            # 4. Pump
            ser.write(b'p')
            time.sleep(0.1)

            # 5. Response
            trial_licks = []
            lick_count = listen_for_lick(ser, RESPONSE_WINDOW, t_start, all_lick_timestamps, trial_licks)

            if lick_count > 0:
                reach_count += 1
                wait_for_silence(ser, FLEX_POST_LICK)

            elapsed = time.time() - t_start
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)

            print(f"Trial {trial} | Lick Count = {lick_count} | Reach Number = {reach_count} | Elapsed: {elapsed_min}m{elapsed_sec}s")

            trial_records.append({
                "trial": trial,
                "lick_count": lick_count,
                "reach_number": reach_count,
                "elapsed_sec": round(elapsed, 2),
                "lick_timestamps": ";".join(f"{t:.3f}" for t in trial_licks)
            })

            # 6. Inter-trial interval
            interval = random.uniform(*TRIAL_INTERVAL_RANGE)
            #print(f"[INTER-TRIAL] Waiting {interval:.2f}s before next trial...")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[EXIT] Ctrl+C pressed. Saving log...")

    finally:
        ser.close()

        # Save CSV
        with open(LOG_PATH, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["trial", "lick_count", "reach_number", "elapsed_sec", "lick_timestamps"])
            writer.writeheader()
            writer.writerows(trial_records)

        print(f"[✓] Log saved to {LOG_PATH}")

if __name__ == "__main__":
    main()
