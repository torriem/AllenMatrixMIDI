#include "usb_names.h"

#define MIDI_NAME {'A','l','l','e','n',' ','O','r','g','a','n',' ','M','I','D','I'}
#define MIDI_NAME_LEN 16

struct usb_string_descriptor_struct usb_string_product_name = {
  2 + MIDI_NAME_LEN * 2,
  3,
  MIDI_NAME
};
