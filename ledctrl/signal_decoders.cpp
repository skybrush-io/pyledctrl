#include <math.h>
#include "signal_decoders.h"

/**
 * \def PPM_NUMBER_OF_EDGES
 * Defines how many edges there are in a single PPM signal period (8 channels:
 * 8 rising edge and 1 rising edge in the next cycle, which indicates the next
 * period and the end of the current one).
 */
#define PPM_NUMBER_OF_EDGES 8

/**
 * \def PPM_MINIMUM_GAP_LENGTH_US
 * Length of a frame gap in the PPM signal (in microseconds).
 */
#define PPM_MINIMUM_GAP_LENGTH_US 4000

/**
 * \def PPM_SAMPLE_COUNT
 * Defines how many samples will be used to calculating the accurate PPM signals.
 */
#define PPM_SAMPLE_COUNT 10

/**
 * Stores the index of the current PPM channel.
 */
static volatile int ppmSignalSource_currentChannel;

/**
 * Stores the timestamp corresponding to the last invocation of the PPM interrupt
 * handler.
 */
static volatile long ppmSignalSource_lastTime;

/**
 * Stores the length of the last full period of the PPM signal.
 */
static volatile long ppmSignalSource_fullPeriodLength;

/**
 * Stores the start time of the last full period of the PPM signal.
 */
static volatile long ppmSignalSource_lastFullPeriodStartTime;

/**
 * Stores the lengths of the periods corresponding to the individual channels
 * in the last full period of the PPM signal.
 */
static volatile long ppmSignalSource_periods[PPM_NUMBER_OF_EDGES];

volatile u8 PPMSignalSource::accurateChannelValue(u8 channelIndex) const {
  long accurateValue = 0;
  u8 numSamples = 0;
  long previousValue;
  long currentValue;
  u8 i;

  previousValue = ppmSignalSource_periods[channelIndex];
  for (i = 1; i < PPM_SAMPLE_COUNT; i++) {
    currentValue = ppmSignalSource_periods[channelIndex];
    if (abs(currentValue - previousValue) < 100) {
      accurateValue += currentValue;
      numSamples++;
    }
    previousValue = currentValue;
  }

  accurateValue /= numSamples;
  
  return rescalePeriodLengthToByte(accurateValue);
}

void PPMSignalSource::attachInterruptHandler() const {
  attachInterrupt(m_interruptIndex, PPMSignalSource_interruptHandler, RISING);
}

u8 PPMSignalSource::channelValue(u8 channelIndex) const {
  return rescalePeriodLengthToByte(ppmSignalSource_periods[channelIndex]);
}

void PPMSignalSource_interruptHandler() {
  long currentTime = micros();
  long periodLength = currentTime - ppmSignalSource_lastTime;
  
  ppmSignalSource_currentChannel++;
  if (ppmSignalSource_currentChannel >= PPM_NUMBER_OF_EDGES ||
      periodLength >= PPM_MINIMUM_GAP_LENGTH_US) {
    ppmSignalSource_currentChannel = -1;
    ppmSignalSource_fullPeriodLength = currentTime - ppmSignalSource_lastFullPeriodStartTime;
    ppmSignalSource_lastFullPeriodStartTime = currentTime;
  } else {
    ppmSignalSource_periods[ppmSignalSource_currentChannel] = periodLength;
  }

  ppmSignalSource_lastTime = currentTime;
}

void PPMSignalSource::dumpDebugInformation() const {
  int i;

  for (i = 0; i < PPM_NUMBER_OF_EDGES; i++) {
    Serial.print(" #");
    Serial.print(i);
    Serial.print(": ");
    Serial.print(ppmSignalSource_periods[i]);
  }
  Serial.print(" Current channel: ");
  Serial.print(ppmSignalSource_currentChannel);
  Serial.print(" Period length: ");
  Serial.println(ppmSignalSource_fullPeriodLength);
}

u8 PPMSignalSource::numChannels() const {
  return PPM_NUMBER_OF_EDGES-1;
}

u8 PPMSignalSource::rescalePeriodLengthToByte(long periodLength) {
#define MIN_PERIOD_LENGTH 1100
#define MAX_PERIOD_LENGTH 1900
  periodLength = (
    constrain(periodLength, MIN_PERIOD_LENGTH, MAX_PERIOD_LENGTH) - MIN_PERIOD_LENGTH
  ) * (255.0 / (MAX_PERIOD_LENGTH-MIN_PERIOD_LENGTH));
#undef MIN_PERIOD_LENGTH
#undef MAX_PERIOD_LENGTH
  return periodLength;
}

/*======================================================================================*/

/**
 * Variable that holds the index of the pin on which the PWM signal comes according
 * to the "current" PWMSignalSource.
 */
static volatile u8 currentPWMPinIndex = 0;

/**
 * Stores the timestamp corresponding to the last invocation of the interrupt
 * handler.
 */
static volatile long pwmSignalSource_lastTime;

/**
 * Stores the length of the last full period. 
 */
static volatile long pwmSignalSource_lastPeriodLength;

/**
 * Stores the start time of the current period.
 */
static volatile long pwmSignalSource_periodStartTime;

/**
 * Stores the length of the "high" part of the last full period. 
 */
static volatile long pwmSignalSource_highTime;

/**
 * Stores the length of the "low" part of the last full period. 
 */
static volatile long pwmSignalSource_lowTime;

volatile u8 PWMSignalSource::accurateChannelValue(u8 channelIndex) const {
  return channelValue(channelIndex);
}

void PWMSignalSource::attachInterruptHandler() const {
  detachInterrupt(m_interruptIndex);
  currentPWMPinIndex = m_pinIndex;
  attachInterrupt(m_interruptIndex, PWMSignalSource_interruptHandler, CHANGE);
}

u8 PWMSignalSource::channelValue(u8 channelIndex) const {
  u8 convertedValue = (u8)((float)pwmSignalSource_highTime/100);
  return convertedValue;
}

void PWMSignalSource_interruptHandler() {
  long currentTime = micros();
  
  if (bitRead(PIND, currentPWMPinIndex) == HIGH) {
    pwmSignalSource_lastPeriodLength = currentTime - pwmSignalSource_periodStartTime;
    pwmSignalSource_highTime = currentTime - pwmSignalSource_lastTime;
  } else {
    pwmSignalSource_lowTime = currentTime - pwmSignalSource_lastTime;
  }
  
  pwmSignalSource_lastTime = currentTime;
}

u8 PWMSignalSource::numChannels() const {
  return 0;    // TODO: update when we have proper PWM decoding
}

void PWMSignalSource::dumpDebugInformation() const {
  Serial.print(" high: ");
  Serial.print(pwmSignalSource_highTime);
  Serial.print("  low: ");
  Serial.print(pwmSignalSource_lowTime);
  if (abs(pwmSignalSource_lastPeriodLength - pwmSignalSource_highTime - pwmSignalSource_lowTime) < 50) {
    Serial.println("  [ok]");
  } else {
    Serial.println("  [not ok]");
  }
}
    
/*======================================================================================*/

volatile u8 DummySignalSource::accurateChannelValue(u8 channelIndex) const {
  return channelValue(channelIndex);
}

u8 DummySignalSource::channelValue(u8 channelIndex) const {
  assert(channelIndex >= 0 && channelIndex < m_numChannels);
  return analogRead(m_pins[channelIndex]);
}

void DummySignalSource::dumpDebugInformation() const {
  int i, n = numChannels();
  
  for (i = 0; i < n; i++) {
    Serial.print(" #");
    Serial.print(i);
    Serial.print(": ");
    Serial.print(channelValue(i));
  }
  Serial.println("");
}

u8 DummySignalSource::numChannels() const {
  return m_numChannels;
}
