import time
import board
import digitalio
import neopixel
import statemachines

COLOR_CYCLE_STEP_MAX = 44
COLOR_CYCLE_STEP_DIV = 4

def color_cycle_color_limiter(*color):
    max_multiplier = COLOR_CYCLE_STEP_MAX / COLOR_CYCLE_STEP_DIV
    max_component = max(color)
    if max_component * max_multiplier < 256:
        return color

    scale_factor = (255 / ( max_component *  max_multiplier))
    assert scale_factor * max_component *  max_multiplier < 256, color

    return tuple((c * scale_factor for c in color))

def color_cycle_pallet_limiter(*pallet):
    return tuple((color_cycle_color_limiter(*color) for color in pallet))

def number_color_to_tuple(hex_color):
    return (hex_color >> 16 & 0xFF, hex_color >> 8 & 0xFF,hex_color & 0xFF)

def number_palet_to_tuple(*pallet):
    return tuple((number_color_to_tuple(color) for color in pallet))

UKRAINE_YELLOW = (255, 0xD5, 0)
SAPPHIRE = (00, 0x5B, 0xBB)
UKRAINE_PALLET = color_cycle_pallet_limiter(UKRAINE_YELLOW, SAPPHIRE)

XMASS_PALLET = color_cycle_pallet_limiter((42, 255, 0), (255, 0, 0))
HANUKKAH_PALLET = color_cycle_pallet_limiter((0, 0, 255), (64, 64, 64))
PRIDE_PALLET = color_cycle_pallet_limiter(*number_palet_to_tuple(0xE40303, 0xFF4000, 0xFFED00, 0x008026, 0x24408E, 0x732982))

class Controller:
    def __init__(self, button_watcher):
        self.button_watcher = button_watcher
        self.count = 0
        self.candle = False
        self.color_list = None
        self.last_count_triggered = self.count

    def button_was_pressed(self):
        if self.button_watcher.consume():
            self.count += 1
            return True
        return False

    def colors(self):
        return self.color_list

    def start(self, now):
        return self.flickering, statemachines.IMMEDATE_TRANSFER

    def pride(self, now):
        print("pride")
        self.color_list = PRIDE_PALLET

        if self.button_was_pressed():
            self.color_list = None
            return self.ukraine, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def hanukkah(self, now):
        print("hanukkah")
        self.color_list = HANUKKAH_PALLET

        if self.button_was_pressed():
            self.color_list = None
            return self.pride, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def ukraine(self, now):
        print("ukraine")
        self.color_list = UKRAINE_PALLET

        if self.button_was_pressed():
            self.color_list = None
            return self.flickering, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def xmass(self, now):
        print("christmas")
        self.color_list = XMASS_PALLET

        if self.button_was_pressed():
            self.color_list = None
            return self.hanukkah, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def flickering(self, now):
        print("flame")
        self.candle = True

        if self.button_was_pressed():
            self.candle = False
            return self.xmass, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def triggered(self):
        if  self.count != self.last_count_triggered:
            self.last_count_triggered = self.count
            return True

        return False

class OurFlicker(statemachines.NeoPixelFlicker):
    def __init__(self, pixels, event, policy, controller):
        super().__init__(pixels, 0, event, policy)
        self.controller = controller

    def suppress(self):
        if self.controller.candle:
            return None

        return self.controller

class ColorCycle:
    def __init__(self, pixels, pulser, controller):
        self.pixels = pixels
        self.pulser = pulser
        self.controller = controller
        self.color_list = None

    def start(self, now):
        if self.controller.colors():
            print(f"color cycle over: {self.controller.colors()}")
            return self.new_cycle, statemachines.IMMEDATE_TRANSFER
        return self.idle, self.controller

    def idle(self, now):
        if self.controller.colors():
            print(f"color cycle over: {self.controller.colors()}")
            return self.new_cycle, statemachines.IMMEDATE_TRANSFER
        return None, self.controller

    def new_cycle(self, now):
        self.color_list = self.controller.colors()
        self.color_index = 0
        self.step = 1

        return self.up, statemachines.IMMEDATE_TRANSFER

    def load_pixel(self):
        self.pixels[0] = [ int(x*self.step/COLOR_CYCLE_STEP_DIV) for x in self.color_list[self.color_index] ]

    def up(self, now):
        if self.controller.colors() is not self.color_list:
            return self.idle, statemachines.IMMEDATE_TRANSFER

        self.load_pixel()
        self.step += 1
        if self.step >= COLOR_CYCLE_STEP_MAX:
            return self.down, statemachines.IMMEDATE_TRANSFER
        return None, self.pulser

    def down(self, now):
        if self.controller.colors() is not self.color_list:
            return self.idle, statemachines.IMMEDATE_TRANSFER

        self.load_pixel()
        self.step -= 1
        if self.step < 1:
            self.color_index += 1
            if self.color_index >= len(self.color_list):
                return self.new_cycle, statemachines.IMMEDATE_TRANSFER
            return self.up, statemachines.IMMEDATE_TRANSFER
        return None, self.pulser

# debuging aid
blinker = statemachines.UnevenBlinker(board.LED, 0.5, 4.5)
statemachines.register_machine(blinker)

pulser = statemachines.Pulser(0.01)
# input
button_watcher = statemachines.ButtonWatcher(board.BUTTON, pulser, invert=True)
controller = Controller(button_watcher)

statemachines.register_machine(button_watcher, controller)

pixels = neopixel.NeoPixel(board.D5, pixel_order=neopixel.GRB, n=1, auto_write=False)


# Flickering
flicker_policy = statemachines.FlickerPolicy(index_bottom=32,
                                             index_min=64,
                                             index_max=128)
flicker = OurFlicker(pixels, pulser, flicker_policy, controller)
statemachines.register_machine(flicker)

# Cycling
cycler = ColorCycle(pixels, statemachines.Pulser(0.04), controller)
statemachines.register_machine(cycler)

statemachines.run((pixels.show,))
