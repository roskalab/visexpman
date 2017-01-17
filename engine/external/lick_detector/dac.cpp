#include "dac.h"
#include "config.h"
#include "Arduino.h"

Dac::Dac(void)
{
  pinMode(13, OUTPUT);//SCK and MOSI outputs
  pinMode(11, OUTPUT);
  SPCR = (1<<SPE)|(1<<MSTR)|(1<<SPR1)|(1<<SPR0);//fclk/128 =115200 Hz ->70 us byte time
  pinMode(SLAVESELECTPIN,OUTPUT);
  digitalWrite(SLAVESELECTPIN, HIGH);//goes to init
  pinMode(7, OUTPUT);
  digitalWrite(7, LOW);//LOW: Select dac route with analog switch
    
}

void Dac::set(float voltage)
{    
    byte w1,w2;
    int dac_value;
    dac_value=(int)(1000*voltage);//1mV =  1 dac value
    w1=1<<4;//shutdown inv=1, channel A, gain = 2, 1 dac = 1 mV
    w1|=(byte)((dac_value&0x0F00)>>8);
    w2=(byte)(dac_value&0x00FF);
    digitalWrite(SLAVESELECTPIN, LOW);
    spi_transfer(w1);
    spi_transfer(w2);
    digitalWrite(SLAVESELECTPIN, HIGH);
    
}
void Dac::spi_transfer(char c)
{
  SPDR = c;
  delayMicroseconds(70);
  //while (!(SPSR & (1<<SPIF)))
  //  ;
}

