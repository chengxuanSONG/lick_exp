#define PUMP_ENABLE 11       // Pump control pin 
#define PUMP_EN_R 7          // Secondary enable pin
#define PUMP_DURATION 300    // Pump on time in ms
#define AUDIO_PIN 6          // Speaker pin (must be digital output capable)

const int TONE1_FREQ = 4000;          // Hz
const int TONE2_FREQ = 9000;         // Hz
const int TONE_DURATION = 1000;       // in ms
const int POST_TONE_DELAY = 500;      // in ms
const int POST_TRIAL_DELAY = 3000;    // in ms

const byte ARDUINO_START = '1';
const byte ARDUINO_OFF = '0';

byte incoming = 0;

void setup() {
  pinMode(PUMP_ENABLE, OUTPUT);
  pinMode(PUMP_EN_R, OUTPUT);
  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
  pinMode(AUDIO_PIN, OUTPUT);
  Serial.begin(115200);
  randomSeed(analogRead(A0));  // for trial randomization
}

void loop() {
  if (Serial.available() > 0) {
    incoming = Serial.read();
    if (incoming == ARDUINO_START) {
      run_trial();
    }
  }
}

void run_trial() {
  int rand_choice = random(0, 2); // 0 or 1

  if (rand_choice == 0) {
    // Tone1 (4kHz) and reward
    play_manual_tone(AUDIO_PIN, TONE1_FREQ, TONE_DURATION);
    delay(POST_TONE_DELAY);
    give_reward();
    Serial.println("Tone1,Reward");
  } else {
    // Tone2 (10kHz), no reward
    play_manual_tone(AUDIO_PIN, TONE2_FREQ, TONE_DURATION);
    delay(POST_TONE_DELAY);
    Serial.println("Tone2,None");
  }

  delay(POST_TRIAL_DELAY);
}

void play_manual_tone(int pin, int freq, int duration_ms) {
  int half_period_us = 1000000 / (2 * freq);  // microseconds for half cycle
  long num_cycles = (long)duration_ms * 1000L / (2 * half_period_us);  // total toggles

  for (long i = 0; i < num_cycles; i++) {
    digitalWrite(pin, HIGH);
    delayMicroseconds(half_period_us);
    digitalWrite(pin, LOW);
    delayMicroseconds(half_period_us);
  }
}

void give_reward() {
  digitalWrite(PUMP_ENABLE, HIGH);
  digitalWrite(PUMP_EN_R, HIGH);
  delay(PUMP_DURATION);
  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
}
