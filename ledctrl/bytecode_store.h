/**
 * \file bytecode_store.h
 * \brief Access control objects for bytecode stored in SRAM or EEPROM.
 */
#ifndef BYTECODE_STORE_H
#define BYTECODE_STORE_H

#include <Arduino.h>
#include <assert.h>
#include <avr/eeprom.h>
#include <avr/pgmspace.h>
#include <stdint.h>
#include "commands.h"
#include "errors.h"
#include "types.h"

/**
 * Typedef for locations in a bytecode store.
 */
typedef int bytecode_location_t;

/**
 * \def BYTECODE_LOCATION_NOWHERE
 * Special value for \c bytecode_location_t that indicates "nowhere".
 */
#define BYTECODE_LOCATION_NOWHERE -1

/**
 * Pure abstract class for bytecode store objects.
 */
class BytecodeStore {
private:
  /**
   * Internal counter that is increased whenever \c suspend() is called and
   * decreased whenever \c resume() is called. The bytestore should only
   * return \c NOP bytes when it is suspended.
   */
  signed short int m_suspendCounter;
  
public:
  /**
   * Constructor.
   */
  BytecodeStore() : m_suspendCounter(0) {}

  /**
   * Destructor.
   */
  virtual ~BytecodeStore() {}
  
  /**
   * \brief Returns the capacity of the store.
   * 
   * The capacity of the store is equal to the length of the longest bytecode
   * that one can write into it. Read-only bytecode stores should report a
   * capacity of zero.
   */
  virtual unsigned int capacity() const = 0;
  
  /**
   * \brief Returns whether the store is empty.
   * 
   * The store is empty if it contains no code to be executed at all. Note that
   * the store is \em not empty if it contains code but the internal pointer is
   * at the end of the store.
   */
  virtual bool empty() const = 0;
  
  /**
   * \brief Returns the next byte from the bytecode store and advances the
   *        internal pointer.
   */
  virtual u8 next() = 0;

  /**
   * \brief Resumes the bytecode store after a previous call to \c suspend().
   *        
   * This function can be invoked multiple times; it must be balanced
   * with an equal number of calls to \c suspend() when used correctly.
   */
  void resume() {
    m_suspendCounter--;
  }
  
  /**
   * \brief Rewinds the bytecode store to the start of the current bytecode.
   */
  virtual void rewind() = 0;  

  /**
   * \brief Moves the internal pointer of the bytecode to the given location.
   * 
   * Bytecode cells are non-negative integers starting from zero. Zero means the
   * point where the execution starts.
   */
  virtual void seek(bytecode_location_t location) = 0;

  /**
   * \brief Temporarily suspend the bytecode store so it will simply return
   *        \c NOP until it is resumed.
   *        
   * This function can be invoked multiple times; it must be balanced
   * with an equal number of calls to \c resume() to restore the bytecode
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
   *        
   * \return  the number of bytes written, i.e. 1 if the write was successful 
   *          and 0 if it failed
   */
  virtual int write(u8 value) = 0;
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

  unsigned int capacity() const {
    return 0;
  }
  
  bool empty() const {
    return m_bytecode == 0;
  }
  
  /**
   * \brief Loads the given bytecode into the store.
   * 
   * Note that the memory area holding the bytecode is \em not copied into
   * the bytecode store; it is the responsibility of the caller to manage the
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
    assert(location >= 0);
    m_pNextCommand = m_bytecode + location;
  }
  
  bytecode_location_t tell() const {
    bytecode_location_t location = m_pNextCommand - m_bytecode;
    return location < 0 ? BYTECODE_LOCATION_NOWHERE : location;
  }

  int write(u8 value) {
    return 0;
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
   * Capacity of the bytecode store.
   */
  int m_capacity;
  
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
  explicit SRAMBytecodeStore(u8* bytecode=0, unsigned int capacity=0) : BytecodeStore() {
    load(bytecode, capacity);
  }

  /**
   * Returns a pointer to the start of the memory block where the bytecode
   * is stored.
   */
  u8* begin() const {
    return m_bytecode;
  }

  unsigned int capacity() const {
    return m_capacity;
  }
  
  bool empty() const {
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
   * \param  capacity  the length of the memory area that will hold the bytecode,
   *                   in bytes. Ignored and assumed to be zero if \c bytecode
   *                   is \c NULL
   */
  void load(u8* bytecode, unsigned int capacity) {
    m_bytecode = bytecode;
    m_capacity = bytecode ? capacity : 0;
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
    assert(location >= 0);
    m_pNextCommand = m_bytecode + location;
  }
  
  bytecode_location_t tell() const {
    bytecode_location_t location = m_pNextCommand - m_bytecode;
    return location < 0 ? BYTECODE_LOCATION_NOWHERE : location;
  }

  int write(u8 value) {
    assert(m_pNextCommand != 0);
    *m_pNextCommand = value;
    m_pNextCommand++;
    return 1;
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
   * Capacity of the bytecode store.
   */
  int m_capacity;
  
  /**
   * Pointer to the byte in EEPROM that contains the next byte to be returned, or
   * -1 if the EEPROM memory segment does not contain valid bytecode.
   */
  int m_nextIndex;

public:
  /**
   * Constructor.
   * 
   * \param  startIndex  Index of the byte in EEPROM where the bytecode starts, including
   *                     the magic byte sequence at the start.
   * \param  capacity    The capacity of the bytecode store
   */
  explicit EEPROMBytecodeStore(int startIndex=0, unsigned int capacity=0)
    : BytecodeStore(), m_startIndex(startIndex), m_capacity(capacity) {
    rewind();
  }

  /**
   * Returns the index of the byte in EEPROM where the bytecode starts.
   * This index will point \em to the magic byte sequence at the start.
   */
  const int begin() const {
    return m_startIndex;
  }

  unsigned int capacity() const {
    return m_capacity;
  }
  
  virtual bool empty() const {
    return m_startIndex < 0 || m_nextIndex < m_startIndex;
  }
  
  u8 next() {
    if (suspended()) {
      return CMD_NOP;
    } else if (m_nextIndex == -1) {
      // No bytecode in EEPROM yet, so pretend we have an infinite
      // stream of CMD_END
      SET_ERROR(Errors::NO_BYTECODE_IN_EEPROM);
      return CMD_END;
    } else {
      return nextByte();
    }
  }

  void rewind() {
    m_nextIndex = m_startIndex;
    if (!validateMagicBytes()) {
      m_nextIndex = -1;
    } else {
      CLEAR_ERROR();
    }
  }

  void seek(bytecode_location_t location) {
    assert(location >= 0);
    m_nextIndex = m_startIndex + location + 2;
  }
  
  bytecode_location_t tell() const {
    return m_nextIndex >= m_startIndex+2 ? (m_nextIndex-m_startIndex-2) : BYTECODE_LOCATION_NOWHERE;
  }

  int write(u8 value) {
    if (m_nextIndex == -1) {
      // We had no EEPROM bytecode but we have started writing something
      // so let's add the magic marker first
      m_nextIndex = m_startIndex;
      eeprom_update_byte((unsigned char*)m_nextIndex, 0xCA);
      m_nextIndex++;
      eeprom_update_byte((unsigned char*)m_nextIndex, 0xFE);
      rewind();    // to clear the error LED
    }

    assert(m_nextIndex >= 0);
    eeprom_update_byte((unsigned char*)m_nextIndex, value);
    m_nextIndex++;
    
    return 1;
  }

private:
  /**
   * \brief Returns the next byte from the bytecode store (even if it is suspended)
   *        and advances the internal pointer.
   */
  u8 nextByte() {
    u8 result;
    
    assert(m_nextIndex >= 0);
    result = eeprom_read_byte((unsigned char*)m_nextIndex);
    m_nextIndex++;

    return result;
  }
  
  /**
   * \brief Checks whether the next four bytes are the magic bytes.
   */
  bool validateMagicBytes() {
    // We cannot use next() here because it wouldn't work if the bytecode
    // store is suspended (as we always return CMD_NOP)
    if (nextByte() != 0xCA)
      return false;
    return nextByte() == 0xFE;
  }
};

/**
 * Provides access to bytecode stored in a constant in PROGMEM.
 */
class PROGMEMBytecodeStore : public BytecodeStore {
private:
  /** 
   * Pointer to the start of the memory block in PROGMEM where the bytecode
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
   * \param  bytecode  pointer to the start of the memory block in PROGMEM where
   *                   the bytecode is stored.
   */
  explicit PROGMEMBytecodeStore(const u8* bytecode=0) : BytecodeStore() {
    load(bytecode);
  }

  /**
   * Returns a pointer to the start of the memory block where the bytecode
   * is stored.
   */
  const u8* begin() const {
    return m_bytecode;
  }

  unsigned int capacity() const {
    return 0;
  }
  
  bool empty() const {
    return m_bytecode == 0;
  }
  
  /**
   * \brief Loads the given bytecode into the store.
   * 
   * Note that the memory area holding the bytecode is \em not copied into
   * the bytecode store; it is the responsibility of the caller to manage the
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
    u8 result;
    
    if (suspended()) {
      return CMD_NOP;
    } else {
      assert(m_pNextCommand != 0);
      result = pgm_read_byte_near(m_pNextCommand);
      m_pNextCommand++;
      return result;
    }
  }

  void rewind() {
    m_pNextCommand = m_bytecode;
  }

  void seek(bytecode_location_t location) {
    assert(location >= 0);
    m_pNextCommand = m_bytecode + location;
  }
  
  bytecode_location_t tell() const {
    bytecode_location_t location = m_pNextCommand - m_bytecode;
    return location < 0 ? BYTECODE_LOCATION_NOWHERE : location;
  }

  int write(u8 value) {
    return 0;
  }
};

#endif
