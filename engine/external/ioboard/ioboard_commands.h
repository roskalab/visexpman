#include "comm.h"
#include "Arduino.h"

typedef enum state_t {
    ON,
    OFF
    } state_t;

class IOBoardCommands:public Comm {
    public:
        IOBoardCommands(void);
        void run(void);
        void isr(void);
        void waveform_isr(void);
        void elongate_isr(void);
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
        void set_pin(float pin,float value);
        void pulse(float pin,float duration);
        void waveform(float base_frequency, float frequency_range, float modulation_frequency);
        void start_read_pins(void);
        void stop_read_pins(void);
        void stop_waveform(void);
        void read_pins(unsigned char force);
};
