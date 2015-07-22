#define NUMBEROFEDGES 9
/*
* \def NUMBEROFEDGES
* define how many edges are in  an PPM signal-period (8 channel: 8 rising edge and 1 rising edge in the next cycle,
* which is ndicate the next period and end of current one.
*/

#define PACKETSIZE 22000

/*
* \def PACKETSIZE
* define the comonly used PPM period  (represented in microseconds)
*/

/*
* if we use manual controller, we can assing here PPM channels and colours
*/
#define PPMCHANNEL_R 1
#define PPMCHANNEL_G 2
#define PPMCHANNEL_B 3

/*
* define how many sample will bi used by calculating the aaccurate signals
*/
#define ACCURATE_CYC 10

#include "config.h"

#if PPM_INTERRUPT
/**
* PPM decoder header
*/

/*
* Struct for timestamps in PPM signal decoding interrupt
*/
typedef struct
{
	volatile long current;
	volatile long last;
	volatile long period;
	volatile long Periods[NUMBEROFEDGES];
	volatile long fullperiod;
	volatile long fullperiod_begin;
	volatile long fullperiod_lastbegin;
} PPMtime;


/*
* Values for readed timestamps
*/
volatile int CurrentChannel = 0;
int ReadedChannel;
long time_readed;
long time_last = 125;


void ppmIT();
volatile void PPMsignalToSerial();
PPMtime ppmtime;


long verify[ACCURATE_CYC];
long AccurateValue = 0;
long time;

/*
* INTERRUPT FUNCTION
* Catch and calculate elapsed time between two rising edges, and drop bad ones
*
*/
void ppmIT()
{

	ppmtime.current = micros();
	CurrentChannel++;
	ppmtime.period = ppmtime.current - ppmtime.last;
	if (CurrentChannel >= NUMBEROFEDGES | ppmtime.period >= PACKETSIZE / 3)
	{
		CurrentChannel = -1;

		ppmtime.fullperiod_begin = ppmtime.current;
		ppmtime.fullperiod = ppmtime.fullperiod_begin - ppmtime.fullperiod_lastbegin;
		ppmtime.fullperiod_lastbegin = ppmtime.current;
	}
	else
	{
		ppmtime.Periods[CurrentChannel] = ppmtime.period;
	}
	ppmtime.last = ppmtime.current;
}


/* function for senging signal values to serial port*/
volatile void PPMsignalToSerial()
{
	for (int i = 0; i <= NUMBEROFEDGES - 1; i++)
	{
		Serial.print(" ch: ");
		Serial.print(i);
		Serial.print(" : ");
		Serial.print(ppmtime.Periods[i]);
	}
	Serial.println();
	Serial.println(ppmtime.fullperiod);

}


/**
* give an accurate PPM signal per channel
* catch some sample and drop which is probaly not correct and calculate average from remainders
* This function ask for some time, therefore use with watchfully
*/
volatile long accuratePPMsignals(byte ch)
{
	verify[0] = ppmtime.Periods[ch];
	byte i = 1;
	while (i < ACCURATE_CYC)
	{
		verify[i] = ppmtime.Periods[ch];
		if (abs(verify[i] - verify[i - 1]) < 100)
		{
			AccurateValue += verify[i];
		}
		i++;
		//delay(2);
	}
	AccurateValue /= ACCURATE_CYC;
	return AccurateValue;
}


/**
* Function for control the LED strip with RC controller (i.e. with PPM signals)
*
*/
volatile byte LightController(byte ch)
{
	time = accuratePPMsignals(ch); //precision controlling
	//time = ppmtime.Periods[ch]; //fastest, but without precision
	if (time > 1900) time = 1900;
	if (time < 1100) time = 1100;
	time = (time - 1100) * 0.315; //254/800
	byte x = static_cast<byte>(round(time / 10) * 10);
	return x;
}

#endif
#if PWM_INTERRUPT

/*
* PWM decoder header
*/

typedef struct
{
	volatile long current;
	volatile long last;
	volatile long period;
	volatile long period_begin;
	volatile long high;
	volatile long low;
} PWMtime;

PWMtime pwmtime;

/*
* Functions of PWM signal's interrupt
*/

void pwmIT()
{
	pwmtime.current = micros();
	if (bitRead(PIND, ITPIN) == HIGH)
	{
		pwmtime.period = pwmtime.current - pwmtime.period_begin;
		pwmtime.period_begin = pwmtime.current;

		pwmtime.high = pwmtime.current - pwmtime.last;
	}
	else
	{
		pwmtime.low = pwmtime.current - pwmtime.last;
	}
	pwmtime.last = pwmtime.current;
}

/* function for senging signal values to serial port*/
volatile void PWMsignalToSerial()
{
	Serial.println();
	Serial.print("high: ");
	Serial.print(pwmtime.high);
	Serial.print("  low: ");
	Serial.print(pwmtime.low);
	if (abs(pwmtime.period - pwmtime.high - pwmtime.low)<50)
		Serial.print("  [ok] ");
	else
		Serial.print("  [not ok]");
}

#endif