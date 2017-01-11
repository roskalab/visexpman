#include "dac.h"
#include "config.h"
#include "Arduino.h"

Dac::Dac(void)
{
  DDRB&=(1<<5)|(1<<3);//SCK and MOSI outputs
  SPCR = (1<<SPE)|(1<<MSTR)|(1<<SPR0);
  digitalWrite(SLAVESELECTPIN, HIGH);//goes to init
    
}

void Dac::set(float voltage)
{    
    char w1,w2;
    int dac_value;
    dac_value=(int)(1000*voltage);//1mV =  1 dac value
    w1=1<<4;//shutdown inv=1, channel A, gain = 2, 1 dac = 1 mV
    w1|=(char)((dac_value&0x0F00)>>8);
    w2=(char)(dac_value&0x00FF);
    digitalWrite(SLAVESELECTPIN, LOW);
    spi_transfer(w1);
    spi_transfer(w2);
    digitalWrite(SLAVESELECTPIN, HIGH);
    
}
void Dac::spi_transfer(char c)
{
  SPDR = c;
  while (!(SPSR & (1<<SPIF)))
    ;
}

