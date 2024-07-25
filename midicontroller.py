from enum import Enum

import pygame

import time
import rtmidi

from dataclasses import dataclass

# utils
def clamp(val, min, max):
    if val > max: return max
    if val < min: return min
    return val

# window
def midi_to_note_name(midi_key):
    note_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
    note = note_names[midi_key % 12]
    octave = midi_key // 12 - 1
    return f"{note}{octave}"

def note_set_string(notes):
    return ' '.join((midi_to_note_name(note) for note in notes))

def render_text(text, screen, font, center, color):
    text = font.render(text, True, color)
    text_rect = text.get_rect(center=center)
    screen.blit(text, text_rect)

def update_screen(screen, display_data):
    screen.fill((255, 255, 255))

    big_font = pygame.font.Font(None, 22)
    small_font = pygame.font.Font(None, 14)

    # notes
    render_text(
        text=note_set_string(display_data.notes),
        screen=screen,
        font=big_font,
        center=(75, 15),
        color=(0, 0, 0)
    )
    render_text(
        text=f'T: {display_data.transpose}',
        screen=screen,
        font=small_font,
        center=(15, 42),
        color=(0, 0, 0)
    )
    render_text(
        text=f'V: {display_data.velocity}',
        screen=screen,
        font=small_font,
        center=(130, 42),
        color=(0, 0, 0)
    )

    pygame.display.update()
    pygame.display.flip()


def init_window():
    pygame.init()

    pygame.font.init()

    pygame.display.set_caption('midi controller')
    screen = pygame.display.set_mode((150, 50))

    # TODO: set always pinned to top

    return screen

# midiout
NOTE_ON = 0x90
NOTE_OFF = 0x80

def midiout_on(midiout, note, velocity):
    midiout.send_message([NOTE_ON, note, velocity])

def midiout_off(midiout, note):
    midiout.send_message([NOTE_OFF, note, 0])


def create_midiout():
    midiout = rtmidi.MidiOut()
    available_ports = midiout.get_ports()

    if available_ports:
        midiout.open_port(0)
    else:
        midiout.open_virtual_port('my virtual output')

    return midiout


class Controller:
    TRANSPOSE_RANGE = (0-55, 127-55)
    VELOCITY_RANGE = (0, 127)

    def __init__(self, midiout):
        self.midiout = midiout

        self.base_note = {
            pygame.K_z:         55,
            pygame.K_x:         56,
            pygame.K_c:         57,
            pygame.K_v:         58,
            pygame.K_b:         59,
            pygame.K_n:         60,
            pygame.K_m:         61,
            pygame.K_COMMA:     62,
            pygame.K_PERIOD:    63,
            pygame.K_SLASH:     64,

            pygame.K_a:         60,
            pygame.K_s:         61,
            pygame.K_d:         62,
            pygame.K_f:         63,
            pygame.K_g:         64,
            pygame.K_h:         65,
            pygame.K_j:         66,
            pygame.K_k:         67,
            pygame.K_l:         68,
            pygame.K_SEMICOLON: 69,
            pygame.K_QUOTE:     70,

            pygame.K_q:            65,
            pygame.K_w:            66,
            pygame.K_e:            67,
            pygame.K_r:            68,
            pygame.K_t:            69,
            pygame.K_y:            70,
            pygame.K_u:            71,
            pygame.K_i:            72,
            pygame.K_o:            73,
            pygame.K_p:            74,
            pygame.K_LEFTBRACKET:  75,
            pygame.K_RIGHTBRACKET: 76,
            pygame.K_BACKSLASH:    77,

            pygame.K_1:            70,
            pygame.K_2:            71,
            pygame.K_3:            72,
            pygame.K_4:            73,
            pygame.K_5:            74,
            pygame.K_6:            75,
            pygame.K_7:            76,
            pygame.K_8:            77,
            pygame.K_9:            78,
            pygame.K_0:            79,
            pygame.K_MINUS:        80,
            pygame.K_EQUALS:       81,
        }
        self.notes = set()
        self.transpose = 0
        self.velocity = 112
        self.sustain = False

    def _key_is_note(self, key):
        return key in self.base_note

    def _note_from_key(self, key):
        return self.base_note[key] + self.transpose

    def _release(self):
        for note in range(0, 127):
            midiout_off(self.midiout, note)

    def _note_on(self, note):
        midiout_on(self.midiout, note, self.velocity)
        self.notes.add(note)

    def _note_off(self, note):
        midiout_off(self.midiout, note)
        self.notes.remove(note)


    def handle_keyup(self, key):
        if self._key_is_note(key) and not self.sustain:
            self._note_off(self._note_from_key(key))

    def handle_keydown(self, key, modifiers):
        transpose_delta = 12 if modifiers & pygame.KMOD_SHIFT else 1

        if self._key_is_note(key):
            self._note_on(self._note_from_key(key))

        # velocity
        elif key == pygame.K_UP:
            self.velocity = clamp(self.velocity + 8, *Controller.VELOCITY_RANGE)
        elif key == pygame.K_DOWN:
            self.velocity = clamp(self.velocity - 8, *Controller.VELOCITY_RANGE)
        # transpose
        elif key == pygame.K_LEFT:
            self.transpose = \
                clamp(self.transpose - transpose_delta, *Controller.TRANSPOSE_RANGE)
        elif key == pygame.K_RIGHT:
            self.transpose = \
                clamp(self.transpose + transpose_delta, *Controller.TRANSPOSE_RANGE)
        # misc
        elif key == pygame.K_ESCAPE:
            self._release()


@dataclass
class DisplayData:
    notes: set
    velocity: int
    transpose: int

    def update_from(self, controller):
        self.notes = controller.notes
        self.velocity = controller.velocity
        self.transpose = controller.transpose



def mainloop(midiout, screen):
    controller = Controller(midiout)
    display_data = DisplayData(set(), 0, 0)

    running = True

    with midiout:
        while running:
            # event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type == pygame.KEYDOWN:
                    controller.handle_keydown(event.key, event.mod)

                elif event.type == pygame.KEYUP:
                    controller.handle_keyup(event.key)

            display_data.update_from(controller)

            update_screen(screen, display_data)


    pygame.quit()

if __name__ == '__main__':
    midiout = create_midiout()
    screen = init_window()
    mainloop(midiout, screen)
    del midiout
