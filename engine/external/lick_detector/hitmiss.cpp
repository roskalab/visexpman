#include "hitmiss.h"
#include "config.h"
#include <string.h>
#if (PLATFORM==PC)
  using namespace std;
  #include <iostream>
  #include <ctime>
#elif (PLATFORM==ARDUINO)
  #include "Arduino.h"
#endif


HitMiss::HitMiss(void)
{
    laser_voltage = 0;
    laser_duration = 0;
    pre_trial_interval = 0;
    reponse_window_time = 0;
    water_dispense_delay = 0;
    water_dispense_time = 0;
    drink_time = 0;
    state=IDLE;
    #if (PLATFORM==ARDUINO)
      lick_detector=LickDetector();
      dac=Dac();
    #endif
    
}

void HitMiss::run(void)
{
    int res,i;
    res=parse();
    if (res==NO_ERROR)
    {           
        if ((strcmp(command,"start_protocol")==0)&&(nparams==7)&& (state==IDLE))
        {
            laser_voltage = par[0];
            laser_duration = par[1];
            pre_trial_interval = par[2];
            reponse_window_time = par[3];
            water_dispense_delay = par[4];
            water_dispense_time = par[5];
            drink_time = par[6];
            set_state(PRETRIAL);
          #if (PLATFORM==ARDUINO)
            Serial.print("Protocol parameters: ");
            for(i=0;i<7;i++)
            {
              Serial.print(par[i]);
              Serial.print(",");
            }
            Serial.print("\r\n");
          #endif
        }
        else if ((strcmp(command,"reset_protocol")==0)&&(nparams==0))
        {            
            set_state(IDLE);
            Serial.println("Protocol state set to idle");
        }
        else if ((strcmp(command,"protocol_state")==0)&&(nparams==0))
        {            
            Serial.print("Protocol state: ");
            Serial.println(state);
        }
        else if ((strcmp(command,"ping")==0)&&(nparams==0))
        {          
          #if (PLATFORM==ARDUINO)
            debug_pulse();
            Serial.println("pong");
          #endif
        }
        else
        {
          #if (PLATFORM==ARDUINO)
            Serial.println("unknown command");
          #endif
        }
     
    }
    switch (state)
    {
        case PRETRIAL:
            #if (PLATFORM==PC)
                cout<<"Pretrial Wait "<<pre_trial_interval<<" s"<<endl;
            #elif (PLATFORM==ARDUINO)
                Serial.println("Pretrial wait");
                delay((int)(pre_trial_interval*1000));
                Serial.println("End of pretrial wait");
            #endif
            set_state(LICKTRIAL);
            break;
        case LICKTRIAL:
            #if (PLATFORM==PC)
                t_wait_for_response=milliseconds();
                cout<<"Lick trial, laser flash "<<laser_voltage<<"V duration "<<laser_duration<< "s " <<t_wait_for_response<<endl;
            #elif (PLATFORM==ARDUINO)
                Serial.println("Lick trial");
                //Reset lick counter
                lick_detector.reset();
                digitalWrite(LASERPIN, HIGH);
                dac.set(laser_voltage);
                delay((int)(laser_duration*1000));
                dac.set(0.0f);
                digitalWrite(LASERPIN, LOW);
                if (dac.check_output(0.0f))
                {
                  dac.set(0.0f);
                  Serial.println("Could not turn off laser, retrying");
                }
                t_wait_for_response=millis();
            #endif
            set_state(WAIT4RESPONSE);
            break;
        case WAIT4RESPONSE:
            #if (PLATFORM==PC)
                now=milliseconds();
                cout<<"Wait for lick event" <<endl;
                if (now%2000==0)
                {
                    cout<<"HIT"<<endl;
                    result=HIT;
                    set_state(WATERREWARD);
                    break;
                }
            #elif (PLATFORM==ARDUINO)
                now=millis();
                //Check if lick condition has happened
                if (lick_detector.get_lick_number()>0)
                {
                  Serial.println("Lick detected");
                  result=HIT;
                  set_state(WATERREWARD);
                  //Reward delay offset has to be modified if lick has happened during flash
                  cli();
                  if (t_wait_for_response>lick_detector.first_lick_time)
                  {
                    water_dispense_delay_correction=t_wait_for_response-lick_detector.first_lick_time;
                  }
                  else
                  {
                    water_dispense_delay_correction=0;
                  }
                  sei();
                  Serial.print("Water dispense delay correction [ms]: ");
                  Serial.println(water_dispense_delay_correction);
                }
            #endif
            //check timeout
            if ((now-t_wait_for_response)>(unsigned long)((reponse_window_time-laser_duration)*1000))
            {                
                set_state(ENDOFTRIAL);
                result=MISS;
             #if (PLATFORM==ARDUINO)
                Serial.println("Lick timeout");
             #endif
            }
            break;
        case WATERREWARD:
            #if (PLATFORM==PC)
                cout<<"Water reward delay "<<water_dispense_delay<<" s"<<endl;
                cout<<"Release water for "<<water_dispense_time<<" s"<<endl;
                cout<<"Drink time "<<drink_time<<" s"<<endl;
            #elif (PLATFORM==ARDUINO)
                delay((water_dispense_delay)*1000-water_dispense_delay_correction);
                digitalWrite(REWARDPIN, HIGH);
                delay((int)((water_dispense_time)*1000));
                digitalWrite(REWARDPIN, LOW);
                delay(drink_time*1000);
            #endif
            Serial.println("Water reward");
            set_state(ENDOFTRIAL);
            break;
        case ENDOFTRIAL:
            #if (PLATFORM==PC)
                cout<<"End of trial, result "<<result<<endl;
            #elif (PLATFORM==ARDUINO)
                Serial.println("End of trial");
                //todo: call send results(result, number_of_licks)
                //Perhaps it will be evaluated by host sw
            #endif
            dac.set(0.0f);//Make sure that laser is disabled
            set_state(IDLE);
            break;
        case IDLE:
        default:
        {}
    }
    
}

unsigned long HitMiss::milliseconds(void)
{
  #if (PLATFORM==PC)
      return (unsigned long)(time(0)*1000);
  #endif
}
void HitMiss::set_state(protocol_state_t state2set)
{
  debug_pulse();
  state=state2set;
}
