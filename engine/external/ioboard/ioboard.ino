byte index;
#define BUFLEN 32
char buffer[BUFLEN];
void setup() {
  Serial.begin(115200);
  index=0;
  PIND=0xFC;
  PORTD=0x0;
}

char b;
char cmd;
byte val;
boolean eoc_received=false;
boolean eop_received=false;

void loop() {
  b = Serial.read();
  if (b>0)
  {
    if (b=='(' &&!eop_received)
    {
      eoc_received=true;
    }
    else if (b==')' &&eoc_received)
    {
      eop_received=true;
    }
    buffer[index]=b;
    index++;
    if (index==BUFLEN){
       index=0;
    }
    if (eoc_received && eop_received)
    {
      val=buffer[index-2];
      cmd=buffer[index-4];
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
      }
    }
  }
  
}
