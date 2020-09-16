/*
This class implements the hit/miss protocol
*/
#include "comm.h"
#if (PLATFORM==ARDUINO)
  #include "lick.h"
  #include "dac.h"
#endif

typedef enum result_t {
    HIT = 0,
    MISS = 1
    } result_t;
    
typedef enum protocol_state_t 
    {
        IDLE,
        PRETRIAL, 
        LICKTRIAL,
        WAIT4RESPONSE, 
        WATERREWARD,
        ENDOFTRIAL,
    }  protocol_state_t ;

class HitMiss:public Comm {
    public:
        HitMiss(void);
        void run(void);
    #if (PLATFORM==ARDUINO)
        LickDetector lick_detector;
        Dac dac;
    #endif
    private:
    //Protocol parameters
        float laser_voltage;
        float laser_duration;
        float pre_trial_interval;
        float reponse_window_time;
        float water_dispense_delay;
        float water_dispense_time;
        float drink_time;
        float wait4lick;
    //Output
        float number_of_licks;
        result_t result;
    //Other
        protocol_state_t state;
        unsigned long t_wait_for_response;
        unsigned long now;
        unsigned long milliseconds(void);
        unsigned long water_dispense_delay_correction;
        void set_state(protocol_state_t state2set);
        void set_voltage(float voltage,int channel);
    
};
