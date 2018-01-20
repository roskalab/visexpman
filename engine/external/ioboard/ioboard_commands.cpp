#include "ioboard_commands.h"
#include "config.h"
#include "Arduino.h"
#include <string.h>

IOBoardCommands::IOBoardCommands(void)
{
  //initialize variables
  read_state=OFF;
  waveform_state=DISABLED;
  port=0;
  port_last=0;
  //initialize peripherals
  Serial.begin(115200);
  DDRD=OUTPORT_MASK;//port 2-4 input, port 5-7 output
  PORTD=0x0;
  //Initialize timer2 periodic interrupt
  TCCR2B = TIMER_PRESCALE;
  OCR2A = TIMER_COMPARE;
  TIMSK2 |= 1<<1;  
  sei();
}

void IOBoardCommands::run(void)
{
  int res,i;
  res=parse();
  if (res==NO_ERROR)
  {
    if ((strcmp(command,"set_pin")==0)&&(nparams==2))
    {
      set_pin(par[0], par[1]);
      Serial.print(par[0]);
      Serial.print(" pin set to ");
      Serial.println(par[1]);
    }
    else if ((strcmp(command,"start_read_pins")==0)&&(nparams==0))
    {
      Serial.println("Start reading pins");
      isr();
      read_state=ON;
    }
    else if ((strcmp(command,"stop_read_pins")==0)&&(nparams==0))
    {
      Serial.println("Stop reading pins");
      read_state=OFF;
    }
    else if ((strcmp(command,"pulse")==0)&&(nparams==2))
    {
      pulse(par[0], par[1]);
      Serial.print(par[1]);
      Serial.print(" ms pulse on pin ");
      Serial.println(par[0]);
    }
    else if ((strcmp(command,"square_wave")==0)&&(nparams==1))
    {
      Serial.print(par[0]);
      Serial.println(" Hz square wave");
      waveform_state=SQUARE_WAVE;
      frequency=par[0];
    }
    else if ((strcmp(command,"stop_waveform")==0)&&(nparams==0))
    {
      Serial.println("Stop wave");
      waveform_state=DISABLED;
    }
    else
    {
      #if (PLATFORM==ARDUINO_UNO)
        Serial.print("unknown command: ");
        Serial.println(command);
      #endif
    }
  }
}
/*
PortD 5,6,7 pins ara valid outputs, these values are accepted as channel
*/
void IOBoardCommands::set_pin(float channel,float value)
{
  uint8_t channel_bit;
  channel_bit=(uint8_t)(channel);
  if (channel<=7 && channel>=5)
  {
    if (value==0.0)
    {
       PORTD&=~(1<<channel_bit);
    }
    else if (value==1.0)
    {
      PORTD|=(1<<channel_bit);
    }
    else
    {
      Serial.println("Invalid pin value");
    }
  }
}
void IOBoardCommands::pulse(float channel,float duration)
{
  set_pin(channel,1.0);
  delay((unsigned long)(duration));
  set_pin(channel,0.0);  
}
/*
Called by interrupt handler periodically. Handles reading data pins
*/
void IOBoardCommands::isr(void)
{
  if (read_state==ON)
  {  
    time_ms = millis();
    port=PIND&INPORT_MASK;
    if (port!=port_last)
    {
      Serial.print(time_ms);
      Serial.print(" ms: ");
      Serial.println(port&INPORT_MASK,HEX);
      port_last=port;
    }
  }
}
