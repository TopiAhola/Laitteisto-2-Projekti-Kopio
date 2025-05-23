from machine import UART, Pin, I2C, Timer, ADC, PWM
from ssd1306 import SSD1306_I2C
from fifo import Fifo
import time, ujson


# Encoder input interrupt
class Encoder:
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.fifo = Fifo(30, typecode='i')
        self.a.irq(handler=self.handler, trigger=Pin.IRQ_RISING, hard=True)

    def handler(self, pin):
        # print("handler called")
        if self.b():
            self.fifo.put(-1)
        else:
            self.fifo.put(1)


# Encoder button input interrupt
class Button:
    def __init__(self, pin):
        self.fifo = Fifo(1, typecode='i')
        self.pin = pin
        self.pin.irq(handler=self.button_handler, trigger=Pin.IRQ_RISING)

    def button_handler(self):
        self.fifo.put(1)


# Pulse sensor timed interrupt
class Pulse_measurement:
    measurements = {}

    def __init__(self):
        self.name = f"Measurement {len(Pulse_measurement.measurements)}"
        self.timer = Timer(mode=Timer.PERIODIC, freq=200, callback=self.log_data)
        self.fifo = Fifo(800, typecode='i')
        Pulse_measurement.measurements[self.name] = self

    def start(self):
        # This is a redundant function for now. Unless continuing a measurement is needed.
        self.timer = Timer(mode=Timer.PERIODIC, freq=200, callback=self.log_data)

    def log_data(self):
        self.fifo.put(adc1.read_u16())

    def stop(self):
        self.timer.deinit()  # deinit might be useful as a standalone function too.



# Menu ASM class
class Menu:
    # General Class methods:
    def __init__(self):
        self.state = self.main_menu
        self.cursor_position = 0
        self.cycle_time = 0.05
        self.last_measurement = []


    def run(self):
        self.state()

    def update_cursor(self, len_options):
        enc1_input = 0
        while not enc1.fifo.empty():
            try:
                enc1_input = enc1_input + enc1.fifo.get()
            except:
                print("Fifo is empty..")
        self.cursor_position = self.cursor_position + enc1_input
        if self.cursor_position > len_options-1:
            self.cursor_position = len_options-1
        if self.cursor_position < 0:
            self.cursor_position = 0


    def select_option(self, cursor_position, options):
        button_input = 0
        if not button.fifo.empty():
            button_input = button.fifo.get()
        if button_input:
            self.state = options[cursor_position]
            self.cursor_position = 0

    # Render functions to draw menus
    def render_menu(self, header, text_lines, option_lines):
        oled.fill(0)
        oled.text(header, 4, 0, 1)
        n=0
        for line in text_lines:            
            oled.text(line, 4, 9*n, 1)
            n = n+1
        for line in option_lines:
            oled.text(line, 4, 9*n, 1)
            n = n+1
        oled.text("[               ]",0,9*(1+len(text_lines)+self.cursor_position),1)
        oled.show()

    def render_measurement_screen(self):
        oled.fill(0)
        oled.text("Measurement in progress", 0, 0, 1)
        oled.text("Press button to cancel", 0, 9, 1)
        oled.show()

    # Menu states with sleep timers:
    def main_menu(self):
        header: str = "Main Menu"
        text_lines: list[str] = ["Welcome","Choose option:"]
        option_lines : list[str] = ["Submenu1", "Submenu2", "default"]
        options = [self.submenu1, self.submenu2, self.default]
        self.select_option(self.cursor_position, options)
        self.update_cursor(len(options))
        self.render_menu(header,text_lines, option_lines)
        time.sleep(self.cycle_time)


    def measurement_start_menu(self):
        # state active during pulse measurement, options: user cancel
        header: str = "Default Menu"
        text_lines: list[str] = ["Choose option:"]
        option_lines: list[str] = ["Submenu1", "Submenu2", "default"]
        options = []

        self.select_option(self.cursor_position, options)
        self.update_cursor(len(options))
        self.render_menu(header, text_lines, option_lines)


        # One time only render to save performance during measurement.
        if self.state == self.measurement_active:
            self.render_measurement_screen()


    def measurement_active(self, new_measurement):
        new_measurement = Pulse_measurement()
        duration = 10/self.cycle_time
        cycles = 0
        while cycles < duration:
            button_input = button.fifo.get()
            if button_input:
                new_measurement.stop()
                self.state = self.measurement_cancel
                del new_measurement
                break
            else:
                measurement_ok = True
            time.sleep(self.cycle_time)
            cycles += 1

        if measurement_ok:
            while not new_measurement.fifo.empty():
                try:
                     self.last_measurement.append(enc1.fifo.get())
                except:
                    print("Fifo is empty..")

            self.state = self.measurement_ready


    def measurement_cancel(self):
        pass


    def measurement_ready(self):
        pass

    def submenu1(self):
        pass

    def submenu2(self):
        pass

    def default(self):
        header: str = "Default Menu"
        text_lines: list[str] = ["Choose option:"]
        option_lines : list[str] = ["Submenu1", "Submenu2", "default"]
        options = []

        self.select_option(self.cursor_position, options)
        self.update_cursor(len(options))
        self.render_menu(header, text_lines, option_lines)
        time.sleep(self.cycle_time)

####################################################################################
# Main program
# Globals

# Init menu object
menu = Menu()

# Display definitions
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

# Input Pins
adc1 = ADC(Pin(27))
rot_push = Pin(12, Pin.IN, Pin.PULL_UP)
rota = Pin(10, Pin.IN, Pin.PULL_UP)
rotb = Pin(11, Pin.IN, Pin.PULL_UP)

# Encoder definition
enc1 = Encoder(rota, rotb)

# Button definition
button = Button(rot_push)


while True:
    Menu.run(menu)

