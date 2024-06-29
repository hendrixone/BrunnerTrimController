import os
import time
import tkinter as tk
from tkinter import ttk
import json
import pygame
from threading import Thread

import BrunnerDrive
class HotkeyBinder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hotkey Binder")
        self.geometry("700x200")

        start_time = time.time()

        self.hotkeys = {"Trim Release": None, "Trim Set": None, "Trim Left": None, "Trim Right": None}
        self.selected_hotkey = None

        self.load_config()

        print(f"Config loaded in {time.time() - start_time:.2f} seconds")

        pygame.init()
        pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        self.previous_button_states = {joystick.get_id(): [False] * joystick.get_numbuttons() for joystick in
                                       self.joysticks}

        self.previous_hat_states = {joystick.get_id(): [(0, 0)] * joystick.get_numhats() for joystick in self.joysticks}

        print(f"Joysticks initialized in {time.time() - start_time:.2f} seconds")

        self.create_widgets()
        self.bind_all("<KeyPress>", self.on_key_press)
        self.running = True

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.input_thread = Thread(target=self.detect_game_controller_input)
        self.input_thread.start()

        print(f"Initialization complete in {time.time() - start_time:.2f} seconds")

    def create_widgets(self):
        self.labels = {}
        self.buttons = {}

        for idx, hotkey in enumerate(self.hotkeys.keys()):
            label_text = f"{hotkey}: {self.hotkeys[hotkey] if self.hotkeys[hotkey] else 'Not bound'}"
            label = ttk.Label(self, text=label_text, anchor="w", width=80)
            label.grid(row=idx, column=0, padx=10, pady=5, sticky="W")
            self.labels[hotkey] = label

            button = ttk.Button(self, text=f"Bind", command=lambda h=hotkey: self.bind_hotkey(h))
            button.grid(row=idx, column=1, padx=15, pady=5, sticky="E")
            self.buttons[hotkey] = button

        self.submit_button = ttk.Button(self, text="Submit", command=self.save_config)
        self.submit_button.grid(row=4, column=0, columnspan=2, pady=10, ipadx=10)

    def bind_hotkey(self, hotkey):
        self.selected_hotkey = hotkey
        self.labels[hotkey].config(text=f"{hotkey}: Press a key or button")

    def on_key_press(self, event):
        if self.selected_hotkey:
            key_info = f"{event.keysym} ({event.keycode})"
            self.hotkeys[self.selected_hotkey] = key_info
            self.labels[self.selected_hotkey].config(text=f"{self.selected_hotkey}: {key_info}")
            self.selected_hotkey = None

    def detect_game_controller_input(self):
        while self.running:
            pygame.event.pump()
            for joystick in self.joysticks:
                device_name = joystick.get_name()
                device_id = joystick.get_id()

                # Detect button presses
                for i in range(joystick.get_numbuttons()):
                    current_state = joystick.get_button(i)
                    if current_state and not self.previous_button_states[device_id][i]:
                        button_info = f"{device_name} Button {i}"
                        if self.selected_hotkey:
                            self.hotkeys[self.selected_hotkey] = button_info
                            self.labels[self.selected_hotkey].config(text=f"{self.selected_hotkey}: {button_info}")
                            self.selected_hotkey = None
                    self.previous_button_states[device_id][i] = current_state

                # Detect POV (HAT) presses
                hat_count = joystick.get_numhats()
                for j in range(hat_count):
                    current_hat_state = joystick.get_hat(j)
                    if current_hat_state != self.previous_hat_states[device_id][j]:
                        hat_info = f"{device_name} POV {j} {current_hat_state}"
                        if self.selected_hotkey:
                            self.hotkeys[self.selected_hotkey] = hat_info
                            self.labels[self.selected_hotkey].config(text=f"{self.selected_hotkey}: {hat_info}")
                            self.selected_hotkey = None
                    self.previous_hat_states[device_id][j] = current_hat_state

    def load_config(self):
        if os.path.exists("config.json"):
            with open("config.json", "r") as config_file:
                self.hotkeys = json.load(config_file)

    def save_config(self):
        self.running = False
        with open("config.json", "w") as config_file:
            json.dump(self.hotkeys, config_file)
        self.destroy()
        self.run_main_loop()

    def on_closing(self):
        self.running = False
        self.destroy()
        pygame.quit()
        quit()

    def run_main_loop(self):
        print("Entering main loop...")
        driver = BrunnerDrive.HotkeyHandler(self.hotkeys)
        driver.start()

if __name__ == "__main__":
    app = HotkeyBinder()
    app.mainloop()
