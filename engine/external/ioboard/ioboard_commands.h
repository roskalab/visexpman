#include "comm.h"
#include "config.h"
#include "Arduino.h"

typedef enum state_t {
    ON,
    OFF
    } state_t;
    
#if ENABLE_STIMULUS_PHASE_LOCKING
typedef enum phase_lock_state_t {
   NOT_RUNNING,
   MEASURE_FPS,
   MEASURE_PHASE_ONLY,
   MEASURE_PHASE_ENABLE_LED   
} phase_lock_state_t;

#endif

class IOBoardCommands:public Comm {
    public:
        IOBoardCommands(void);
        void run(void);
        void isr(void);
        void waveform_isr(void);
        void int0_isr(void);
        void int1_isr(void);
    private:
        state_t read_state;
        state_t waveform_state;
        state_t elongate_state;
        float base_frequency;
        float frequency_range;
        float modulation_frequency;
        uint16_t waveform_frq_register;
        unsigned long time_ms;
        unsigned long phase_counter;
        int port;
        int port_last;
        float tmp;
        float tmp_isr;
        unsigned char debug;
        float elongate_output_pin;
        float elongate_duration;
        float elongate_delay;
#if ENABLE_STIMULUS_PHASE_LOCKING
        //Variables for phase locking stimulus
        unsigned long last_imaging_pulse_ts;
        unsigned long last_stimulus_pulse_ts;        
        unsigned long imaging_timestamps[TIMING_BUFFER_SIZE];
        unsigned long stimulus_timestamps[TIMING_BUFFER_SIZE];
        unsigned char imaging_timestamp_index;
        unsigned char stimulus_timestamp_index;
        unsigned long imaging_frame_interval;
        phase_lock_state_t phase_lock_state;
        unsigned long imaging_pulse_counter;
#endif
        void set_pin(float pin,float value);
        void pulse(float pin,float duration);
        void waveform(float base_frequency, float frequency_range, float modulation_frequency);
        void start_read_pins(void);
        void stop_read_pins(void);
        void stop_waveform(void);
        void read_pins(unsigned char force);
};
