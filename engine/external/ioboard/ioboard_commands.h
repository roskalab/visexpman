#include "comm.h"

typedef enum state_t {
    ON,
    OFF
    } state_t;

class IOBoardCommands:public Comm {
    public:
        IOBoardCommands(void);
        void run(void);
        void isr(void);
    private:
        state_t read_state;
        state_t fm_state;
        state_t square_state;
        unsigned long sq_half_period_ms;
        unsigned long last_state_change_ms;
        float sq_port;
        state_t sq_port_state;
        float fm_frequency;
        float frequency_range;
        float modulation_frequency;
        unsigned long time_ms;
        int port;
        int port_last;
        unsigned char debug;
        void set_pin(float pin,float value);
        void pulse(float pin,float duration);
        void square_wave(float pin, float frequency);
        void fm_waveform(float base_frequency, float frequency_range, float modulation_frequency);
        void start_read_pins(void);
        void stop_read_pins(void);
        void stop_square_waveform(void);
        void stop_fm(void);        
        void set_timer_channel(float pin);
        void read_pins(unsigned char force);
        void square_wave_handler(void);
};
