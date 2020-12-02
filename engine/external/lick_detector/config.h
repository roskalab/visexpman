#define QICHEN_SETUP 1
#define LICKPIN A5
#define LICKDETECTEDPIN 5
#if (QICHEN_SETUP==1)
  #define REWARDPIN 8
  #define LASERPIN 3
#else
  #define REWARDPIN 3
  #define LASERPIN 8
#endif
#define DEBUGPIN 4
#define SLAVESELECTPIN 10
#define ADCREF 1.1
#define ADCMAXCOUNT 1023
#define ADC_SCALE (float)(ADCREF/ADCMAXCOUNT)
#define DETECTOR_RUN_PERIOD_MS 10
#define LICK_DURATION_MIN 10e-3
#define LICK_DURATION_MAX 100e-3
#if (QICHEN_SETUP==1)
  #define LICK_THRESHOLD 0.10
#else
  #define LICK_THRESHOLD 0.25
#endif
#define DEBUG_PULSE_DURATION_US 200
