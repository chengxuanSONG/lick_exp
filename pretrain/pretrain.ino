// === Hardware Pin Definitions ===
#define PUMP_ENABLE 11
#define PUMP_EN_R 7
#define AUDIO_PIN 6
#define LICK_PIN A1
#define TRIAL_ON 8
#define TTL_IN 2  // not used here

// === Timing Parameters (ms) ===
#define PUMP_DURATION 100
#define LICK_DEBOUNCE 10

// === State Variables ===
bool last_lick_state = LOW;
unsigned long last_lick_time = 0;

void setup() {
  pinMode(PUMP_ENABLE, OUTPUT);
  pinMode(PUMP_EN_R, OUTPUT);
  pinMode(AUDIO_PIN, OUTPUT);
  pinMode(TRIAL_ON, OUTPUT);
  pinMode(LICK_PIN, INPUT);
  pinMode(TTL_IN, INPUT);

  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
  digitalWrite(TRIAL_ON, LOW);

  Serial.begin(115200);
  Serial.println("🔌 Arduino ready.");
}

void loop() {
  check_lick();

  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'P') {
      give_reward();
      Serial.println("PUMP_DONE");
    }
  }
}

void check_lick() {
  bool current_state = digitalRead(LICK_PIN);
  unsigned long now = millis();

  // Detect rising edge with debounce
  if (current_state == HIGH && last_lick_state == LOW && (now - last_lick_time > LICK_DEBOUNCE)) {
    Serial.println("LICK");
    last_lick_time = now;
  }

  last_lick_state = current_state;
}

void give_reward() {
  digitalWrite(PUMP_ENABLE, HIGH);
  digitalWrite(PUMP_EN_R, HIGH);
  delay(PUMP_DURATION);
  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
}
