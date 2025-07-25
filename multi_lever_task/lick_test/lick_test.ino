// === Pin Definitions ===
const int LICK_PIN = 2;  // Connect your LICK sensor output to digital pin 2

// === Debounce Settings ===
const unsigned long DEBOUNCE_MS = 100;  // Minimum time between licks (in ms)

// === State Tracking ===
bool last_state = LOW;
unsigned long last_lick_time = 0;

void setup() {
  pinMode(LICK_PIN, INPUT);   // Use INPUT or INPUT_PULLUP depending on your hardware
  Serial.begin(115200);
  Serial.println("🍭 Lick Detection Ready.");
}

void loop() {
  bool current_state = digitalRead(LICK_PIN);
  unsigned long now = millis();

  // Detect rising edge: LOW → HIGH, and debounce
  if (current_state == HIGH && last_state == LOW && (now - last_lick_time > DEBOUNCE_MS)) {
    Serial.print("LICK detected at ");
    Serial.print(now);
    Serial.println(" ms");
    last_lick_time = now;
  }

  last_state = current_state;  // Update for next loop
}
