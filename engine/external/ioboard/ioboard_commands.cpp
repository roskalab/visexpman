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
  debug=1;
  //initialize peripherals
  Serial.begin(115200);
  DDRD=OUTPORT_MASK;//port 2-4 input, port 5-7 output
  PORTD=0x0;
  //Initialize timer2 periodic interrupt
  TCCR2B = TIMER_PRESCALE;
  OCR2A = TIMER_COMPARE;
  TIMSK2 |= 1<<1;  
  //initialize timer2 for waveform generation
  TCCR1B=1<<3;
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
      if (debug==1)
      {
        Serial.print(par[0]);
        Serial.print(" pin set to ");
        Serial.println(par[1]);
      }
      set_pin(par[0], par[1]);
    }
    else if ((strcmp(command,"start_read_pins")==0)&&(nparams==0))
    {
      if (read_state==OFF)
      {
        if (debug==1)
        {
          Serial.println("Start reading pins");
        }
        read_state=ON;
      }
    }
    else if ((strcmp(command,"stop_read_pins")==0)&&(nparams==0))
    {
      if (debug==1)      
      {
        Serial.println("Stop reading pins");
      }
      read_state=OFF;
    }
    else if ((strcmp(command,"read_pins")==0)&&(nparams==0))
    {
      if (read_state==OFF)
      {
        read_pins(1);
      }
    }
    else if ((strcmp(command,"pulse")==0)&&(nparams==2))
    {
      if (debug==1)
      {
        Serial.print(par[1]);
        Serial.print(" ms pulse on pin ");
        Serial.println(par[0]);
      }
      pulse(par[0], par[1]);
    }
    else if ((strcmp(command,"square_wave")==0)&&(nparams==2))
    {
      if (debug==1)      
      {
        Serial.print(par[1]);
        Serial.print(" Hz square wave on pin ");
        Serial.println(par[0]);
      }
      waveform_state=SQUARE_WAVE;
      frequency=par[1];
      set_timer_channel(par[0]);
      TCCR1B|=4;
      
    }
    else if ((strcmp(command,"stop_waveform")==0)&&(nparams==1))
    {
      if (debug==1)
      {
        Serial.println("Stop wave");
      }
      waveform_state=DISABLED;
      stop_waveform(par[0]);       
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
void IOBoardCommands::set_pin(float pin,float value)
{
  uint8_t channel_bit;
  channel_bit=(uint8_t)(pin);
  if (pin<=7 && pin>=5)
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
    read_pins(0);
  }
}
void IOBoardCommands::read_pins(unsigned char force)
{
  time_ms = millis();
  port=PIND&INPORT_MASK;
  if ((port!=port_last) || (force==1))
  {
    Serial.print(time_ms);
    Serial.print(" ms: ");
    Serial.println(port&INPORT_MASK,DEC);
    port_last=port;
  }
}


void IOBoardCommands::set_timer_channel(float pin)
{
  static uint8_t reg;
 //Calculate compare register value from frequency (par[1]):
  if (waveform_state==SQUARE_WAVE)
  {
    reg =(unsigned char)(CPU_FRQ/(64*par[1])-1);
  }
  if (pin==5)//channel B
  {
    TIMSK1=1<<2;
    TCCR1A=1<<6;
    OCR2B=reg;
  }
  else if (pin==6)//channel A
  {
    TIMSK1=1<<1;
    TCCR1A=1<<4;
    OCR2A=reg;
  }
}

void IOBoardCommands::stop_waveform(float pin)
{
  if (pin==5)//channel B
  {
    TIMSK1&=~(1<<2);
    TCCR1A&=~(3<<6);
  }
  else if (pin==6)//channel A
  {
    TIMSK1&=~(1<<1);
    TCCR1A&=~(3<<4);
  }
}
