
// === Hardware Pin Definitions ===
#define PUMP_ENABLE 11         // Water pump control
#define PUMP_EN_R 7            // Pump relay control
#define AUDIO_PIN 6            // Speaker output
#define LICK_PIN A1            // Lick sensor input
#define TRIAL_ON 8             // TTL output for trial start

// === Timing Parameters (ms) ===
#define PUMP_DURATION 300      // Reward pump duration
#define TONE_DURATION 1500     // Tone playback duration
#define POST_TONE_DELAY 1000   // Delay after tone ends
#define MAX_SAME_TONE 5        // Max consecutive same-tone trials
#define LICK_DEBOUNCE 10       // Lick debounce time


// === TTL Pulse Durations (ms)
#define TTL_TONE1_DURATION 50  // TTL pulse for Tone1 (short)
#define TTL_TONE2_DURATION 100  // TTL pulse for Tone2 (long)

// === Tone Frequencies ===
const int TONE1_FREQ = 4000;   // Low tone (rewarded)
const int TONE2_FREQ = 9000;   // High tone (unrewarded)

// === Serial Control Bytes ===
const byte ARDUINO_START = '1';  // Start trial
const byte ARDUINO_OFF = '0';    // (Unused in this code)

byte incoming = 0;

// === Trial State Variables ===
int last_tone = -1;
int same_count = 0;

// === Lick Detection State ===
int last_lick_state = 0;
unsigned long last_lick_time = 0;
volatile int lick_count_this_trial = 0;

void setup() {
  // Initialize output pins
  pinMode(PUMP_ENABLE, OUTPUT);
  pinMode(PUMP_EN_R, OUTPUT);
  pinMode(TRIAL_ON, OUTPUT);
  pinMode(AUDIO_PIN, OUTPUT);

  // Initialize input pin
  pinMode(LICK_PIN, INPUT);

  // Ensure all outputs start LOW
  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
  digitalWrite(TRIAL_ON, LOW);

  // Start serial communication
  Serial.begin(115200);

  // Random seed for tone choice
  randomSeed(analogRead(A0));
}

void loop() {
  check_lick();  // Continuously monitor lick sensor

  if (Serial.available() > 0) {
    incoming = Serial.read();
    if (incoming == ARDUINO_START) {
      run_trial();  // Trigger trial if '1' received from serial
    }
  }
}

void run_trial() {
  // Reset lick counter for this trial
  lick_count_this_trial = 0;

  // Randomly choose tone (0 = TONE1, 1 = TONE2)
  int rand_choice = random(0, 2);
  if (rand_choice == last_tone) {
    same_count++;
    if (same_count >= MAX_SAME_TONE) {
      rand_choice = 1 - last_tone;  // Force switch
      same_count = 0;
    }
  } else {
    same_count = 1;
  }
  last_tone = rand_choice;

  // === Send TTL pulse to mark trial start ===
  digitalWrite(TRIAL_ON, HIGH);
  if (rand_choice == 0) {
    delay(TTL_TONE1_DURATION);  // Short TTL for Tone1
  } else {
    delay(TTL_TONE2_DURATION);  // Long TTL for Tone2
  }
  digitalWrite(TRIAL_ON, LOW);

  // === Play tone and monitor licking ===
  unsigned long tone_start = millis();
  tone(AUDIO_PIN, (rand_choice == 0 ? TONE1_FREQ : TONE2_FREQ), TONE_DURATION);

  // Wait while tone plays and post-tone delay elapses
  while (millis() - tone_start < TONE_DURATION + POST_TONE_DELAY) {
    check_lick();
  }

  noTone(AUDIO_PIN);  // Stop tone

  // === Report result via serial ===
  if (rand_choice == 0) {
    give_reward();
    Serial.print("Tone1_low,Reward,LickCount:");
  } else {
    Serial.print("Tone2_high,None,LickCount:");
  }
  Serial.println(lick_count_this_trial);
  int POST_TRIAL_DELAY = random(1000, 4001);  // Random between 1000–4000 ms
  delay(POST_TRIAL_DELAY);  // Wait before next trial
}

void give_reward() {
  // Activate water pump for fixed duration
  digitalWrite(PUMP_ENABLE, HIGH);
  digitalWrite(PUMP_EN_R, HIGH);
  delay(PUMP_DURATION);
  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
}
void check_lick() {
  static int last_state = LOW;
  static unsigned long change_time_ms = 0;
  static unsigned long last_lick_time_ms = 0;
  const unsigned int LICK_DEBOUNCE_MS = 10;

  int reading = digitalRead(LICK_PIN);
  unsigned long now_ms = millis();

  if (reading != last_state) {
    // Detected a change in signal
    if (change_time_ms == 0) {
      change_time_ms = now_ms;
    }
    else if (now_ms - change_time_ms > LICK_DEBOUNCE_MS) {
      // Signal remained stable for debounce period
      last_state = reading;
      if (reading == HIGH) {
        // Confirmed a real lick
        lick_count_this_trial++;
        Serial.print("Lick,");
        Serial.println(now_ms);
        last_lick_time_ms = now_ms;
      }
      change_time_ms = 0;
    }
  } else {
    change_time_ms = 0;
  }
}
