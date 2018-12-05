#include "ioboard_commands.h"
#include "config.h"
#include "Arduino.h"
#include <EEPROM.h>
#include <string.h>

IOBoardCommands::IOBoardCommands(void)
{
  //initialize variables
  read_state=OFF;
  waveform_state=OFF;
  elongate_state=ON;
  elongate_output_pin=5.0;
  elongate_duration=5000.0;
  elongate_delay=0*7000.0;
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
  DDRB|=1<<1|1<<5;//pin 1 (pin 9 on arduino) enabled as output, pin 5 led
  TCCR1A = _BV(COM2A0);
  TCCR1B = _BV(WGM12);
//  OCR1A = 1300;*/

  EICRA|=3;//INT0/PIN2 rising edge
  EIMSK|=1;
#if ENABLE_STIMULUS_PHASE_LOCKING
  imaging_timestamp_index=0;
  stimulus_timestamp_index=0;
  phase_lock_state=NOT_RUNNING;
  imaging_pulse_counter=0;
  EICRA|=3<<2;//INT1/PIN2 rising edge
  EIMSK|=1<<1;  
#endif
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
    else if ((strcmp(command,"set_led")==0)&&(nparams==1))
    {
      if (debug==1)
      {
        Serial.print(" led set to ");
        Serial.println(par[0]);
      }
      if (par[0]>0)
      {
        PORTB|=1<<5;
      }
      else
      {
        PORTB&=~(1<<5);
      }
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
      stop_waveform();
    }
    else if ((strcmp(command,"reset")==0)&&(nparams==0))
    {
      if (debug==1)
      {
        Serial.println("Reset");
      }
      read_state=OFF;
      stop_waveform();
    }
    else if ((strcmp(command,"set_id")==0)&&(nparams==1))
    {
      if (debug==1)
      {
        Serial.print("Set Device ID to ");
        Serial.println(par[0]);        
      }
      EEPROM.write(ID_EEPROM_ADDRESS, (byte)(par[0]));
    }
    else if ((strcmp(command,"get_id")==0)&&(nparams==0))
    {
      if (debug==1)
      {
        Serial.print("Device ID ");
        Serial.println(EEPROM.read(ID_EEPROM_ADDRESS));
      }
    }
    else if ((strcmp(command,"elongate")==0)&&(nparams==4))//FOR SOME REASON THIS COMMAND DOES NOT WORK
    {
      if (par[0]==0.0)
      {
        elongate_state=OFF;
        EIMSK&=~1;
      }
      else
      {
        elongate_output_pin=par[1];
        elongate_duration=par[2];
        elongate_delay=par[3];
        if (elongate_delay<1e-3)
        {
          elongate_duration-=INT0_LATENCY_US;
        }
        else
        {
          elongate_delay-=INT0_LATENCY_US;
        }
        Serial.println(elongate_duration);
        if (elongate_duration<0)
        {//TODO: This check does not work!!!!!!
          Serial.println("Too short");
        }
        else
        {
          elongate_state=ON;
          EIMSK|=1;
          elongate_output_pin=par[2];
          elongate_duration=par[3]-INT0_LATENCY_US;
        }
      }
      if (debug==1)
      {
        Serial.print("Elongate: port: ");
        Serial.print(elongate_output_pin);
        Serial.print(" duration ");
        Serial.print(elongate_duration);
        Serial.print(" delay: ");
        Serial.print(elongate_delay);
        Serial.print(" state");
        Serial.println(elongate_state);
      }
    }
#if ENABLE_STIMULUS_PHASE_LOCKING
    else if ((strcmp(command,"measure_fps")==0)&&(nparams==0))
    {
        phase_lock_state=MEASURE_FPS;
        Serial.println("OK");      
    }
    else if ((strcmp(command,"stop_fpsmeas")==0)&&(nparams==0))
    {
        phase_lock_state=NOT_RUNNING;
        Serial.println("OK");      
    }
    else if ((strcmp(command,"read_fps")==0)&&(nparams==0))
    {
        phase_lock_state=NOT_RUNNING;
        Serial.println(imaging_frame_interval/(TIMING_BUFFER_SIZE-1));
    }    
#endif
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
void IOBoardCommands::stop_waveform(void)
{
  TCCR1B&=~7;
  TIMSK1 &= ~(1<<1);
  waveform_state=OFF;
}
void IOBoardCommands::int0_isr(void)
{
#if (!ENABLE_STIMULUS_PHASE_LOCKING)
    if (elongate_state==ON)
    {
      if (elongate_delay>0.0)
      {
          delayMicroseconds((unsigned long)(elongate_delay));
      }
      set_pin(elongate_output_pin,1.0);
      //Serial.print("I");
      delayMicroseconds((unsigned long)(elongate_duration));
      set_pin(elongate_output_pin,0.0);
    }
#else
    static int i;
    last_imaging_pulse_ts=micros();
    imaging_timestamps[imaging_timestamp_index]=last_imaging_pulse_ts;
    imaging_timestamp_index++;
    imaging_pulse_counter++;
    if (imaging_timestamp_index==TIMING_BUFFER_SIZE)
    {
      imaging_timestamp_index=0;
    }
    switch (phase_lock_state)
    {
      case MEASURE_FPS:
        if (imaging_pulse_counter>TIMING_BUFFER_SIZE)//buffer is not empty
        {
          imaging_frame_interval=0;
          for(i=0;i<TIMING_BUFFER_SIZE;i++)
          {
             if ((i==0) && (imaging_timestamps[i]>imaging_timestamps[TIMING_BUFFER_SIZE-1]))
             {
               imaging_frame_interval+=imaging_timestamps[i]-imaging_timestamps[TIMING_BUFFER_SIZE-1];
             }
             else if (imaging_timestamps[i]>imaging_timestamps[i-1])
             {
                imaging_frame_interval+=imaging_timestamps[i]-imaging_timestamps[i-1];
             }
          }
        }
        break;
    }
#endif
  
}
void IOBoardCommands::int1_isr(void)
{
#if ENABLE_STIMULUS_PHASE_LOCKING
    last_stimulus_pulse_ts=micros();
    stimulus_timestamps[stimulus_timestamp_index]=last_stimulus_pulse_ts;    
    stimulus_timestamp_index++;
    if (stimulus_timestamp_index==TIMING_BUFFER_SIZE)
    {
      stimulus_timestamp_index=0;
    }
    Serial.println(last_stimulus_pulse_ts);
#endif
  
}
