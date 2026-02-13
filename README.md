# Allen MOS II Organ Keyboard Matrix to USB MIDI Adapter
This is a Teensy 4.1 sketch for connecting an Allen MOS II Organ's keyboards to a computer over USB MIDI.  It's designed to read the 11x6 keyboard matrix for each keyboard, and also the pedal board, and export them as a MIDI device suitable to connect to any virtual pipe organ.

## Operation
The keyboards all share a common set of read wires.  Each keyboard uses 11 read wires and the pedal board uses at least 8.  Each keyboard has its own set of six signal wires.  To read the keyboards a microcontroller (the organ itself or a Teensy) raises each signal wire in turn to a high state and then reads the key pressed signals from the read wires.  This is done in a sequential cycle, many times per second. In this way a relatively few wires can read the entire keyboard quickly, and multiple keys can be pressed at once.

Since the Teensy operates with isolated voltage potential, it's possible for the Teensy and also the built-in Allen organ computer to scan the keyboards at the same time. This should allow a MIDI interface to connect to an unaltered organ.

The sketch turns keyboard presses and releases into MIDI NOTE ON and NOTE OFF events, with a velocity of 127.  The first keyboard events are on channel 1, the second on channel 2, and the pedal board on channel 3.  If you want to change it, you can set it in the sketch.

## Black common wires
The 11 black read wires connect to Teensy pins 20-30.  Looking at the keyboard from the top, the left-most key is connected to its own black wire to pin 20.  Every group of 6 keys after that connects via diodes to a common black wire and those go in order to pins 21 and higher.

Looking at the 44-pin MOS Matrix board connector, the connections are:

| Teensy | MOS Matrix pin |
| ------ | -------------- |
| 20     | 11             |
| 21     | 13             |
| 22     | 9              |
| 23     | 5              |
| 24     | 7              |
| 25     | 3              |
| 26     | 1              |
| 27     | 8              |
| 28     | 10             |
| 29     | 12             |
| 30     | 14             |

## Keyboard 1 Read Wires
The top keyboard matrix is read via six wires, each wire connected to 11 keys.  These are connected left to right to Teensy to pins 2,3,4,5,6,7.  These wires can also be accessed via the 44-pin keyboard matrix edge connector on 22,23,26,25,24, and 21. On our organ these wires are white.

| Teensy | MOS Matrix pin |
| ------ | -------------- |
| 2      | 22             |
| 3      | 23             |
| 4      | 26             |
| 5      | 25             |
| 6      | 24             |
| 7      | 21             |

## Keyboard 2 Read Wires
The second keyboard matrix is also read through six wires that connect to Teensy
's pins 8,9,10,11,12,and 13.  On our organ these are orange wires and are connected to the edge connector to pins 28, 29, 32, 31, 30, and 27.

| Teensy | MOS Matrix pin |
| ------ | -------------- |
| 8      | 28             |
| 9      | 29             |
| 10     | 32             |
| 11     | 31             |
| 12     | 30             |
| 13     | 27             |

## Pedal Board Read Wires
The pedal board is read through six wires that connect to Teensy pins 14, 15, 16, 17, 18, and 19.  These wires are blue on our organ and connect to pins 40, 41, 44, 43, 42, and 39 on the 44 pin matrix edge connector.

| Teensy | MOS Matrix pin |
| ------ | -------------- |
| 14     | 40             |
| 15     | 41             |
| 16     | 44             |
| 17     | 43             |
| 18     | 42             |
| 19     | 39             |


