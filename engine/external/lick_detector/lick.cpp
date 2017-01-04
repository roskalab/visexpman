#include "config.h"
#include "Arduino.h"
#include "lick.h"

#define ENABLE_DEBUG_PULSES 0

LickDetector::LickDetector(void)
{
  duration_max_ms=(unsigned long)(LICK_DURATION_MAX*1e3);
  duration_min_ms=(unsigned long)(LICK_DURATION_MIN*1e3);
  voltage_threshold_adc=(int)ADCMAXCOUNT/ADCREF*LICK_THRESHOLD;
  last_run=micros();
  reset();
}

void LickDetector::reset(void)
{
  cli();
  rise=false;
  lick_counter=0;
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
  timestamp_us = millis();
  if ((timestamp_us-last_run>DETECTOR_RUN_PERIOD_MS)||1)
  { 
    last_run=timestamp_us;
    //Serial.println(duration_max_us);
    /*#if (ENABLE_DEBUG_PULSES)
      digitalWrite(LICKDETECTEDPIN, HIGH);
      delayMicroseconds(1000);
      digitalWrite(LICKDETECTEDPIN, LOW);
    #endif*/
    adc_val = analogRead(LICKPIN);
    if ((adc_val>voltage_threshold_adc)&&(!rise))
    {
      rise=true;
      rise_time=timestamp_us;
      #if (ENABLE_DEBUG_PULSES)
        digitalWrite(LICKDETECTEDPIN, HIGH);
        delayMicroseconds(200);
        digitalWrite(LICKDETECTEDPIN, LOW);
      #endif
    }
    else if ((adc_val<voltage_threshold_adc)&&rise)
    {      
      rise=false;
      dt=timestamp_us-rise_time;
      if ((dt>duration_min_ms) && (dt<duration_max_ms))
      {
        lick_counter++;
        last_lick_time=timestamp_us;
        digitalWrite(LICKDETECTEDPIN, HIGH);
        delayMicroseconds(400);
        digitalWrite(LICKDETECTEDPIN, LOW);
      }
    }
  }
}

