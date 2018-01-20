//Main timer
#define CPU_FRQ  16e6//14.7456e6
#define PRESCALER  64
#define TIMER_FRQ  2e3
#define TIMER_COMPARE (int)(CPU_FRQ/(PRESCALER*TIMER_FRQ)-1)
//#define TIMER_COMPARE 116//2 kHz, FCPU is 14.7456MHz, comp=FCPU/(f*prescale)-1
#define TIMER_PRESCALE 4 //64 prescale

#define DEBUGPIN 13
#define DEBUG_PULSE_DURATION_US 10

#define OUTPORT_MASK 0xe0
#define INPORT_MASK 0x1C


