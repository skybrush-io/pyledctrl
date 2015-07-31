#include "signal_decoders.h"
#include "trigger.h"

static void fireTrigger(EdgeDetector* detector, long time, void* data) {
  Trigger* trigger = static_cast<Trigger*>(data);
  if (trigger != 0) {
    trigger->fire();
  }
}

Trigger::Trigger() : m_pSignalSource(0), m_channelIndex(0), m_edgeDetector() {
  m_edgeDetector.callbackData = this;
}

void Trigger::checkAndFireWhenNeeded() {
  if (m_pSignalSource == 0)
    return;

  u8 value = m_pSignalSource->channelValue(m_channelIndex);
  m_edgeDetector.feedAnalogSignal(value);
}

void Trigger::disable() {
  m_pSignalSource = 0;
  m_channelIndex = 0;
  m_edgeDetector.callbacks.rising = 0;
  m_edgeDetector.callbacks.falling = 0;
}

void Trigger::fire() {
  Serial.println("Trigger fired!");  
}

void Trigger::watchChannel(const SignalSource* signalSource, u8 channelIndex, u8 edge) {
  m_pSignalSource = signalSource;
  m_channelIndex = signalSource ? channelIndex : 0;
  
  if (m_pSignalSource != 0) {
    if (m_channelIndex >= m_pSignalSource->numChannels()) {
      disable();
      return;
    }
  }

  switch (edge) {
    case RISING:
      m_edgeDetector.callbacks.rising = fireTrigger;
      m_edgeDetector.callbacks.falling = 0;
      break;
      
    case FALLING:
      m_edgeDetector.callbacks.rising = 0;
      m_edgeDetector.callbacks.falling = fireTrigger;
      break;
      
    case CHANGE:
      m_edgeDetector.callbacks.rising = fireTrigger;
      m_edgeDetector.callbacks.falling = fireTrigger;
      break;

    default:
      disable();
      return;
  }

  m_edgeDetector.reset();
}

