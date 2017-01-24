#include "dac.h"
#include "config.h"
#include "Arduino.h"

Dac::Dac(void)
{
  pinMode(13, OUTPUT);//SCK and MOSI outputs
  pinMode(11, OUTPUT);
  SPCR = (1<<SPE)|(1<<MSTR)|(1<<SPR1)|(1<<SPR0)|(1<<CPHA)|(1<<CPOL);//fclk/128 =115200 Hz ->70 us byte time
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

int Dac::check_output(float expected_voltage)
{
  int dac_readback;
  float dac_readback_voltage;
  dac_readback=analogRead(A3);
  dac_readback_voltage=(float)(ADC_SCALE*dac_readback);
  if (abs(dac_readback_voltage-expected_voltage)>20e-3)
  {
    Serial.println(dac_readback_voltage);
    return 1;
  }
  else
  {
    return 0;
  }
}
int Dac::test(void)
{
  int res1,res2;
  set(40e-3);
  res1=check_output(40e-3);
  set(0.0);
  res1=check_output(0.0);
  return res1+res2;
}

