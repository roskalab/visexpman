#include "config.h"
#include "Arduino.h"
#include "lick.h"

#define ENABLE_DEBUG_PULSES 0

LickDetector::LickDetector(void)
{
  duration_max_ms=(unsigned long)(LICK_DURATION_MAX*1e3);
  duration_min_ms=(unsigned long)(LICK_DURATION_MIN*1e3);
  voltage_threshold_adc=(int)(LICK_THRESHOLD/ADC_SCALE);
  analogReference(INTERNAL);//1.1V internal reference selected
  last_run=micros();
  reset();
}

void LickDetector::reset(void)
{
  cli();
  rise=false;
  lick_counter=0;
  first_lick_time=0;
  sei();
}

int LickDetector::get_lick_number(void)
{
  return lick_counter;
}

float LickDetector::get_last_lick_time(void)
{
  if (lick_counter==0)
  {
    return -1;
  }
  else
  {
    return (float)last_lick_time;
  }
}
void LickDetector::update(void)
{
  timestamp = millis();
  if (1)//((timestamp_us-last_run>DETECTOR_RUN_PERIOD_MS)||1)
  { 
    //last_run=timestamp;
    //Serial.println(duration_max_us);
    #if (ENABLE_DEBUG_PULSES)
      digitalWrite(LICKDETECTEDPIN, HIGH);
      delayMicroseconds(1000);
      digitalWrite(LICKDETECTEDPIN, LOW);
    #endif
    adc_val = analogRead(LICKPIN);
    if ((adc_val>voltage_threshold_adc)&&(!rise))
    {
      rise=true;
      //digitalWrite(LICKDETECTEDPIN, HIGH);//DEBUG
      rise_time=timestamp;
      #if (ENABLE_DEBUG_PULSES)
        digitalWrite(LICKDETECTEDPIN, HIGH);
        delayMicroseconds(200);
        digitalWrite(LICKDETECTEDPIN, LOW);
      #endif
    }
    else if ((adc_val<voltage_threshold_adc)&&rise)
    {      
      rise=false;
      //digitalWrite(LICKDETECTEDPIN, LOW);//DEBUG
      dt=timestamp-rise_time;
      if ((dt>duration_min_ms) && (dt<duration_max_ms))
      {
        lick_counter++;
        last_lick_time=timestamp;
        if (lick_counter==1)
        {
          first_lick_time=timestamp;
        }
        digitalWrite(LICKDETECTEDPIN, HIGH);
        delayMicroseconds(500);
        digitalWrite(LICKDETECTEDPIN, LOW);
      }
    }
  }
}

