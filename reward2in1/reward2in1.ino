// === Hardware Pin Definitions ===
#define PUMP_ENABLE 11
#define PUMP_EN_R 7
#define AUDIO_PIN 6
#define LICK_PIN A1
#define TRIAL_ON 8
#define TTL_IN 2

// === Timing Parameters (ms)
#define PUMP_DURATION 150
#define TONE_DURATION 1000
#define POST_TONE_DELAY 1000
#define MAX_SAME_TONE 5
#define LICK_DEBOUNCE 0.025

// === Reward Probabilities (%)
#define REWARD_PROB_PCT     95   // Tone1_low: probability to deliver water
#define NONREWARD_PROB_PCT  20   // Tone2_high: probability to deliver water

// === Post-Trial Delay (ms) ===
#define POST_TRIAL_DELAY_MIN 5000  // min inter-trial for Random
#define POST_TRIAL_DELAY_MAX 8000  // max inter-trial for Random


// === TTL Pulse Durations (ms)
#define TTL_TONE1_DURATION 50
#define TTL_TONE2_DURATION 100

// === Tone Frequencies
const int TONE1_FREQ = 4000;
const int TONE2_FREQ = 9000;

// === Serial Bytes
const byte ARDUINO_RESET = 'r';
const byte ARDUINO_READY = 'x';

// === State Variables
bool started = false;
bool waiting_for_ttl = true;  // 🆕 required for Mode 1
int last_tone = -1;
int same_count = 0;
int lick_count_this_trial = 0;
bool last_lick_state = LOW;
unsigned long last_lick_time = 0;

void setup() {
  pinMode(PUMP_ENABLE, OUTPUT);
  pinMode(PUMP_EN_R, OUTPUT);
  pinMode(TRIAL_ON, OUTPUT);
  pinMode(AUDIO_PIN, OUTPUT);
  pinMode(LICK_PIN, INPUT);
  pinMode(TTL_IN, INPUT);

  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
  digitalWrite(TRIAL_ON, LOW);

  Serial.begin(115200);
  randomSeed(analogRead(A0));

  Serial.println("🔌 Arduino ready. Waiting for TTL...");
}

void loop() {
  check_lick();  // always run

  // TTL trigger detection (Mode 1)
  if (waiting_for_ttl && digitalRead(TTL_IN) == HIGH) {
    started = true;
    waiting_for_ttl = false;
    Serial.write(ARDUINO_READY);
    Serial.println("✅ TTL HIGH detected. Trials enabled.");
  }

  // Serial control
  if (Serial.available() > 0) {
    char incoming = Serial.read();
    if (incoming == '1' && started) {
      run_trial();
    } else if (incoming == 't') {
      started = true;
      waiting_for_ttl = false;
      Serial.println("🧪 Testing mode activated. Skipping TTL.");
    } else if (incoming == ARDUINO_RESET) {
      started = false;
      waiting_for_ttl = true;
      Serial.println("🔁 Reset received. Waiting for TTL again.");
    }

  }
}

void run_trial() {
  lick_count_this_trial = 0;

  int rand_choice = random(0, 2);
  if (rand_choice == last_tone) {
    same_count++;
    if (same_count >= MAX_SAME_TONE) {
      rand_choice = 1 - last_tone;
      same_count = 0;
    }
  } else {
    same_count = 1;
  }
  last_tone = rand_choice;

  digitalWrite(TRIAL_ON, HIGH);
  delay(rand_choice == 0 ? TTL_TONE1_DURATION : TTL_TONE2_DURATION);
  digitalWrite(TRIAL_ON, LOW);

  Serial.println("TRIAL_START");

  unsigned long tone_start = millis();
  tone(AUDIO_PIN, rand_choice == 0 ? TONE1_FREQ : TONE2_FREQ, TONE_DURATION);

  while (millis() - tone_start < TONE_DURATION + POST_TONE_DELAY) {
    check_lick();
  }
  noTone(AUDIO_PIN);

  if (rand_choice == 0) {
    // === Tone1_low: reward-eligible ===
    bool deliver = (random(100) < REWARD_PROB_PCT);  // 95% yes, 5% no
    if (deliver) {
      give_reward();
      Serial.print("Tone1_low,Reward,LickCount:");
    } else {
      delay(PUMP_DURATION);                          // fake wait for timing symmetry
      Serial.print("Tone1_low,None,LickCount:");
    }
  } else {
    // === Tone2_high: normally non-reward ===
    bool deliver = (random(100) < NONREWARD_PROB_PCT);  // 20% yes, 80% no
    if (deliver) {
      give_reward();
      Serial.print("Tone2_high,Reward,LickCount:");
    } else {
      delay(PUMP_DURATION);                            // fake wait to keep duration matched
      Serial.print("Tone2_high,None,LickCount:");
    }
  }
  Serial.println(lick_count_this_trial);

  unsigned long delay_start = millis();
  unsigned long delay_duration = random(POST_TRIAL_DELAY_MIN, POST_TRIAL_DELAY_MAX + 1);
  while (millis() - delay_start < delay_duration) {
    check_lick();
  }
}

void give_reward() {
  digitalWrite(PUMP_ENABLE, HIGH);
  digitalWrite(PUMP_EN_R, HIGH);
  delay(PUMP_DURATION);
  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
}

void check_lick() {
  bool current_state = digitalRead(LICK_PIN);
  unsigned long now = millis();

  if (current_state == HIGH && last_lick_state == LOW && (now - last_lick_time > LICK_DEBOUNCE)) {
    lick_count_this_trial++;
    Serial.print("Lick,");
    Serial.println(now);
    last_lick_time = now;
  }

  last_lick_state = current_state;
}
