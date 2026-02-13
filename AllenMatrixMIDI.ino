/*
 * 18x11 Keyboard Matrix Scanner for Teensy 4.1
 * 
 * Scans an 18x11 keyboard matrix using shift-register-style scanning:
 * - 18 output pins (column drivers)
 * - 11 input pins (row sensors)
 * 
 * Debouncing uses Bounce2's Debouncer class to track stable state over time.
 * USB MIDI output using Teensy's built-in usbMIDI object.
 */

#include <Bounce2.h>

#define USE_MIDI

// Configuration
const int COLUMN_COUNT = 18;
const int ROW_COUNT = 11;
const int STABLE_TIME_MS = 20;  // Time readings must be stable before reporting (2x scan interval)

const int MIDI_BASE_NOTE = 36;

const int keyboard1_channel = 1;
const int keyboard2_channel = 2;
const int pedalboard_channel = 3;

// Lookup table: column, row -> MIDI note number
const int midiNoteMap[COLUMN_COUNT][ROW_COUNT] = {
  {36, 37, 43, 49, 55, 61, 67, 73, 79, 85, 91},
  {37, 38, 44, 50, 56, 62, 68, 74, 80, 86, 92},
  {38, 39, 45, 51, 57, 63, 69, 75, 81, 87, 93},
  {39, 40, 46, 52, 58, 64, 70, 76, 82, 88, 94},
  {40, 41, 47, 53, 59, 65, 71, 77, 83, 89, 95},
  {41, 42, 48, 54, 60, 66, 72, 78, 84, 90, 96},
  {36, 37, 43, 49, 55, 61, 67, 73, 79, 85, 91},
  {37, 38, 44, 50, 56, 62, 68, 74, 80, 86, 92},
  {38, 39, 45, 51, 57, 63, 69, 75, 81, 87, 93},
  {39, 40, 46, 52, 58, 64, 70, 76, 82, 88, 94},
  {40, 41, 47, 53, 59, 65, 71, 77, 83, 89, 95},
  {41, 42, 48, 54, 60, 66, 72, 78, 84, 90, 96},
  {36, 37, 43, 49, 55, 61, 67, 73, 79, 85, 91},
  {37, 38, 44, 50, 56, 62, 68, 74, 80, 86, 92},
  {38, 39, 45, 51, 57, 63, 69, 75, 81, 87, 93},
  {39, 40, 46, 52, 58, 64, 70, 76, 82, 88, 94},
  {40, 41, 47, 53, 59, 65, 71, 77, 83, 89, 95},
  {41, 42, 48, 54, 60, 66, 72, 78, 84, 90, 96}
};

// Pin assignments - Teensy 4.1 pins
// Using pins 2-19 for outputs (leaving serial port 1 pins 0,1 available)
// Rows use internal pull-downs, input goes HIGH when key pressed
// Adjust these as needed for your hardware
const uint8_t OUTPUT_PINS[COLUMN_COUNT] = {
  2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19
};

const uint8_t INPUT_PINS[ROW_COUNT] = {
  20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30
};

class MatrixDebouncer : public Debouncer {
public:
  bool update(bool newState) {
    currentState = newState;
    return Debouncer::update();
  }
protected:
  bool currentState;
  virtual bool readCurrentState() override {
    return currentState;
  }
};
MatrixDebouncer debouncers[COLUMN_COUNT][ROW_COUNT];

// Tracking variables
unsigned long lastScanTime = 0;

void setup() {
  Serial.begin(9600);
  
  // Initialize output pins (all low initially)
    for (int col = 0; col < COLUMN_COUNT; col++) {
      pinMode(OUTPUT_PINS[col], OUTPUT);
      digitalWrite(OUTPUT_PINS[col], LOW);
      for (int row = 0; row < ROW_COUNT; row++) {
        debouncers[col][row].interval(STABLE_TIME_MS);
      }
    }
  
  // Initialize input pins with internal pull-downs enabled
  // Rows are normally LOW, go HIGH when key pressed
  for (int row = 0; row < ROW_COUNT; row++) {
    pinMode(INPUT_PINS[row], INPUT_PULLDOWN);
  }
  
  Serial.println("Keyboard Matrix Scanner Ready");
#if !defined(USE_MIDI)
  Serial.print("Matrix size: ");
  Serial.print(COLUMN_COUNT);
  Serial.print("x");
  Serial.print(ROW_COUNT);
  Serial.println(" (columns x rows)");
#endif
}

void loop() {
  scanMatrix();
#if defined(USE_MIDI)
  while (usbMIDI.read()) {}
#endif
}

void scanMatrix() {
  for (int col = 0; col < COLUMN_COUNT; col++) {
    digitalWrite(OUTPUT_PINS[col], HIGH);
    delayMicroseconds(10);
    
    for (int row = 0; row < ROW_COUNT; row++) {
      if (debouncers[col][row].update(digitalRead(INPUT_PINS[row]) == HIGH)) {
        int midiNote = midiNoteMap[col][row];
        if (midiNote > 0) {
          int channel;
          if (col >= 0 && col <= 5) {
            channel = keyboard1_channel;
          } else if (col >= 6 && col <= 11) {
            channel = keyboard2_channel;
          } else if (col >= 12 && col <= 17) {
            channel = pedalboard_channel;
          }
          
        if (debouncers[col][row].read()) {
#if defined(USE_MIDI)
          usbMIDI.sendNoteOn(midiNote, 127, channel);
#else
          Serial.print("Note ON: ");
          Serial.print(midiNote);
          Serial.print(" Channel: ");
          Serial.println(channel);
#endif
        } else {
#if defined(USE_MIDI)
          usbMIDI.sendNoteOff(midiNote, 0, channel);
#else
          Serial.print("Note OFF: ");
          Serial.print(midiNote);
          Serial.print(" Channel: ");
          Serial.println(channel);
#endif
        }
        }
      }
    }
    
    digitalWrite(OUTPUT_PINS[col], LOW);
  }
}

bool isKeyPressed(int col, int row) {
  if (col < 0 || col >= COLUMN_COUNT || row < 0 || row >= ROW_COUNT) {
    return false;
  }
  return debouncers[col][row].read();
}
