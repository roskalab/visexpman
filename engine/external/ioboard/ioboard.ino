#define COMPARE 116//2 kHz, FCPU is 14.7456MHz, comp=FCPU/(f*prescale)+1
#define PRESCALE 4 //64 prescale
#define IDLE_ST 0
#define WAIT_PAR_ST 1
#define OUTPORT_MASK 0xC0

char b;
byte state;
byte par;

byte cmd = 0;
byte send_data=true;
byte port,port_prev;
unsigned long time;
bool force_read_pin=false;

ISR(TIMER1_COMPA_vect) {
   PORTB |=(1<<2);//D10 output
   TCNT1L=0;
   TCNT1H=0;
   time = millis();
   port=PIND&0xfc;
   if ((port!=port_prev) || force_read_pin)
   {
     if (send_data)
     {
       Serial.print(time);
       Serial.print(" ms: ");
       Serial.print(port,HEX);
       Serial.print("\r\n");
     }
     force_read_pin=false;
     port_prev=port;
   }
   PORTB &=~(1<<2);
}

void init_digital_input_timer()
{
   TCCR1B = PRESCALE;
   OCR1AH = 0;
   OCR1AL = COMPARE;
   TIMSK1 |= 1<<1;
}

void setup() {
  Serial.begin(115200);
  DDRB|=1<<2;//D10 output for debugging
  DDRD=OUTPORT_MASK;//port 2-4 input, port 5-7 output
  PORTD=0x00;
  state=IDLE_ST;
  init_digital_input_timer();
  port_prev=0;
  port=0;
  sei();
}


void loop() {
  b = Serial.read();
  if (b!=-1) {
    //Serial.write(state+0x30);
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
          default:
            state=IDLE_ST;
            break;
        }
        break;
      case WAIT_PAR_ST:
        par = b;
        switch (cmd) {
          case 'd':
              PORTD = par&OUTPORT_MASK;
              break;
          case 'p':
              PORTD |= par&OUTPORT_MASK;
              delay(2);
              PORTD &= ~(par&OUTPORT_MASK);
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
  
  /*if (b>0)
  {
    if (b=='(' &&!eop_received)
    {
      eoc_received=true;
    }
    else if (b==')' &&eoc_received)
    {
      eop_received=true;
    }
    buf[index]=b;
    index++;
    if (index==BUFLEN){
       index=0;
    }
    
    
    if (eoc_received && eop_received&&1)
    {      
      val=buf[index-2];
      cmd=buf[index-4];
      Serial.write(cmd);
      switch (cmd) {
        case 'd':
            PORTD = val&0xFC;
            break;
        case 'p':
            PORTD |= val&0xFC;
            delay(2);
            PORTD &= ~(val&0xFC);
            break;
        case 'a':
            break;
      eoc_received=false;
      eop_received=false;
      index=0;
      }
    }
  }*/
  
}
