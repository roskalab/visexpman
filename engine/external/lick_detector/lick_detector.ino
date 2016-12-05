int sensorPin = A0;
int outPin = 13;
int lickValue = 0;
int tsample=10;
unsigned long timestamp,timestamp_us;
unsigned long rise_time,dt, last_run;
bool rise;
float voltage_threshold=0.25;
float voltage_threshold_adc=1024/5.0*voltage_threshold;
float max_width_us=100000;
float min_width_us=10000;

void setup() {
  // put your setup code here, to run once:
  pinMode(outPin, OUTPUT);
  Serial.begin(115200);
  rise=false;
  last_run=micros();
}

void loop() {  
  timestamp_us = micros();
  if (timestamp_us-last_run>tsample*1000)
  { 
    last_run=timestamp_us;
    /*digitalWrite(outPin, HIGH);
    delayMicroseconds(1000);
    digitalWrite(outPin, LOW);*/
    lickValue = analogRead(sensorPin);
    if ((lickValue>voltage_threshold_adc)&&(!rise))
    {
      rise=true;
      rise_time=timestamp_us;
    /*  digitalWrite(outPin, HIGH);
      delayMicroseconds(200);
      digitalWrite(outPin, LOW);*/
    }
    else if ((lickValue<voltage_threshold_adc)&&rise)
    {
      rise=false;
      dt=timestamp_us-rise_time;
      if ((dt>min_width_us) && (dt<max_width_us))
      {
        digitalWrite(outPin, HIGH);
        delayMicroseconds(400);
        digitalWrite(outPin, LOW);
      }
    }
    
  }
  
}
