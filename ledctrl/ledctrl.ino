#define __ASSERT_USE_STDERR

#include "config.h"
#include "commands.h"
#include "executor.h"
#include "led.h"
#include "led_strip.h"
#include "switch.h"
#include "SignalDecoders.h"



LED builtinLed;
LEDStrip ledStrip(RED_PWM_PIN, GREEN_PWM_PIN, BLUE_PWM_PIN);
Switch mainSwitch(MAIN_SWITCH_PIN);

#ifdef HAS_VOLTMETER
VoltMeter voltmeter(VOLTMETER_PIN, LIGHT_COEFF);
#endif

CommandExecutor executor(&ledStrip, &builtinLed);

// Set the following macro to the number of the test sequence that you want to start
// 0 = simple test sequence
// 1 = testing transition types and easing functions
#define BYTECODE_INDEX 2

static const u8 bytecode[] = {
#if BYTECODE_INDEX == 0
#  include "bytecode_first_test.h"
#elif BYTECODE_INDEX == 1
#  include "bytecode_transition_test.h"
#elif BYTECODE_INDEX == 2
#include "bytecode_3_test.h"
#endif
};

SRAMBytecodeStore bytecodeStore(bytecode);

void setup() {
  // Wait 100 milliseconds
  // TODO: Arpi, why is this necessary?
	wait(100);

#ifdef HAS_VOLTMETER
  // Attach the voltage meter to the LED strip
  ledStrip.setVoltmeter(&voltmeter);
#endif

  // Configure the serial port where we will listen for commands and
  // send debug output
  Serial.begin(SERIAL_BAUD_RATE);

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
void serialEvent() {

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
