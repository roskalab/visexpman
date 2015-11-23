
char b;
byte state;
char cmd;
byte par;
#define IDLE_ST 0
#define WAIT_PAR_ST 1

void setup() {
  Serial.begin(115200);
  PIND=0xFC;
  PORTD=0x0;
  state=IDLE_ST;
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
          case 'd':
          case 'p':
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
          case 'd':
              PORTD = par&0xFC;
              break;
          case 'p':
              PORTD |= par&0xFC;
              delay(2);
              PORTD &= ~(par&0xFC);
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
