
#include "ioboard_commands.h"
#include "config.h"
#include <EEPROM.h>
/*
Arduino pin 0-1: reserved
Arduino pin 2-4: input: level changes are captured and timestamps are sent over usb/serial port
Arduino pin 5-7: output: level, pulse can be generated.
Arduino pin 9: digital waveform generation

Commands:
set_pin,pin,state: sets pin to state which can be 0.0 or 1.0
pulse,pin,duration: generates a pulse on pin with with of duration [ms]
waveform,frequency,frequency_range,modulation_frequency: waveform is generated on D9 pin. If frequency_range and modulation_frequency are 0, it is a simple square wave at frequency.
      In fm waveform mode the frequency is recalculated in every 4th call of 2 kHz timer ISR.
stop: terminates waveform generation
reset: stop all activity on iobaord
start_read_pins: pin 2-4 will be sampled with 2 kHz (TIMER_FRQ), upon value change corresponding timestamp is sent via UART
stop_read_pins: stop sampling pin 2-4.
get_id: read device id stored in eeprom
set_id: reprogram device id to eeprom
set_led,state: set's the arduino board's led
elongate,status,pin,width in us: elongates a short pulse detected on pin2 by INT0. pin 5-7 can be selected as output

*/

#define IDLE_ST 0
#define WAIT_PAR_ST 1
#define PULSE_WIDTH 2

char b;
byte state;
byte par;

byte cmd = 0;
byte send_data=true;
byte port,port_prev,waveform_pin;
unsigned long time;
bool force_read_pin=false;
bool enable_waveform=false;
byte frequency;
int period;
IOBoardCommands iobc;


ISR(TIMER2_COMPA_vect) {
   TCNT2=0;
   iobc.isr();
}

ISR(TIMER1_COMPA_vect)
{
  iobc.waveform_isr();
}

ISR(INT0_vect)
{
  iobc.elongate_isr();
}

ISR(INT1_vect)
{
  Serial.println("INT1");
}


void setup() {
  //Serial.begin(115200);
  iobc=IOBoardCommands();
  //DDRB|=(1<<1);
  //DDRD|=(1<<5);
  //TCCR1A|=(1<<4);
  //TCCR1B|=(1<<3)|3;//1/256 prescale
  //OCR1A=300;
  //OCR1AL=200;
  
  
  //pinMode(9, OUTPUT);
  
}

void loop()
{
  static char c[2];
  if (Serial.available()>0)
  {
    c[0]=Serial.read();
    c[1]=0;
    iobc.put(c);
  }
  iobc.run();
}
