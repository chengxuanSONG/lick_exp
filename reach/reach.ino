#define PUMP_ENABLE 11
#define PUMP_EN_R 7
#define AUDIO_PIN 6
#define LICK_PIN A1
#define TRIAL_ON 8

#define TONE_FREQ 6000
#define TONE_DURATION 500
#define PUMP_DURATION 50
#define LICK_DEBOUNCE 100

void setup() {
  pinMode(PUMP_ENABLE, OUTPUT);
  pinMode(PUMP_EN_R, OUTPUT);
  pinMode(AUDIO_PIN, OUTPUT);
  pinMode(LICK_PIN, INPUT);
  pinMode(TRIAL_ON, OUTPUT);

  digitalWrite(PUMP_ENABLE, LOW);
  digitalWrite(PUMP_EN_R, LOW);
  digitalWrite(TRIAL_ON, LOW);

  Serial.begin(115200);
  Serial.println("🟢 Arduino ready.");
}

void loop() {
  check_lick();

  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 's') {
      digitalWrite(TRIAL_ON, HIGH);
      delay(50);
      digitalWrite(TRIAL_ON, LOW);
    } else if (cmd == 't') {
      tone(AUDIO_PIN, TONE_FREQ, TONE_DURATION);
      delay(TONE_DURATION);
    } else if (cmd == 'p') {
      digitalWrite(PUMP_ENABLE, HIGH);
      digitalWrite(PUMP_EN_R, HIGH);
      delay(PUMP_DURATION);
      digitalWrite(PUMP_ENABLE, LOW);
      digitalWrite(PUMP_EN_R, LOW);
    }
  }
}

void check_lick() {
  static bool last_state = LOW;
  static unsigned long last_lick_time = 0;
  bool curr = digitalRead(LICK_PIN);
  unsigned long now = millis();
  if (curr == HIGH && last_state == LOW && (now - last_lick_time > LICK_DEBOUNCE)) {
    Serial.print("Lick,");
    Serial.println(now);
    last_lick_time = now;
  }
  last_state = curr;
}
