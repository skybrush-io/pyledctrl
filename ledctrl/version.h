/**
 * \file version.h
 * \brief Version information for \c ledctrl
 */

#ifndef VERSION_H
#define VERSION_H

/**
 * \def LEDCTRL_VERSION_MAJOR
 * Major version number of \c ledctrl
 */
#define LEDCTRL_VERSION_MAJOR 1

/**
 * \def LEDCTRL_VERSION_MINOR
 * Minor version number of \c ledctrl
 */
#define LEDCTRL_VERSION_MINOR 0

/**
 * \def LEDCTRL_VERSION_PATCH
 * Patch level of \c ledctrl
 */
#define LEDCTRL_VERSION_PATCH 0

/**
 * \def LEDCTRL_VERSION
 * Unified version number of \c ledctrl
 */
#define LEDCTRL_VERSION (LEDCTRL_VERSION_MAJOR * 10000 + LEDCTRL_VERSION_MINOR * 100 + LEDCTRL_VERSION_PATCH)

#endif
