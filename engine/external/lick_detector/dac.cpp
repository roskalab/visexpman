#include "dac.h"
#include "config.h"
#include "Arduino.h"
#include <SPI.h>

Dac::Dac(void)
{
    digitalWrite(SLAVESELECTPIN, HIGH);//goes to init
    SPI.begin(); //goes to init
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
    SPI.transfer(w1);
    SPI.transfer(w2);
    digitalWrite(SLAVESELECTPIN, HIGH);
    
}
