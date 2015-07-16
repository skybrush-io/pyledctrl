/**
 * \file bytecode_store.h
 * \brief Access control objects for bytecode stored in SRAM or EEPROM.
 */
#ifndef BYTECODE_STORE_H
#define BYTECODE_STORE_H

#include <Arduino.h>
#include <assert.h>
#include <avr/eeprom.h>
#include <stdint.h>
#include "commands.h"
#include "errors.h"
#include "types.h"

/**
 * Typedef for locations in a bytecode store.
 */
typedef uintptr_t bytecode_location_t;

/**
 * \def BYTECODE_LOCATION_NOWHERE
 * Special value for \c bytecode_location_t that indicates "nowhere".
 */
#define BYTECODE_LOCATION_NOWHERE 0

/**
 * Pure abstract class for bytecode store objects.
 */
class BytecodeStore {
private:
  /**
   * Internal counter that is increased whenever \c suspend() is called and
   * decreased whenever \c release() is called. The bytestore should only
   * return \c NOP bytes when it is suspended.
   */
  signed short int m_suspendCounter;
  
public:
  /**
   * Constructor.
   */
  BytecodeStore() : m_suspendCounter(0) {}
  
  /**
   * \brief Returns whether the store is empty.
   * 
   * The store is empty if it contains no code to be executed at all. Note that
   * the store is \em not empty if it contains code but the internal pointer is
   * at the end of the store.
   */
  virtual bool empty() = 0;
  
  /**
   * \brief Returns the next byte from the bytecode store and advances the
   *        internal pointer.
   */
  virtual u8 next() = 0;

  /**
   * \brief Releases the bytecode store after a previous call to \c suspend().
   *        
   * This function can be invoked multiple times; it must be balanced
   * with an equal number of calls to \c suspend() when used correctly.
   */
  void release() {
    m_suspendCounter--;
  }
  
  /**
   * \brief Rewinds the bytecode store to the start of the current bytecode.
   */
  virtual void rewind() = 0;  

  /**
   * \brief Moves the internal pointer of the bytecode to the given location.
   */
  virtual void seek(bytecode_location_t location) = 0;

  /**
   * \brief Temporarily suspend the bytecode store so it will simply return
   *        \c NOP until it is released.
   *        
   * This function can be invoked multiple times; it must be balanced
   * with an equal number of calls to \c release() to restore the bytecode
   * store to its original (unsuspended) state.
   */
  void suspend() {
    m_suspendCounter++;
  }

  /**
   * \brief Returns whether the bytecode store is currently suspended.
   * \return \c true if the bytecode store is currently suspended, \c false
   *         otherwise.
   */
  bool suspended() const {
    return m_suspendCounter > 0;
  }
  
  /**
   * \brief Returns the current location of the internal pointer of the
   *        bytecode.
   *        
   * The value returned by this function should be considered opaque; it
   * should not be altered by third-party code. The only valid use-case
   * for this value is to pass it on to \c seek() later.
   * 
   * \return  the current location of the internal pointer of the bytecode,
   *          or \c BYTECODE_LOCATION_NOWHERE if this bytecode store does
   *          not support seeking
   */
  virtual bytecode_location_t tell() const = 0;

  /**
   * \brief Writes the given byte into the current location in the bytecode,
   *        and advances the internal pointer.
   */
  virtual void write(u8 value) = 0;
};

/**
 * Provides access to bytecode stored in a constant in SRAM.
 */
class ConstantSRAMBytecodeStore : public BytecodeStore {
private:
  /** 
   * Pointer to the start of the memory block in SRAM where the bytecode
   * is stored.
   */
  const u8* m_bytecode;
  
  /**
   * Pointer to the current location within the bytecode.
   */
  const u8* m_pNextCommand;

public:
  /**
   * Constructor.
   * 
   * \param  bytecode  pointer to the start of the memory block in SRAM where
   *                   the bytecode is stored.
   */
  explicit ConstantSRAMBytecodeStore(const u8* bytecode=0) : BytecodeStore() {
    load(bytecode);
  }

  /**
   * Returns a pointer to the start of the memory block where the bytecode
   * is stored.
   */
  const u8* begin() const {
    return m_bytecode;
  }

  bool empty() {
    return m_bytecode == 0;
  }
  
  /**
   * \brief Loads the given bytecode into the store.
   * 
   * Note that the memory area holding the bytecode is \em not copied into
   * the executor; it is the responsibility of the caller to manage the
   * memory occupied by the bytecode and free it when it is not needed
   * any more.
   * 
   * \param  bytecode  the bytecode to be loaded. \c NULL is supported; passing
   *                   \c NULL here simply unloads the previous bytecode.
   */
  void load(const u8* bytecode) {
    m_bytecode = bytecode;
    rewind();
  }

  u8 next() {
    if (suspended()) {
      return CMD_NOP;
    } else {
      assert(m_pNextCommand != 0);
      return *(m_pNextCommand++);
    }
  }

  void rewind() {
    m_pNextCommand = m_bytecode;
  }

  void seek(bytecode_location_t location) {
    m_pNextCommand = (const u8*)location;
  }
  
  bytecode_location_t tell() const {
    return (bytecode_location_t)m_pNextCommand;
  }

  void write(u8 value) {
    SET_ERROR(Errors::OPERATION_NOT_SUPPORTED);
  }
};

/**
 * Provides access to bytecode stored in a constant in SRAM.
 */
class SRAMBytecodeStore : public BytecodeStore {
private:
  /** 
   * Pointer to the start of the memory block in SRAM where the bytecode
   * is stored.
   */
  u8* m_bytecode;
  
  /**
   * Pointer to the current location within the bytecode.
   */
  u8* m_pNextCommand;

public:
  /**
   * Constructor.
   * 
   * \param  bytecode  pointer to the start of the memory block in SRAM where
   *                   the bytecode is stored.
   */
  explicit SRAMBytecodeStore(u8* bytecode=0) : BytecodeStore() {
    load(bytecode);
  }

  /**
   * Returns a pointer to the start of the memory block where the bytecode
   * is stored.
   */
  u8* begin() const {
    return m_bytecode;
  }

  bool empty() {
    return m_bytecode == 0;
  }
  
  /**
   * \brief Loads the given bytecode into the store.
   * 
   * Note that the memory area holding the bytecode is \em not copied into
   * the executor; it is the responsibility of the caller to manage the
   * memory occupied by the bytecode and free it when it is not needed
   * any more.
   * 
   * \param  bytecode  the bytecode to be loaded. \c NULL is supported; passing
   *                   \c NULL here simply unloads the previous bytecode.
   */
  void load(u8* bytecode) {
    m_bytecode = bytecode;
    rewind();
  }

  u8 next() {
    if (suspended()) {
      return CMD_NOP;
    } else {
      assert(m_pNextCommand != 0);
      return *(m_pNextCommand++);
    }
  }

  void rewind() {
    m_pNextCommand = m_bytecode;
  }

  void seek(bytecode_location_t location) {
    m_pNextCommand = (u8*)location;
  }
  
  bytecode_location_t tell() const {
    return (bytecode_location_t)m_pNextCommand;
  }

  void write(u8 value) {
    assert(m_pNextCommand != 0);
    *m_pNextCommand = value;
  }
};

/**
 * Provides access to bytecode stored in the EEPROM.
 * 
 * The memory segment that hosts the bytecode must start with the magic bytes
 * \c "CA FE". The actual bytecode follows these two bytes.
 */
class EEPROMBytecodeStore : public BytecodeStore {
private:
  /** 
   * Pointer to the byte in EEPROM where the bytecode starts.
   */
  const int m_startIndex;
  
  /**
   * Pointer to the byte in EEPROM that contains the next byte to be returned, or
   * -1 if the EEPROM memory segment does not contain valid bytecode.
   */
  int m_nextIndex;

public:
  /**
   * Constructor.
   */
  explicit EEPROMBytecodeStore() : BytecodeStore(), m_startIndex(0) {
    rewind();
  }

  /**
   * Returns the index of the byte in EEPROM where the bytecode starts.
   * This index will point \em to the magic byte sequence at the start.
   */
  const int begin() const {
    return m_startIndex;
  }

  virtual bool empty() {
    return m_startIndex < 0 || m_nextIndex < m_startIndex;
  }
  
  u8 next() {
    if (suspended()) {
      return CMD_NOP;
    } else {
      assert(m_nextIndex >= 0);
      return eeprom_read_byte((unsigned char*)m_nextIndex);
    }
  }

  void rewind() {
    m_nextIndex = m_startIndex;
    if (!validateMagicBytes()) {
      m_nextIndex = -1;
    }
  }

  void seek(bytecode_location_t location) {
    m_nextIndex = (int)(location-1);
  }
  
  bytecode_location_t tell() const {
    return m_nextIndex >= 0 ? (bytecode_location_t)(m_nextIndex+1) : BYTECODE_LOCATION_NOWHERE;
  }

private:
  /**
   * \brief Checks whether the next four bytes are the magic bytes.
   */
  bool validateMagicBytes() {
    if (next() != 0xCA)
      return false;
    return next() == 0xFE;
  }
};

#endif
