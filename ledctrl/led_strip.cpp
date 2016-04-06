#include "led_strip.h"

void LEDStrip::initialize() {
  // Set the pins to OUTPUT mode
  pinMode(m_redPin, OUTPUT);
  pinMode(m_greenPin, OUTPUT);
  pinMode(m_bluePin, OUTPUT);
  
  // Define voltage compensation ranges for the diodes
  calculateVoltageCompensationRanges();

  // Turn off the LEDs
  off();
}

void LEDStrip::calculateVoltageCompensationRanges() {
	m_pwmIntervals.red_duty_range.min = normalizeVoltage(RED_LED_MIN_VOLTAGE);
	m_pwmIntervals.red_duty_range.max = normalizeVoltage(RED_LED_MAX_VOLTAGE);
	m_pwmIntervals.green_duty_range.min = normalizeVoltage(GREEN_LED_MIN_VOLTAGE);
	m_pwmIntervals.green_duty_range.max = normalizeVoltage(GREEN_LED_MAX_VOLTAGE);
	m_pwmIntervals.blue_duty_range.min = normalizeVoltage(BLUE_LED_MIN_VOLTAGE);
	m_pwmIntervals.blue_duty_range.max = normalizeVoltage(BLUE_LED_MAX_VOLTAGE);
}
	
byte LEDStrip::normalizeVoltage(float voltage) const {
	return static_cast<byte>(255 * voltage / BOARD_MAX_INPUT_VOLTAGE);
}
