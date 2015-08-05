#define __ASSERT_USE_STDERR

#include "config.h"
#include "commands.h"
#include "edge_detector.h"
#include "executor.h"
#include "led.h"
#include "led_strip.h"
#include "serial_protocol.h"
#include "signal_decoders.h"
#include "switch.h"


/**
 * The built-in LED of the board.
 */
LED builtinLed;

/**
 * The LED strip attached to the board.
 */
LEDStrip ledStrip(RED_PWM_PIN, GREEN_PWM_PIN, BLUE_PWM_PIN);

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

/**
 * Command executor that is responsible for executing the scheduled bytecode
 * commands.
 */
CommandExecutor executor(&ledStrip);

// Set the following macro to the number of the test sequence that you want to start
// 0 = simple test sequence
// 1 = testing transition types and easing functions
// 2 = testing jump instruction
// 3 = writable bytecode in SRAM with no program loaded by default
// 4 = writable bytecode in EEPROM with whatever program there is in the EEPROM
// 5 = LED strip controlled from remote controller, channels 1, 2 and 3
// 6 = read-only bytecode in PROGMEM
#define BYTECODE_INDEX 4

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
#  include "bytecode_rc.h"
#elif BYTECODE_INDEX == 6
#  include "bytecode_progmem.h"
#else
#  error "Invalid BYTECODE_INDEX value"
#endif

#if USE_PPM_REMOTE_CONTROLLER
PPMSignalSource signalSource(RC_INTERRUPT);
#elif USE_PWM_REMOTE_CONTROLLER
PWMSignalSource signalSource(RC_INTERRUPT);
#else
#  define NUM_FAKE_SIGNAL_PINS 2
static const u8 signalSourcePins[NUM_FAKE_SIGNAL_PINS] = { A0, A5 };
DummySignalSource signalSource(NUM_FAKE_SIGNAL_PINS, signalSourcePins);
#endif

#ifdef START_SIGNAL_CHANNEL
bool seenStartSignal;
EdgeDetector startSignalEdgeDetector;

void startSignalCallback(EdgeDetector* detector, long time, void* data) {
  seenStartSignal = true;
}
#endif

/**
 * Setup function; called once after a reset.
 */
void setup() {
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

  // Attach to the PPM/PWM interrupts if needed
#if USE_PPM_REMOTE_CONTROLLER || USE_PWM_REMOTE_CONTROLLER
  signalSource.attachInterruptHandler();
#endif
  
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

#ifdef START_SIGNAL_CHANNEL
  // Set up the start signal edge detector
  seenStartSignal = false;
  startSignalEdgeDetector.callbacks.rising = startSignalCallback;
  startSignalEdgeDetector.callbacks.falling = startSignalCallback;
  startSignalEdgeDetector.reset();
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
#ifdef START_SIGNAL_CHANNEL
  if (!seenStartSignal) {
    // Feed the edge detector of the start signal if we haven't seen the signal
    // yet. The callback function of the edge detector will set the seenStartSignal
    // flag when an appropriate edge is detected.
    startSignalEdgeDetector.feedAnalogSignal(signalSource.channelValue(START_SIGNAL_CHANNEL));
    return;
  }
#endif

#ifdef MAIN_SWITCH_PIN
  // Check the main switch
  if (!mainSwitch.on()) {
    // Turn off the LEDs
    builtinLed.off();
    ledStrip.off();
    return;
  }
#endif

#ifdef VOLTMETER_PIN
  // Update the voltmeter reading
  voltmeter.measure();
#endif

  // Dump some debug information of the signal source
#ifdef DEBUG
  // signalSource.dumpDebugInformation();
#endif

  // Make a step with the executor
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
