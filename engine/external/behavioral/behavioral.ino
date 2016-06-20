
char b;
unsigned long prev,now;
byte dir;
byte pin;
long delta_time;
unsigned long t0,t1;
byte led_state=0;
//TODO: test ISR runtime, Do not send message if more than 50% cpu time is used
ISR(PCINT0_vect ) {
  //cli();
  PORTD|=(1<<5);
  pin=(PINB&(1<<4))>>4;
  if (pin==0)
  {
    dir=(PINB&(1<<3))>>3;
    now=millis();
    delta_time=now-prev;
    if (dir==1)
    {
      delta_time*=-1;
    }
    prev=now;
    if (abs(delta_time)>10)
    {
      Serial.print("deltaT");
      Serial.print(delta_time);
/*     Serial.print(" dir= ");
       Serial.print(dir);
     Serial.print("pins= ");
//    Serial.print(PINB&(1<<4));
    Serial.print((PINB&(1<<4))|(PINB&(1<<3)));*/
      Serial.print("ms\r\n");
    }    
  }
 //sei();
 PORTD&=~(1<<5);
}

void setup() {
  Serial.begin(115200);
  DDRB=0x7;
  PORTB=0x0;
  //Enable PCINT4
   PCMSK0|=1<<4;
   PCICR=1;
  // sei();
   prev=millis();
   //For testing:
   DDRD|=(1<<7)|(1<<6)|(1<<5);
   randomSeed(0);
   t1=millis();
   pinMode(13, OUTPUT);
}

byte channel, pulse_width;
int emspd,noise=0;

void loop() {  
  b = Serial.read();
  /*
  Command structure:
  bit 7,6: channel
  bit 5..0: pulse duration x 5ms, 0: off, 0x3F: on
  */
  if (b!=-1) {
      channel=(b&0xC0)>>6;
      pulse_width=b&0x3F;
      switch (pulse_width)
     {
       case 0:
         PORTB&=~(1<<channel);
         break;
       case 0x3F:
         PORTB|=(1<<channel);
         break;
       default:
         PORTB|=(1<<channel);
         delay(pulse_width*5);
         PORTB&=~(1<<channel);   
     }
    }
  if (0)
  {
    noise=random(-10,10);
    emspd=-30+noise;
    Serial.print("deltaT");
    Serial.print(emspd);
    Serial.print("ms\r\n");
    delay(30);
  }
  if (0){
   t0=millis()/1000;
   if (t0%2==0)
   {
    digitalWrite(13, HIGH);
   }
   else
   {
    digitalWrite(13, LOW);
   }
   
   
  }
 
}
