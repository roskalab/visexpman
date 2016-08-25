#define NSAMPLES 4
#define PULSE_WIDTH_120HZ (1000000/(120*6/2))
#define PULSE_WIDTH_60HZ (1000000/(60*6/2))
#define _60HZ_US (1000000/60)*2
#define _120HZ_US (1000000/120)*2
byte input_state;
unsigned long period=0;
unsigned long pulse_width=0;
unsigned long period_calc;
unsigned long periods[NSAMPLES];
byte index=0;
bool frq_decided;
unsigned long last_isr,now;

ISR(INT0_vect) {
  input_state++;
  if (input_state==4)
  {
    input_state=0;
  }
  if (input_state==3)
  {    
    now=micros();
    if (frq_decided)
    {
      PORTD&=~(1<<6);//pmt off
      PORTD|=1<<7;//stim led on
      delayMicroseconds(pulse_width);
      PORTD&=~(1<<7);//stim led off
      PORTD|=1<<6;//pmt on 
    } 
    else if (~frq_decided)
    {
      
      period_calc=(now-last_isr);
      last_isr=now;
      periods[index]=period_calc;
      index++;
      if (index==NSAMPLES)
      {
        period_calc=0;
        
        for(int i=0;i<NSAMPLES;i++)
        {
          period_calc+=periods[i];
        }
        period_calc/=NSAMPLES;
        /*Serial.print(period_calc);
        Serial.print(' ');
        Serial.print(_60HZ_US);
        Serial.print(' ');
        Serial.print(PULSE_WIDTH_60HZ);
        Serial.print(' ');*/
        if ((0.8*_60HZ_US<period_calc)&&(1.2*_60HZ_US>period_calc))
        {
          pulse_width=PULSE_WIDTH_60HZ;
          frq_decided=true;
        }
        else if ((0.8*_120HZ_US<period_calc)&&(1.2*_120HZ_US>period_calc))
        {
          pulse_width=PULSE_WIDTH_120HZ;
          frq_decided=true;
        }
        else
        {
          index=0;
        }
        /*Serial.print(pulse_width);
        Serial.print("\r\n");*/        
      }     
    }
    else
    {
      //overflow, do not update period
    }    
  }
}


void setup() {
  Serial.begin(115200);
  DDRD&=~(1<<2);//pind2 int0
  DDRD|=(1<<7);//pind7 stimulus led
  DDRD|=(1<<6);//pind6 pmt enable
  PORTD&=~(1<<7);
  PORTD&=~(1<<6);
  EICRA|=3;//both edges
  EIMSK|=1;
  input_state=0;
  last_isr=micros();
  period=PULSE_WIDTH_120HZ;
  frq_decided=false;
  sei();

}

void loop() {
  /*digitalWrite(7, HIGH);
  delay(2);
  digitalWrite(7, LOW);
  delay(3);*/

}
