#include "ioboard_commands.h"
#include "config.h"
#include "Arduino.h"
#include <string.h>

IOBoardCommands::IOBoardCommands(void)
{
  //initialize variables
  read_state=OFF;
  waveform_state=OFF;
  port=0;
  port_last=0;
  phase_counter=0;
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
  DDRB|=1<<1;//pin 1 (pin 9 on arduino) enabled as output
  TCCR1A = _BV(COM2A0);
  TCCR1B = _BV(WGM12);
//  OCR1A = 1300;*/
  sei();
}

void IOBoardCommands::run(void)
{
  int res,i;
  res=parse();
  if (res==NO_ERROR)
  {
    //Command for identifying serial port device
    if ((strcmp(command,"ioboard")==0)&&(nparams==0))
    {
      Serial.println("ioboard");
    }

    else if ((strcmp(command,"set_pin")==0)&&(nparams==2))
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
    else if ((strcmp(command,"waveform")==0)&&(nparams==3))
    {
      if (debug==1)      
      {
        Serial.print(par[0]);
        Serial.println(" Hz signal on pin 9");
      }
      if (waveform_state==OFF)
      {         
        base_frequency=par[0];
        frequency_range=par[1];
        modulation_frequency=par[2];
        waveform_state=ON;
        if ((frequency_range==0.0) && (modulation_frequency==0.0))
        {
          tmp=CPU_FRQ/(64*2*base_frequency)-1;
          if ((tmp==0) || (tmp>65535) || base_frequency>5000.0)//Above 5 kHz frequency is not that accurate with this prescaler
          {
            waveform_state=OFF;
            Serial.print(tmp);
            Serial.println(" invalid frequency");
          }
          else
          {
            TCCR1B |= 3;//prescale 64
            waveform_frq_register=(uint16_t)(tmp);          
          }
        }
        else
        {
          TCCR1B|=1;//prescale 1
          waveform_frq_register=1000;
        }
        TIMSK1 |= 1<<1;//enable output compare channel A interrupt
      }
      else
      {
        if (debug==1)      
        {
          Serial.println("Waveform is running");
        }
        
      }
    }
    else if ((strcmp(command,"stop")==0)&&(nparams==0))
    {
      if (debug==1)
      {
        Serial.println("Stop waveform");
      }
      TCCR1B&=~7;
      TIMSK1 &= ~(1<<1);      
      waveform_state=OFF;
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
  if (read_state==ON)
  {
    read_pins(0);
  }
  phase_counter+=1;
  if (phase_counter%4==0)
  {
    if ((waveform_state==ON) && (frequency_range>0.0) && (modulation_frequency>0.0))
    {
//      set_pin(5.0,1.0);
      tmp_isr=0.5*frequency_range*sin(2*PI*modulation_frequency*phase_counter/TIMER_FRQ);
      tmp_isr+=base_frequency;
      tmp_isr=CPU_FRQ/(1*2*tmp_isr)-1;
      waveform_frq_register=(uint16_t)(tmp_isr);
  //    set_pin(5.0,0.0);    
    }
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
void IOBoardCommands::waveform_isr(void)
{
  OCR1A = waveform_frq_register;
}
