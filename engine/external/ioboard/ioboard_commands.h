#include "comm.h"

typedef enum waveform_t {
    DISABLED,
    FREQUENCY_MODULATION,
    SQUARE_WAVE
    } waveform_t;

typedef enum read_state_t {
    ON,
    OFF
    } read_state_t;

class IOBoardCommands:public Comm {
    public:
        IOBoardCommands(void);
        void run(void);
        void isr(void);
    private:
        read_state_t read_state;
        waveform_t waveform_state;
        float frequency;
        float frequency_range;
        float modulation_frequency;
        unsigned long time_ms;
        int port;
        int port_last;
        unsigned char debug;
        void set_pin(float pin,float value);
        void pulse(float pin,float duration);
        void square_wave(float pin, float frequency);
        void fm_waveform(float pin, float base_frequency, float frequency_range, float modulation_frequency);
        void start_read_pins(void);
        void stop_read_pins(void);
        void stop_waveform(float pin);
        void set_timer_channel(float pin);
        void read_pins(unsigned char force);
};
