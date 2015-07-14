#define __ASSERT_USE_STDERR

#include "config.h"
#include "commands.h"
#include "executor.h"
#include "led.h"
#include "led_strip.h"
#include "serial_protocol.h"
#include "switch.h"
#include "SignalDecoders.h"


/**
 * The built-in LED of the board.
 */
LED builtinLed;

/**
 * The LED strip attached to the board.
 */
LEDStrip ledStrip(RED_PWM_PIN, GREEN_PWM_PIN, BLUE_PWM_PIN);

#ifdef HAS_MAIN_SWITCH
/**
 * An optional main switch that can be used to turn off the LED strip and
 * suspend execution.
 */
Switch mainSwitch(MAIN_SWITCH_PIN);
#endif

#ifdef HAS_VOLTMETER
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
#define BYTECODE_INDEX 1

static const u8 bytecode[] = {
#if BYTECODE_INDEX == 0
#  include "bytecode_first_test.h"
#elif BYTECODE_INDEX == 1
#  include "bytecode_transition_test.h"
#elif BYTECODE_INDEX == 2
#include "bytecode_3_test.h"
#endif
};

/**
 * The bytecode store that the command executor will use to read the bytecode
 * from SRAM or EEPROM.
 */
SRAMBytecodeStore bytecodeStore(bytecode);

/**
 * Setup function; called once after a reset.
 */
void setup() {
  // Wait 100 milliseconds
  // TODO: Arpi, why is this necessary?
	wait(100);

  // Configure the serial port where we will listen for commands and
  // send debug output
  Serial.begin(SERIAL_BAUD_RATE);

  // Set up the error handler as early as possible
  ErrorHandler::instance().setErrorLED(&builtinLed);
  
#ifdef HAS_VOLTMETER
  // Attach the voltage meter to the LED strip
  ledStrip.setVoltmeter(&voltmeter);
#endif

  // Attach to the PPM/PWM interrupts if needed
	#if PPM_INTERRUPT
	attachInterrupt(ITNUM, ppmIT, RISING);
	#elif PWM_INTERRUPT
	attachInterrupt(ITNUM, pwmIT, CHANGE);
	#endif
  
  // Load the bytecode into the executor
  executor.setBytecodeStore(&bytecodeStore);

  // Wait 100 milliseconds
  // TODO: Arpi, why is this necessary?
  wait(100);
  
  // Print the banner to the serial port to indicate that we are ready.
  // This will be used by any other service listening on the other end of
  // the serial port to know that the boot sequence has completed and
  // we can upload new bytecode (if we start supporting that)
  Serial.println(F("+OK"));
}

/**
 * The body of the main loop of the application, executed in an infinite loop.
 */
void loop() {
#ifdef HAS_MAIN_SWITCH
	// Check the main switch
	if (!mainSwitch.on()) {
		// Turn off the LEDs
		builtinLed.off();
		ledStrip.off();
		return;
	}
#endif

#ifdef HAS_VOLTMETER
  // Update the voltmeter reading
  voltmeter.measure();
#endif

#if PPM_INTERRUPT
	PPMsignalToSerial();
#elif PWM_INTERRUPT
	//PWMsignalToSerial();
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


void wait(unsigned long ms)
{
	uint16_t start = (uint16_t)micros();
	while (ms > 0)
	{
		if (((uint16_t)micros() - start) >= 1000)
		{
			ms--;
			start += 1000;
		}
	}
}

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
