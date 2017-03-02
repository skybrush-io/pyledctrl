#define __ASSERT_USE_STDERR

#include "config.h"
#include "calibration.h"
#include "commands.h"
#include "edge_detector.h"
#include "executor.h"
#include "led.h"
#include "led_strip.h"
#include "pyro.h"
#include "serial_protocol.h"
#include "signal_decoders.h"
#include "switch.h"

#include "bytecode_landing.h"
#include "bytecode_rc.h"

/**
 * The built-in LED of the board.
 */
LED builtinLed;

/**
 * The LED strip attached to the board.
 */
LEDStrip ledStrip(RED_PWM_PIN, GREEN_PWM_PIN, BLUE_PWM_PIN,
        WHITE_PWM_PIN, USE_WHITE_LED);

#ifdef MAIN_SWITCH_PIN
/**
 * An optional main switch that can be used to turn off the LED strip and
 * suspend execution.
 */
Switch mainSwitch(MAIN_SWITCH_PIN);
#endif

#ifdef VOLTMETER_PIN
/**
 * A voltmeter.
 */
VoltMeter voltmeter(VOLTMETER_PIN, LIGHT_COEFF);
#endif

#ifdef ENABLE_SERIAL_INPUT
/**
 * Parser for the messages coming on the serial port if we handle serial input.
 */
SerialProtocolParser serialProtocolParser;
#endif

#ifdef PYRO_PIN
/**
 * A pyro trigger pin
 */
Pyro pyroTrigger(PYRO_PIN);
#endif

/**
 * Command executor that is responsible for executing the scheduled bytecode
 * commands.
 */
CommandExecutor executor(&ledStrip);


// Set the following macro to the number of the test sequence that you want to start
// 0 = first simple test sequence
// 1 = testing transition types and easing functions
// 2 = testing jump instruction
// 3 = writable bytecode in SRAM with no program loaded by default
// 4 = writable bytecode in EEPROM with whatever program there is in the EEPROM
// 5 = read-only bytecode in PROGMEM
// 6 = read-only bytecode in PROGMEM, test code from pyledctrl, generated by "python bin/ledctrl compile data/test.led -o ledctrl/bytecode_test.h"
// 7 = read-only bytecode in PROGMEM, live sequence from DWD show, generated by "ledctrl compile show.sce -o show_{}.h"
// 8 = timing test pattern for calibrating the clock skew (red-green-blue-black, one second each).
//     Using this test sequence will automatically turn on the calibration mode (even if you did not define
//     it in config.h)
#define BYTECODE_INDEX 1

#if BYTECODE_INDEX == 0
#  include "bytecode_first_test.h"
#elif BYTECODE_INDEX == 1
#  include "bytecode_transition_test.h"
#elif BYTECODE_INDEX == 2
#  include "bytecode_3_test.h"
#elif BYTECODE_INDEX == 3
#  include "bytecode_empty_writable.h"
#elif BYTECODE_INDEX == 4
#  include "bytecode_eeprom.h"
#elif BYTECODE_INDEX == 5
#  include "bytecode_progmem.h"
#elif BYTECODE_INDEX == 6
#  include "bytecode_test.h"
#elif BYTECODE_INDEX == 7
#  include "show_2.h"
#elif BYTECODE_INDEX == 8
#  include "bytecode_timing_test.h"
#else
#  error "Invalid BYTECODE_INDEX value"
#endif

#if USE_PPM_REMOTE_CONTROLLER
PPMSignalSource signalSource(RC_INTERRUPT);
#elif USE_PWM_REMOTE_CONTROLLER
PWMSignalSource signalSource(RC_INTERRUPT);
#else
#define NUM_FAKE_SIGNAL_PINS 2
static const u8 signalSourcePins[NUM_FAKE_SIGNAL_PINS] = { A0, A5 };
DummySignalSource signalSource(NUM_FAKE_SIGNAL_PINS, signalSourcePins);
#endif

#ifdef CLOCK_SKEW_CALIBRATION
bool calibrationDone = 0;
#endif

// Declare some variables for the default values of the switches
// (main switch, landing switch, bytecode trigger switch). If the
// switch channel is defined in config.h, the callback functions
// will adjust these booleans.
bool mainSwitchState = 1;
bool landingSwitchState = 0;
bool bytecodeRCSwitchState = 0;
bool pyroSwitchState = 0;

void updatePyroTrigger() {
#ifdef PYRO_PIN
    if (pyroSwitchState) {
        pyroTrigger.on();
    } else {
        pyroTrigger.off();
    }
#endif
}

void turnAllLightsOff() {
    builtinLed.off();
    ledStrip.off();
}

void updateStateAfterSwitchesChanged() {
  BytecodeStore* desiredBytecodeStore = 0;
  
  if (!mainSwitchState) {
    /* Main switch is off, so we need to turn the lights off. The main loop will
     * return on its own */
    turnAllLightsOff();
    return;
  }
  
  /* Figure out which bytecode should be loaded. The combinations are as follows:
   *
   * landing switch = on,  bytecode RC switch = any ---> landing sequence
   * landing switch = off, bytecode RC switch = off ---> preprogrammed sequence
   * landing switch = off, bytecode RC switch = on  ---> lights controlled by RC channels
   */
  if (landingSwitchState) {
    /* Landing sequence */
    desiredBytecodeStore = &bytecodeStore_landing;
  } else if (bytecodeRCSwitchState) {
    /* Lights are controlled by RC channels */
    desiredBytecodeStore = &bytecodeStore_rc;
  } else {
    /* Standard pre-programmed bytecode must be running */
    desiredBytecodeStore = &bytecodeStore;
  }
  
  /* Main switch is on, we can check whether the right bytecode store is loaded.
   * If we must switch, we switch. We need this check because setBytecodeStore()
   * rewinds the executor unconditionally even if the same bytecoe store is
   * assigned. */
  if (executor.bytecodeStore() != desiredBytecodeStore) {
    executor.setBytecodeStore(desiredBytecodeStore);
  }
}

#ifdef MAIN_SWITCH_CHANNEL
EdgeDetector mainSwitchEdgeDetector;

void mainSwitchCallback(EdgeDetector* detector, long time, void* data) {
  mainSwitchState = detector->value();
  updateStateAfterSwitchesChanged();
  
  // if we just got a new ON state, we rewind the executor even if we stayed
  // on the same bytecode as before
  if (mainSwitchState) {
    executor.rewind();
  }
  
#ifdef CLOCK_SKEW_CALIBRATION
  // if we just got a new OFF state, and the calibration is not done yet, and the
  // internal clock of the executor is between 95% and 105% of the expected time, we finish the
  // calibration and store the results 
  if (!mainSwitchState && !calibrationDone) {
    float factor = finishCalibrationWithDuration(executor.absoluteToInternalTime(time), &ledStrip);
    if (factor > 0) {
      executor.setClockSkewCompensationFactor(factor);
      calibrationDone = 1;
    }
  }
#endif
}
#endif

#ifdef LANDING_SWITCH_CHANNEL
EdgeDetector landingSwitchEdgeDetector;

void landingSwitchCallback(EdgeDetector* detector, long time, void* data) {
  landingSwitchState = detector->value();
  updateStateAfterSwitchesChanged();
}

void setupLandingColor() {
#if defined(LEDCTRL_DEVICE_ID)
  // TODO: make this more configurable, currently it's hardcoded for the Shanghai show
  if (LEDCTRL_DEVICE_ID <= 5) {
    // The IRIS copters have IDs 1-5 and they have to be red
    setLandingColor(20, 0, 0);
  } else if (LEDCTRL_DEVICE_ID == 6 || LEDCTRL_DEVICE_ID == 7 || LEDCTRL_DEVICE_ID == 21 || LEDCTRL_DEVICE_ID == 34 || LEDCTRL_DEVICE_ID == 35) {
    // The old MikroKopters have IDs 6, 7, 21, 34 and 35 and they have to be green
    setLandingColor(0, 20, 0);
  } else {
    // All the other drones are blue
    setLandingColor(0, 0, 20);
  }
#else
  // No device ID is specified, so we just use a nice blueish hue
  setLandingColor(0, 127, 255);
#endif
}

#endif

#ifdef BYTECODE_RC_CHANNEL
EdgeDetector bytecodeRCEdgeDetector;

void bytecodeRCCallback(EdgeDetector* detector, long time, void* data) {
  bytecodeRCSwitchState = detector->value();
  updateStateAfterSwitchesChanged();
}
#endif

#ifdef PYRO_SWITCH_CHANNEL
EdgeDetector pyroSwitchEdgeDetector;

void pyroSwitchCallback(EdgeDetector* detector, long time, void* data) {
  pyroSwitchState = detector->value();
  updatePyroTrigger();
}
#endif

/**
 * Waits for the user to enter "?READY?" followed by a newline on the serial
 * console before letting the execution proceed.
 */
void waitForStartupSignal() {
  const char* startupSignal = "?READY?\n";
  const int startupSignalLength = strlen(startupSignal);
  const int jumpbackTable[] = { 0, 0, 0, 0, 0, 0, 1, 0 };
  const char* nextChar;
  int nextCharIndex;
  int charRead;

  // nextChar points to the next expected character in startupSignal
  // jumpback[] stores the index of the character to jump back to in case of a mismatch
  nextCharIndex = 0;
  nextChar = startupSignal;
  while (true) {
    if (Serial.available() > 0) {
      charRead = Serial.read();
      
      // Turn \r into \n so we become ignorant about line ending conventions
      if (charRead == '\r') {
        charRead = '\n';
      }

      // Did the user manage to match the next expected character?
      if (charRead == *nextChar) {
        // Yes, jump to the next character.
        nextCharIndex++;
        nextChar++;
        if (*nextChar == 0) {
          // Full match, we can return.
          break;
        }
      } else {
        // No, jump back and try to match there
        nextCharIndex = jumpbackTable[nextCharIndex];
        nextChar = startupSignal + nextCharIndex;
        if (charRead == *nextChar) {
          nextCharIndex++;
          nextChar++;
          if (*nextChar == 0) {
            // Full match, we can return.
            break;
          }
        }
      }
    }
  }
}

/**
 * Setup function; called once after a reset.
 */
void setup() {
  calibration_data_t calibrationData;
  
//---------------------------------------------- Set PWM frequency for D5 & D6 -------------------------------

//TCCR0B = TCCR0B & B11111000 | B00000001;    // set timer 0 divisor to     1 for PWM frequency of 62500.00 Hz
//TCCR0B = TCCR0B & B11111000 | B00000010;    // set timer 0 divisor to     8 for PWM frequency of  7812.50 Hz
//TCCR0B = TCCR0B & B11111000 | B00000011;    // set timer 0 divisor to    64 for PWM frequency of   976.56 Hz (The DEFAULT)
//TCCR0B = TCCR0B & B11111000 | B00000100;    // set timer 0 divisor to   256 for PWM frequency of   244.14 Hz (recommended for LED use but Timer0 is used by time functions...)
//TCCR0B = TCCR0B & B11111000 | B00000101;    // set timer 0 divisor to  1024 for PWM frequency of    61.04 Hz


//---------------------------------------------- Set PWM frequency for D9 & D10 ------------------------------

//TCCR1B = TCCR1B & B11111000 | B00000001;    // set timer 1 divisor to     1 for PWM frequency of 31372.55 Hz
//TCCR1B = TCCR1B & B11111000 | B00000010;    // set timer 1 divisor to     8 for PWM frequency of  3921.16 Hz
//TCCR1B = TCCR1B & B11111000 | B00000011;    // set timer 1 divisor to    64 for PWM frequency of   490.20 Hz (The DEFAULT)
  TCCR1B = TCCR1B & B11111000 | B00000100;    // set timer 1 divisor to   256 for PWM frequency of   122.55 Hz (recommended for LED use)
//TCCR1B = TCCR1B & B11111000 | B00000101;    // set timer 1 divisor to  1024 for PWM frequency of    30.64 Hz

//---------------------------------------------- Set PWM frequency for D3 & D11 ------------------------------

//TCCR2B = TCCR2B & B11111000 | B00000001;    // set timer 1 divisor to     1 for PWM frequency of 31372.55 Hz
//TCCR2B = TCCR2B & B11111000 | B00000010;    // set timer 1 divisor to     8 for PWM frequency of  3921.16 Hz
//TCCR2B = TCCR2B & B11111000 | B00000011;    // set timer 1 divisor to    32 for PWM frequency of   980.40 Hz
//TCCR2B = TCCR2B & B11111000 | B00000100;    // set timer 1 divisor to    64 for PWM frequency of   490.20 Hz (The DEFAULT)
//TCCR2B = TCCR2B & B11111000 | B00000101;    // set timer 1 divisor to   128 for PWM frequency of   245.10 Hz
  TCCR2B = TCCR2B & B11111000 | B00000110;    // set timer 1 divisor to   256 for PWM frequency of   122.55 Hz (recommended for LED use, keep in mind that tone() won't be available)
//TCCR2B = TCCR2B & B11111000 | B00000111;    // set timer 1 divisor to  1024 for PWM frequency of    30.64 Hz


  // Wait 100 milliseconds. This is necessary to give some time to PCB's circuit
  // to prepare itself (e.g., condensators need some time to discharge)
  delay(100);
  
  // Configure the serial port where we will listen for commands and
  // send debug output
  Serial.begin(SERIAL_BAUD_RATE);

  // Set up the error handler as early as possible
  ErrorHandler::instance().setErrorLED(&builtinLed);

#ifdef VOLTMETER_PIN
  // Attach the voltage meter to the LED strip
  ledStrip.setVoltmeter(&voltmeter);
#endif

#ifdef CLOCK_SKEW_CALIBRATION
  // Show a red color on the LED strip for 3 seconds to warn the user that the
  // controller is in calibration mode
  ledStrip.setColor(255, 0, 0);
  delay(3000);
  ledStrip.off();
  
  // DON'T WRITE ANYTHING INTO THE EEPROM HERE. This would make the calibration harder,
  // because _after_ the calibration was done, we have to overwrite the program in the
  // Flash with another version that is compiled _without_ the calibration code, but
  // plugging in the USB to do the upload would power up the Arduino and start the existing
  // calibration program -- which would in turn erase the result of the previous calibration.
  assumeUncalibratedState(&calibrationData);
#else
  // Initialize the clock skew compensation of the executor from EEPROM
  readCalibrationData(&calibrationData);
#endif

#if USE_PPM_REMOTE_CONTROLLER || USE_PWM_REMOTE_CONTROLLER
  // Attach to the PPM/PWM interrupts if needed
  signalSource.attachInterruptHandler();
#endif

  // Propagate the clock skew compensation factor to the executor
#ifdef DEBUG
  Serial.print(" Using compensation factor: ");
  Serial.println(calibrationData.clockSkewCompensationFactor, 8);
#endif
  executor.setClockSkewCompensationFactor(calibrationData.clockSkewCompensationFactor);
  
  // Load the bytecode into the executor. We have to do it here and not
  // before the +READY prompt because errors might already happen here
  // (e.g., we are trying to load bytecode from the EEPROM but there is
  // no bytecode there) and we don't want error messages to appear
  // before the +READY prompt.
  executor.setBytecodeStore(&bytecodeStore);

  // Attach the signal source to the executor
  executor.setSignalSource(&signalSource);

#ifdef ENABLE_SERIAL_INPUT
  // Inform the serial protocol parser about the executor so the parser
  // can manipulate it. This is not really nice; a better solution would
  // be to let the parser forward the information about the parsed
  // command to a callback function, and we could then provide a callback
  // function here in the main file so the parser does not have to "know"
  // about the executor directly.
  serialProtocolParser.setCommandExecutor(&executor);
#endif

#ifdef MAIN_SWITCH_CHANNEL
  // Set up the main switch edge detector
  mainSwitchEdgeDetector.callbacks.rising = mainSwitchCallback;
  mainSwitchEdgeDetector.callbacks.falling = mainSwitchCallback;
  mainSwitchEdgeDetector.reset();
#endif

#ifdef LANDING_SWITCH_CHANNEL
  // Set up the landing switch edge detector
  landingSwitchEdgeDetector.callbacks.rising = landingSwitchCallback;
  landingSwitchEdgeDetector.callbacks.falling = landingSwitchCallback;
  landingSwitchEdgeDetector.reset();
  
  // Assign the proper landing color
  setupLandingColor();
#endif

#ifdef BYTECODE_RC_CHANNEL
  // Set up the main switch edge detector
  bytecodeRCEdgeDetector.callbacks.rising = bytecodeRCCallback;
  bytecodeRCEdgeDetector.callbacks.falling = bytecodeRCCallback;
  bytecodeRCEdgeDetector.reset();
#endif

#ifdef PYRO_SWITCH_CHANNEL
  // Set up the pyro switch edge detector
  pyroSwitchEdgeDetector.callbacks.rising = pyroSwitchCallback;
  pyroSwitchEdgeDetector.callbacks.falling = pyroSwitchCallback;
  pyroSwitchEdgeDetector.reset();
#endif

#ifdef ENABLE_SERIAL_PORT_STARTUP_SIGNAL
  // Wait for the startup signal on the serial port
  waitForStartupSignal();
#endif

  // Reset the clock of the executor now
  executor.resetClock();
  
  // Print the banner to the serial port to indicate that we are ready.
  // This will be used by any other service listening on the other end of
  // the serial port to know that the boot sequence has completed and
  // we can upload new bytecode (if we start supporting that).
  // Note that we add a leading newline to the banner to make it easier
  // to find when the app sitting on the other side of the port is reading
  // the serial port line by line and there is some junk left in the
  // serial port buffer from an earlier run.
  Serial.println(F("\n+READY"));
}

/**
 * The body of the main loop of the application, executed in an infinite loop.
 */
void loop() {

#ifdef PYRO_SWITCH_CHANNEL
  // Feed the pyro channel signal to the edge detector
  pyroSwitchEdgeDetector.feedAnalogSignal(signalSource.channelValue(PYRO_SWITCH_CHANNEL));
#endif

#ifdef BYTECODE_RC_CHANNEL
  // Feed the bytecode rc channel signal to the edge detector
  bytecodeRCEdgeDetector.feedAnalogSignal(signalSource.channelValue(BYTECODE_RC_CHANNEL));
#endif

#ifdef LANDING_SWITCH_CHANNEL
  // Feed the landing switch channel signal to the edge detector
  landingSwitchEdgeDetector.feedAnalogSignal(signalSource.channelValue(LANDING_SWITCH_CHANNEL));
#endif

#ifdef PYRO_PIN
#ifdef PYRO_PULSE_LENGTH_IN_SECONDS
  // step the pyro executor to limit pulse length
  pyroTrigger.step();
#endif
#endif

#ifdef MAIN_SWITCH_CHANNEL
  // Feed the main switch channel signal to the edge detector
  mainSwitchEdgeDetector.feedAnalogSignal(signalSource.channelValue(MAIN_SWITCH_CHANNEL));
  if (mainSwitchEdgeDetector.value() == 0) {
    // Turn off the LEDs
    turnAllLightsOff();
    return;
  }
#endif

#ifdef MAIN_SWITCH_PIN
  // Check the main switch pin
  if (!mainSwitch.on()) {
    // Turn off the LEDs
    turnAllLightsOff();
    return;
  }
#endif

#ifdef VOLTMETER_PIN
  // Update the voltmeter reading
  voltmeter.measure();
#endif

#ifdef DEBUG
  // Dump some debug information of the signal source
  // signalSource.dumpDebugInformation();
#endif

  // step the executor forward
  executor.step();
}

#ifdef ENABLE_SERIAL_INPUT
/**
 * Handler function that is called between iterations of the main loop if
 * there is data to be read from the serial port.
 */
void serialEvent() {
  while (Serial.available()) {
    serialProtocolParser.feed(Serial.read());
  }
}
#endif

/**
 * \brief Forwards assertion error messages to the serial link.
 */
void __assert(const char *__func, const char *__file, int __lineno, const char *__sexp) {
  Serial.println(__func);
  Serial.println(__file);
  Serial.println(__lineno, DEC);
  Serial.println(__sexp);
  Serial.flush();
  abort();
}
