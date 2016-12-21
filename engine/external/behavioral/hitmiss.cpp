#include "hitmiss.h"
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
}

void HitMiss::run(void)
{
    int res;
    res=parse();
    if (res==NO_ERROR)
    {
        if ((strcmp(command,"start_protocol")==0)&&(nparams==7))
        {
            laser_voltage = par[0];
            laser_duration = par[1];
            pre_trial_interval = par[2];
            reponse_window_time = par[3];
            water_dispense_delay = par[4];
            water_dispense_time = par[5];
            drink_time = par[6];
            state=PRETRIAL;
        }
    }
    switch (state)
    {
        case PRETRIAL:
            #if (PLATFORM==PC)
                cout<<"Pretrial Wait "<<pre_trial_interval<<" s"<<endl;
            #elif (PLATFORM==ARDUINO)
                delay(pre_trial_interval*1000);
            #endif
            state=LICKTRIAL;
            break;
        case LICKTRIAL:
            #if (PLATFORM==PC)
                t_wait_for_response=milliseconds();
                cout<<"Lick trial, laser flash "<<laser_voltage<<"V duration "<<laser_duration<< "s " <<t_wait_for_response<<endl;
            #elif (PLATFORM==ARDUINO)
                //todo: hardware call
                t_wait_for_response=millis();
            #endif
            state=WAIT4RESPONSE;
            break;
        case WAIT4RESPONSE:
            #if (PLATFORM==PC)
                now=milliseconds();
                cout<<"Wait for lick event" <<endl;
            #elif (PLATFORM==ARDUINO)
                now=millis();
                //todo: hardware call, check if lick condition has happened
                result=MISS;
                state=WATERREWARD;
            #endif
            //check timeout
            if ((now-t_wait_for_response)>(unsigned long)(reponse_window_time*1000))
            {
                state=ENDOFTRIAL;
                result=MISS;
            }
            break;
        case WATERREWARD:
            #if (PLATFORM==PC)
                cout<<"Water reward delay "<<water_dispense_delay<<" s"<<endl;
                cout<<"Release water for "<<water_dispense_time<<" s"<<endl;
                cout<<"Drink time "<<drink_time<<" s"<<endl;
            #elif (PLATFORM==ARDUINO)
                delay(water_dispense_delay*1000);
                //todo: call to release water
                delay(drink_time*1000);
            #endif
            state=ENDOFTRIAL;
            break;
        case ENDOFTRIAL:
            #if (PLATFORM==PC)
                cout<<"End of trial, result "<<result<<endl;
            #elif (PLATFORM==ARDUINO)
                //todo: call send results(result, number_of_licks)
            #endif
            state=IDLE;
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
