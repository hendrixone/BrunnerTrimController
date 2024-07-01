# sdl_driver.py
import ctypes
from threading import Thread

import sdl2
import sdl2.ext


def update_joysticks_binding(loaded_bindings):
    current_joysticks = {}
    for i in range(sdl2.SDL_NumJoysticks()):
        joystick = sdl2.SDL_JoystickOpen(i)
        if joystick:
            device_name = sdl2.SDL_JoystickName(joystick).decode('utf-8')
            current_joysticks[device_name] = sdl2.SDL_JoystickInstanceID(joystick)
            sdl2.SDL_JoystickClose(joystick)  # 确保打开设备后关闭

    updated_bindings = {}
    for function, binding in loaded_bindings.items():
        device_name = binding['device_name']
        if device_name in current_joysticks:
            updated_bindings[function] = {
                'device_id': current_joysticks[device_name],
                'device_name': device_name,
                'button': binding.get('button'),
                'pov': binding.get('pov')
            }
        else:
            updated_bindings[function] = {
                'device_id': None,
                'device_name': device_name,
                'button': binding.get('button'),
                'pov': binding.get('pov')
            }

    print(f"Updated bindings: {updated_bindings}")
    return updated_bindings


class SDLDriver:
    def __init__(self):
        self.joysticks = {}
        self.running = False
        self.status = 'idle'

        if sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK) != 0:
            print(f"SDL_Init Error: {sdl2.SDL_GetError()}")
            exit(1)

        num_joysticks = sdl2.SDL_NumJoysticks()
        print(f"Number of joystick devices: {num_joysticks}")

        for i in range(num_joysticks):
            joystick = sdl2.SDL_JoystickOpen(i)
            if joystick:
                name = sdl2.SDL_JoystickName(joystick).decode('utf-8')
                instance_id = sdl2.SDL_JoystickInstanceID(joystick)
                self.joysticks[instance_id] = {
                    "joystick": joystick,
                    "name": name
                }
                print(f"Joystick {instance_id} name: {name}")
            else:
                print(f"Failed to open joystick {i}")

        self.event_callbacks = {
            sdl2.SDL_JOYBUTTONDOWN: [],
            sdl2.SDL_JOYBUTTONUP: [],
            sdl2.SDL_JOYHATMOTION: []
        }

        self.listener_thread = Thread(target=self.monitor_joysticks)

    def add_event_listener(self, event_type, callback):
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
        else:
            print(f"Unsupported event type: {event_type}")

    def clear_callbacks(self):
        self.event_callbacks = {
            sdl2.SDL_JOYBUTTONDOWN: [],
            sdl2.SDL_JOYBUTTONUP: [],
            sdl2.SDL_JOYHATMOTION: []
        }

    def handle_events(self):
        event = sdl2.SDL_Event()
        # 缓存事件回调列表
        button_down_callbacks = self.event_callbacks[sdl2.SDL_JOYBUTTONDOWN]
        button_up_callbacks = self.event_callbacks[sdl2.SDL_JOYBUTTONUP]
        hat_motion_callbacks = self.event_callbacks[sdl2.SDL_JOYHATMOTION]

        while sdl2.SDL_PollEvent(event):
            if event.type == sdl2.SDL_QUIT:
                return
            elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                instance_id = event.jbutton.which
                if instance_id in self.joysticks:
                    name = self.joysticks[instance_id]['name']
                    # print(instance_id, name, event.jbutton.button)
                    for callback in button_down_callbacks:
                        callback(instance_id, name, event.jbutton.button)
            elif len(self.event_callbacks[sdl2.SDL_JOYBUTTONUP]) != 0 and event.type == sdl2.SDL_JOYBUTTONUP:
                instance_id = event.jbutton.which
                if instance_id in self.joysticks:
                    name = self.joysticks[instance_id]['name']
                    for callback in button_up_callbacks:
                        callback(instance_id, name, event.jbutton.button)
            elif event.type == sdl2.SDL_JOYHATMOTION:
                instance_id = event.jhat.which
                if instance_id in self.joysticks:
                    name = self.joysticks[instance_id]['name']
                    # print(instance_id, name, event.jhat.value, event.type)
                    for callback in hat_motion_callbacks:
                        callback(instance_id, name, event.jhat.value)

    def monitor_joysticks(self):
        while self.running:
            self.handle_events()

    def start(self):
        self.running = True
        self.listener_thread.start()

    def stop(self):
        self.running = False
        self.listener_thread.join()
