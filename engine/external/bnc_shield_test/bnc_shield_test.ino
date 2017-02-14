#include "Arduino.h"
#define LED0  8
#define LED1  9

#define SLAVESELECTPIN 10
#define DAC_READBACK_PIN 3

#define D0_AI0_SELECT 5
#define D1_AI1_SELECT 6
#define D2_DAC_SELECT 7

#define ADCREF 1.1
#define ADCMAXCOUNT 1023
#define ADC_SCALE (float)(ADCREF/ADCMAXCOUNT)

#define SELECT_D0 digitalWrite(D0_AI0_SELECT, HIGH)
#define SELECT_AI0 digitalWrite(D0_AI0_SELECT, LOW)
#define SELECT_D1 digitalWrite(D1_AI1_SELECT, HIGH)
#define SELECT_AI1 digitalWrite(D1_AI1_SELECT, LOW)
#define SELECT_D2 digitalWrite(D2_DAC_SELECT, HIGH)
#define SELECT_DAC digitalWrite(D2_DAC_SELECT, LOW)

#define SLAVESELECTPIN 10

#define VREF1 0.45
#define VREF2 1.0
#define VOLTAGE_ERROR 20e-3

class BncShieldTester {
  public:
    BncShieldTester(void);
    void run(void);
    void led(void);
    void digital_loopback(int out,int in);
    void init_dac(void);
    void spi_transfer(char c);
    float read_dac(void);
    void set_dac(float v);
    void dac_selftest(void);
    void analog_loopback(int aichannel);

};

BncShieldTester::BncShieldTester(void)
{
  Serial.begin(115200);
  pinMode(LED0, OUTPUT);
  pinMode(LED1, OUTPUT);
  pinMode(D0_AI0_SELECT, OUTPUT);
  pinMode(D1_AI1_SELECT, OUTPUT);
  pinMode(D2_DAC_SELECT, OUTPUT);
  init_dac();
  analogReference(INTERNAL);//1.1V internal reference selected
}

void BncShieldTester::run(void)
{
  led();
  digital_loopback(1,2);
  digital_loopback(2,1);
  digital_loopback(0,2);
  digital_loopback(2,0);
  digital_loopback(3,4);
  digital_loopback(4,3);
  analog_loopback(0);
  analog_loopback(1);
  analog_loopback(3);
  delay(5000);
}

void BncShieldTester::init_dac(void)
{
  pinMode(13, OUTPUT);//SCK and MOSI outputs
  pinMode(11, OUTPUT);
  SPCR = (1<<SPE)|(1<<MSTR)|(1<<SPR1)|(1<<SPR0)|(1<<CPHA)|(1<<CPOL);//fclk/128 =115200 Hz ->70 us byte time
  pinMode(SLAVESELECTPIN,OUTPUT);
  digitalWrite(SLAVESELECTPIN, HIGH);//goes to init
}

void BncShieldTester::spi_transfer(char c)
{
  SPDR = c;
  delayMicroseconds(70);
}

void BncShieldTester::set_dac(float v)
{
  byte w1,w2;
  int dac_value;
  dac_value=(int)(1000*v);//1mV =  1 dac value
  w1=1<<4;//shutdown inv=1, channel A, gain = 2, 1 dac = 1 mV
  w1|=(byte)((dac_value&0x0F00)>>8);
  w2=(byte)(dac_value&0x00FF);
  digitalWrite(SLAVESELECTPIN, LOW);
  spi_transfer(w1);
  spi_transfer(w2);
  digitalWrite(SLAVESELECTPIN, HIGH);
}

float BncShieldTester::read_dac(void)
{
  int adc_val;
  float readback_voltage;
  adc_val = analogRead(DAC_READBACK_PIN);
  
  readback_voltage=(float)(adc_val*ADC_SCALE);
  return readback_voltage;
}

void BncShieldTester::led(void)
{
  Serial.print("LED test "); 
  digitalWrite(LED0, HIGH);
  digitalWrite(LED1, HIGH);
  delay(1000);
  digitalWrite(LED0, LOW);
  digitalWrite(LED1, LOW);
  Serial.println("OK");
}

void BncShieldTester::digital_loopback(int out,int in)
{
  int val1,val0;
  if ((in==0) || (out==0))
  {
    SELECT_D0;
  }
  if ((in==1) || (out==1))
  {
    SELECT_D1;
  }
  if ((in==2) || (out==2))
  {
    SELECT_D2;
  }
  Serial.print("digital loopback test: ");
  Serial.print(out);
  Serial.print(" -> ");
  Serial.print(in);
  Serial.print(" ");
  pinMode(out, OUTPUT);
  pinMode(in, INPUT);
  digitalWrite(out, HIGH);
  delayMicroseconds(100);
  val1=digitalRead(in);
  digitalWrite(out, LOW);
  delayMicroseconds(100);
  val0=digitalRead(in);
  if ((val1==1) && (val0==0))
  {
    Serial.println("OK");
  }
  else
  {
    Serial.print("Failed: expected 1, measured ");
    Serial.print(val1);
    Serial.print(" expected 0, measured ");
    Serial.println(val0);
  }
}

void BncShieldTester::analog_loopback(int aichannel)
{
  int adc_val;
  float vread1,vread2;
  Serial.print("Analog loopback test DAC->");
  Serial.print(aichannel);
  Serial.print(" channel ");
  SELECT_DAC;
  switch (aichannel)
  {
    case 0:
      SELECT_AI0;
      break;
    case 1:
      SELECT_AI1;
      break;
    default:
      break;
  }
  set_dac(VREF1);
  delay(1);
  adc_val = analogRead(aichannel);
  vread1=(float)(adc_val*ADC_SCALE);
  set_dac(VREF2);
  delay(1);
  adc_val = analogRead(aichannel);
  vread2=(float)(adc_val*ADC_SCALE);
  set_dac(0.0);
  if ((abs(vread1-VREF1)<VOLTAGE_ERROR)&&(abs(vread2-VREF2)<VOLTAGE_ERROR))
  {
    Serial.println("OK");
  }
  else
  {
    Serial.print("Failed, vref1=");
    Serial.print(VREF1);
    Serial.print(" V, measured: ");
    Serial.print(vread1);
    Serial.print(", vref2=");
    Serial.print(VREF2);
    Serial.print(" V, measured: ");
    Serial.println(vread2);
  }
}

BncShieldTester aot;

void setup() {
  aot=BncShieldTester();  
}

void loop() {
  aot.run();

}
