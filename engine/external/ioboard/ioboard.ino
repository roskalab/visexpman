
#include "ioboard_commands.h"
#include "config.h"
/*
Arduino pin 0-1: reserved
Arduino pin 2-4: input: level changes are captured and timestamps are sent over usb/serial port
Arduino pin 5-7: output: level, pulse or pulse train waveform can be generated.

Commands:
'o': set level, + 1byte binary packed pin values 
'p': generate single pulse on pins determined by subsequent byte value. The lenght of the pulse is 2 ms (PULSE_WIDTH)
'f': set frequency, subsequent byte is interpreted in Hz
'w': toggle enable waveform state
'e': enable send input pin state
'd': disable send input pin state
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

void setup() {
  iobc=IOBoardCommands();
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


void loop1() {
  b = Serial.read();
  if (b!=-1) {
    switch (state)
    {
      case IDLE_ST:
        switch (b)
        {
          case 'o'://output
          case 'p'://pulse
            cmd=b;
            state=WAIT_PAR_ST;
            break;
          case 'r'://read pins
            force_read_pin=true;
            state=IDLE_ST;
            break;
          case 'e'://enable send data
            send_data=true;
            state=IDLE_ST;
            break;
          case 'd'://disable send data
            send_data=false;
            state=IDLE_ST;
            break;
          case 'f'://set frequency
            state=WAIT_PAR_ST;
            cmd=b;
          case 'w': //enable pulse train waveform
            cmd=b;
            state=WAIT_PAR_ST;
            break;
          default:
            state=IDLE_ST;
            break;
        }
        break;
      case WAIT_PAR_ST:
        par = b;
        switch (cmd) {
          case 'o':
              PORTD = par&OUTPORT_MASK;
              break;
          case 'p':
              PORTD |= par&OUTPORT_MASK;
              delay(PULSE_WIDTH);
              PORTD &= ~(par&OUTPORT_MASK);
              break;
          case 'f':
              frequency=par;
              period=1000/par/2;
              break;
          case 'w':
              waveform_pin=par;
              if (enable_waveform)
              {
                enable_waveform=false;
              }
              else
              {
                enable_waveform=true;
              }
              
              //enable_waveform=~enable_waveform;
              break;
          case 'a':
              break;
        }
        state=IDLE_ST;
        break;
      default:
        break;
    }  
  }
  if (enable_waveform)
  {
    PORTD |= waveform_pin&OUTPORT_MASK;
    digitalWrite(LED_BUILTIN, HIGH);
    delay(period);
    PORTD &= ~(waveform_pin&OUTPORT_MASK);
    digitalWrite(LED_BUILTIN, LOW);
    delay(period);
  }
  /*PORTD |= (1<<5)&OUTPORT_MASK;
  delay(50);
  PORTD &= ~((1<<5)&OUTPORT_MASK);
  delay(50);*/
}
