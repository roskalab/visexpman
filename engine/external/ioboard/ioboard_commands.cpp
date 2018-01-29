#include "ioboard_commands.h"
#include "config.h"
#include "Arduino.h"
#include <string.h>

IOBoardCommands::IOBoardCommands(void)
{
  //initialize variables
  read_state=OFF;
  square_state=OFF;
  fm_state=OFF;
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
  //initialize timer1 for waveform generation
  DDRB|=1<<1;//pin 1 (pin 9 on arduino) enabled as outputs
  TCCR1A = _BV(COM2A0);//TODO: move it to a separate location
  TCCR1B = _BV(WGM12) | 3;
  OCR1A = 1300;
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
      square_state=ON;
      sq_half_period_ms = (unsigned long)(0.5*1e3/par[1]);
      if (sq_half_period_ms==0)
      {
        square_state=OFF;
      }
      sq_port=par[0];
      sq_port_state=OFF;
      last_state_change_ms=millis();
    }
    else if ((strcmp(command,"stop_square")==0)&&(nparams==1))
    {
      if (debug==1)
      {
        Serial.println("Stop square");
      }
      square_state=OFF;
      set_pin(sq_port, 0.0);
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
  time_ms = millis();
  square_wave_handler();  
  if (read_state==ON)
  {  
    read_pins(0);
  }
}

void IOBoardCommands::read_pins(unsigned char force)
{
  port=PIND&INPORT_MASK;
  if ((port!=port_last) || (force==1))
  {
    Serial.print(time_ms);
    Serial.print(" ms: ");
    Serial.println(port&INPORT_MASK,DEC);
    port_last=port;
  }
}
void IOBoardCommands::square_wave_handler(void)
{
  if (square_state==ON)
  {
    if (time_ms-last_state_change_ms>sq_half_period_ms)
    {
      
      last_state_change_ms=time_ms;
      if (sq_port_state==OFF)
      {
        sq_port_state=ON;
        set_pin(sq_port, 1.0);
      }
      else
      {
        sq_port_state=OFF;
        set_pin(sq_port, 0.0);
      }
    }
  }
  
}
