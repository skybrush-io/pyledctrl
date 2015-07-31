/**
 * \file signal_decoders.h
 * \brief Decoding of PPM and PWM signals.
 */

#ifndef SIGNAL_DECODERS_H
#define SIGNAL_DECODERS_H

#include "config.h"

/**
 * Abstract superclass for signal sources.
 */
class SignalSource {
  public:
    /**
     * Destructor.
     */
    virtual ~SignalSource() {}
    
    /**
     * Returns a noise-filtered, accurate value of the given channel.
     * 
     * \param  channelIndex  index of the channel to read.
     */
    virtual volatile u8 accurateChannelValue(u8 channelIndex) const = 0;
    
    /**
     * Returns the current value of the given channel.
     *
     * \param  channelIndex  index of the channel to read
     */
    virtual u8 channelValue(u8 channelIndex) const = 0;

    /**
     * Dumps some debug information into the serial port.
     */
    virtual void dumpDebugInformation() const = 0;

    /**
     * Returns the number of channels for this signal source.
     */
    virtual u8 numChannels() const = 0;
};

/**
 * Interrupt handler for the PPM signal source.
 */
void PPMSignalSource_interruptHandler();

/**
 * PPM signal source.
 */
class PPMSignalSource : public SignalSource {
  private:
    /**
     * Index of the interrupt that will notify us when the signal changes.
     */
    u8 m_interruptIndex;

  public:
    /**
     * Constructor.
     */
    explicit PPMSignalSource(u8 interruptIndex) : SignalSource(),
      m_interruptIndex(interruptIndex) {
      assert(interruptIndex >= 0 && interruptIndex < 2);
    }

    volatile u8 accurateChannelValue(u8 channelIndex) const;
    u8 channelValue(u8 channelIndex) const;
    void dumpDebugInformation() const;
    u8 numChannels() const;

    /**
     * Attaches the necessary interrupt handler that will handle the PPM signal source.
     */
    void attachInterruptHandler() const;

  private:
    /**
     * Rescales the length of a period in microseconds to the corresponding channel
     * value.
     */
    static u8 rescalePeriodLengthToByte(long periodLength);

    friend void PPMSignalSource_interruptHandler();
};

/**
 * Interrupt handler for the PWM signal source.
 */
void PWMSignalSource_interruptHandler();

/**
 * PWM signal source.
 */
class PWMSignalSource : public SignalSource {
  private:
    /**
     * Index of the interrupt that will notify us when the signal changes.
     */
    u8 m_interruptIndex;
    
    /**
     * Index of the pin on which the signal is read.
     */
    u8 m_pinIndex;
    
  public:
    /**
     * Constructor.
     * 
     * \param  pinIndex  index of the pin on which the signal is read
     */
    explicit PWMSignalSource(u8 interruptIndex) : SignalSource(), m_interruptIndex(interruptIndex) {
      // Arduino Nano interrupt 0 belongs to pin 2, interrupt 1 belongs to pin 3
      assert(interruptIndex >= 0 && interruptIndex < 2);
      m_pinIndex = interruptIndex + 2;
    }

    volatile u8 accurateChannelValue(u8 channelIndex) const;
    u8 channelValue(u8 channelIndex) const;
    void dumpDebugInformation() const;
    u8 numChannels() const;

    /**
     * Attaches the necessary interrupt handler that will handle the PPM signal source.
     */
    void attachInterruptHandler() const;

    friend void PWMSignalSource_interruptHandler();
};

/**
 * Dummy signal source that can be used to simulate RC signals using digital
 * and analog pins in the absence of a "real" RC controller and receiver.
 * Useful for testing purposes.
 */
class DummySignalSource : public SignalSource {
  private:
    /**
     * The number of channels.
     */
    u8 m_numChannels;

    /**
     * Index of the pin corresponding to each of the channels.
     */
    u8* m_pins;
    
  public:
    /**
     * Constructor.
     * 
     * \param  numChannels  the number of channels in the source
     * \param  pins         the pins corresponding to each of the channels
     */
    explicit DummySignalSource(u8 numChannels=0, const u8* pins=0) : SignalSource(), m_numChannels(numChannels) {
      assert(pins != 0 || numChannels == 0);
      m_pins = new u8[numChannels];
      memcpy(m_pins, pins, numChannels * sizeof(u8));
    }

    ~DummySignalSource() {
      delete m_pins;
    }
    
    volatile u8 accurateChannelValue(u8 channelIndex) const;
    u8 channelValue(u8 channelIndex) const;
    void dumpDebugInformation() const;
    u8 numChannels() const;
};

#endif
