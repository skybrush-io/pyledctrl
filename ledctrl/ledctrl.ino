#define __ASSERT_USE_STDERR

#include "config.h"
//#include "voltmeter.h"
#include "commands.h"
#include "executor.h"
#include "led.h"
#include "led_strip.h"
#include "switch.h"
#include "SignalDecoders.h"



LED builtinLed;
LEDStrip ledStrip(RED_PWM_PIN, GREEN_PWM_PIN, BLUE_PWM_PIN);
Switch mainSwitch(MAIN_SWITCH_PIN);
VoltMeter voltmeter;

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
  // Configure the serial port where we will listen for commands and
  // send debug output
	wait(100);
	ledStrip.initIntervals();

  Serial.begin(SERIAL_BAUD_RATE);
  
	#if PPM_INTERRUPT
	attachInterrupt(ITNUM, ppmIT, RISING);
	#elif PWM_INTERRUPT
	attachInterrupt(ITNUM, pwmIT, CHANGE);
	#endif
  // Load the bytecode into the executor
  executor.setBytecodeStore(&bytecodeStore);
  // Print the banner to the serial port to indicate that we are ready
  Serial.println(F("+OK"));
  wait(100);
}

void loop() {
	#if MAINSWITCH
	// Check the main switch
	if (false && !mainSwitch.on()) {
		// Turn off the LEDs
		builtinLed.off();
		ledStrip.off();
		return;
	}
	#endif
	ledStrip.modification();
	Serial.println(ledStrip.voltagecompensator);
	//wait(250);
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
