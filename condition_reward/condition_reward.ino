// === Hardware Pin Definitions ===
#define PUMP_ENABLE 11
#define PUMP_EN_R 7
#define AUDIO_PIN 6
#define LICK_PIN A1
#define TRIAL_ON 8

// === Timing Parameters (ms) ===
#define PUMP_DURATION 100
#define TONE_DURATION 1000
#define POST_TONE_DELAY 1000
#define FIXED_POST_PUMP_DELAY 2000
#define LICK_DEBOUNCE 50

#define MAX_SAME_TONE 5

// === TTL Pulse Durations (ms)
#define TTL_TONE1_DURATION 50
#define TTL_TONE2_DURATION 100

// === Tone Frequencies ===
const int TONE1_FREQ = 4000;
const int TONE2_FREQ = 9000;

// === Serial Control Bytes ===
const byte ARDUINO_START = '1';

byte incoming = 0;
int last_tone = -1;
int same_count = 0;

unsigned long last_lick_time = 0;
volatile int lick_count_this_trial = 0;
bool count_licks = false;

// === Trial counter from Python ===
int trial_counter = 0;

void setup() {
  pinMode(PUMP_ENABLE, OUTPUT);
  pinMode(PUMP_EN_R, OUTPUT);
  pinMode(TRIAL_ON, OUTPUT);
  pinMode(AUDIO_PIN, OUTPUT);
  pinMode(LICK_PIN, INPUT);

  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
  digitalWrite(TRIAL_ON, LOW);

  Serial.begin(115200);
  randomSeed(analogRead(A0));
}

void loop() {
  check_lick();

  if (Serial.available() > 0) {
    incoming = Serial.read();
    if (incoming == ARDUINO_START) {
      trial_counter++;
      run_trial(trial_counter);
    }
  }
}

void run_trial(int trial_num) {
  lick_count_this_trial = 0;

  // === Tone choice logic ===
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

  // === TTL phase: no licking counted
  count_licks = false;
  digitalWrite(TRIAL_ON, HIGH);
  delayWithLickCheck(rand_choice == 0 ? TTL_TONE1_DURATION : TTL_TONE2_DURATION);
  digitalWrite(TRIAL_ON, LOW);

  // ✅ Print trial start marker
  Serial.print("-- Trial ");
  Serial.print(trial_num);
  Serial.println(" --");

  // === Start counting licking
  count_licks = true;

  // === Tone playback
  Serial.println("TRIAL_START"); 
  unsigned long tone_start = millis();
  tone(AUDIO_PIN, (rand_choice == 0 ? TONE1_FREQ : TONE2_FREQ), TONE_DURATION);

  while (millis() - tone_start < TONE_DURATION + POST_TONE_DELAY) {
    check_lick();
  }
  noTone(AUDIO_PIN);

  // === Reward if needed
  if (rand_choice == 0) {
    give_reward();
    delayWithLickCheck(FIXED_POST_PUMP_DELAY);  // 2s count-lick delay

    // ✅ Print summary marker
    Serial.print("[Summary] Trial ");
    Serial.print(trial_num);
    Serial.print(" | LickCount: ");
    Serial.println(lick_count_this_trial);

    Serial.print("Tone1_low,Reward,LickCount:");
  } else {
    Serial.print("Tone2_high,None,LickCount:");
  }

  Serial.println(lick_count_this_trial);

  // === Post-trial period (not counted)
  count_licks = false;
  delayWithLickCheck(random(2000, 4001));
}

void give_reward() {
  digitalWrite(PUMP_ENABLE, HIGH);
  digitalWrite(PUMP_EN_R, HIGH);
  delayWithLickCheck(PUMP_DURATION);
  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
}

void check_lick() {
  int reading = digitalRead(LICK_PIN);
  unsigned long now = millis();

  if (reading == HIGH && (now - last_lick_time > LICK_DEBOUNCE)) {
    Serial.print("Lick,");
    Serial.println(now);
    last_lick_time = now;

    if (count_licks) {
      lick_count_this_trial++;
    }
  }
}

void delayWithLickCheck(unsigned long duration) {
  unsigned long start = millis();
  while (millis() - start < duration) {
    check_lick();
    delay(1);
  }
}
