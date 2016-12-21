#define COMPARE 59//5 kHz, FCPU is 14.7456MHz, comp=FCPU/(f*prescale)+1
#define PRESCALE 4 //64 prescale

byte cmd = 0;
byte send_data=true;
byte port,port_prev;
unsigned long time;

ISR(TIMER1_COMPA_vect) {
   PORTB |=(1<<2);
   TCNT1L=0;
   TCNT1H=0;
   time = millis();
   port=PIND&0xfc;
   if (port!=port_prev)
   {
     if (send_data)
     {
       Serial.print(time);
       Serial.print(" ms: ");
       Serial.print(port,HEX);
       Serial.print("\r\n");
     }
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

void setup()
{
  DDRB|=1<<2|1;
  Serial.begin(115200);
  init_digital_input_timer();
  port_prev=0;
  port=0;
  sei();
}

void loop()
{
  cmd = Serial.read();
  switch (cmd) {
    case 'e':
      send_data=true;
      break;
    case 'd':
      send_data=false;
      break;
    default:
      break;
  }

}

