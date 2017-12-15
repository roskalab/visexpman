#define PERIOD  20//seconds
#define PULSE_DURATION  10//millseconds
#define RED_LED 12
#define BLUE_LED 13
#define OFFTIME PERIOD*1000-PULSE_DURATION

void setup() {
  pinMode(RED_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);

}

void loop() {
  digitalWrite(RED_LED, HIGH);
  delay(PULSE_DURATION);
  digitalWrite(RED_LED, LOW);
  delay(OFFTIME);
  digitalWrite(BLUE_LED, HIGH);
  delay(PULSE_DURATION);
  digitalWrite(BLUE_LED, LOW);
  delay(OFFTIME);
}
