#include "hitmiss.h"
#include "config.h"

int lickValue = 0;
int tsample=10;
unsigned long timestamp,timestamp_us;
unsigned long rise_time,dt, last_run;
bool rise;
float voltage_threshold=0.25;
float voltage_threshold_adc=1024/5.0*voltage_threshold;
float max_width_us=100000*1e-6;
float min_width_us=10000*1e-6;

class LickProtocolRunner {
  public:
    LickProtocolRunner(void);
    void loop(void);
    HitMiss protocol;
};

LickProtocolRunner::LickProtocolRunner()
{
  protocol=HitMiss();
  pinMode(LICKDETECTEDPIN, OUTPUT);
  pinMode(REWARDPIN, OUTPUT);
  pinMode(LASERPIN, OUTPUT);
  digitalWrite(LASERPIN, LOW);
  digitalWrite(REWARDPIN, LOW);
  Serial.begin(115200);
}

void LickProtocolRunner::loop(void)
{
  char c[2];
  protocol.lick_detector.update();//detect lick events
  if (Serial.available()>0)
  {
    c[0]=Serial.read();
    c[1]=0;
    protocol.put(c);
    protocol.run();
  }
}


LickProtocolRunner lpr;

void setup() {
  // put your setup code here, to run once:
  lpr=LickProtocolRunner();
  
}

void loop() {  
  
  lpr.loop();
}
