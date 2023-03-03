import time
import board
import digitalio
import neopixel
import statemachines

UKRAINE_YELLOW = tuple(int(x/6) for x in (255, 0xD5, 0))
SAPPHIRE = tuple(int(x/6) for x in (00, 0x5B, 0xBB))

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
        self.color_list = (
            (4.659090909090909, 2.3181818181818183, 5.795454545454546),
            (5.795454545454546, 2.2954545454545454, 3.477272727272727),
            (5.795454545454546, 0.0, 0.0),
            (5.795454545454546, 3.227272727272727, 0.0),
            (5.795454545454546, 5.795454545454546, 0.0),
            (0.0, 3.227272727272727, 0.0),
            (0.0, 4.363636363636363, 4.363636363636363),
            (1.4545454545454546, 0.0, 3.4545454545454546),
            (3.227272727272727, 0.0, 3.227272727272727))

        if self.button_was_pressed():
            self.color_list = None
            return self.ukraine, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def hanukkah(self, now):
        self.color_list = ((0, 0, 12), (4,  4, 4))

        if self.button_was_pressed():
            self.color_list = None
            return self.pride, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def ukraine(self, now):
        self.color_list = (UKRAINE_YELLOW, SAPPHIRE)

        if self.button_was_pressed():
            self.color_list = None
            return self.flickering, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def xmass(self, now):
        self.color_list = (( 2, 12, 0), (12,  0, 0))

        if self.button_was_pressed():
            self.color_list = None
            return self.hanukkah, statemachines.IMMEDATE_TRANSFER

        return None, self.button_watcher

    def flickering(self, now):
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
            return self.new_cycle, statemachines.IMMEDATE_TRANSFER
        return self.idle, self.controller

    def idle(self, now):
        if self.controller.colors():
            return self.new_cycle, statemachines.IMMEDATE_TRANSFER
        return None, self.controller

    def new_cycle(self, now):
        self.color_list = self.controller.colors()
        self.color_index = 0
        self.step = 1
        return self.up, statemachines.IMMEDATE_TRANSFER

    def up(self, now):
        if self.controller.colors() is not self.color_list:
            return self.idle, statemachines.IMMEDATE_TRANSFER

        self.pixels[0] = [ int(x*self.step/4) for x in self.color_list[self.color_index] ]
        self.step += 1
        if self.step >= 44:
            return self.down, statemachines.IMMEDATE_TRANSFER
        return None, self.pulser

    def down(self, now):
        if self.controller.colors() is not self.color_list:
            return self.idle, statemachines.IMMEDATE_TRANSFER

        self.pixels[0] = [ int(x*self.step/4) for x in self.color_list[self.color_index] ]
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
