from enum import IntEnum
import socket
import struct

import pygame


# Protocol for commands is as documented in https://cls2sim.brunner-innovation.swiss/

class AxisBitmask(IntEnum):
    Elevator = 0x1
    Aileron = 0x2
    Rudder = 0x4
    Collective = 0x8
    BrakesLeft = 0x10
    BrakesRight = 0x20
    TrimElevator = 0x40
    TrimAileron = 0x80
    TrimRudder = 0x100
    Throttle1 = 0x200
    Throttle2 = 0x400
    Throttle3 = 0x800
    Throttle4 = 0x1000
    SpeedBrake = 0x2000
    NoseWheel = 0x4000
    Seatshaker = 0x8000


def build_get_pos_query(axis):
    return struct.pack('<III', 0xD0, axis, 0x11)


def build_set_trim_pos_query(trim_pos, axis):
    return struct.pack('<IIIf', 0xCE, axis, 0x90, trim_pos)


def sendThenReceive(send_data, targetAddr, sock):
    # after each send you HAVE to do a read, even if you don't do anything with the reponse
    sock.sendto(send_data, targetAddr)
    response, address = sock.recvfrom(8192)
    return response


class RudderTrim:
    def __init__(self):
        self.timeout = 8
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 5)
        self.sock.settimeout(self.timeout)
        self.sock.bind(('', 0))
        self.remoteEndpoint = ('127.0.0.1', 15090)

        self.current_trim_pos = 0

    def get_rudder_pos(self):
        query_readpos = build_get_pos_query(AxisBitmask.Rudder)
        pos_response = sendThenReceive(query_readpos, self.remoteEndpoint, self.sock)
        print(f"pos_response length: {len(pos_response)}")
        length, status, node_yaw, pos_yaw = struct.unpack('<HBHf', pos_response[0:15])
        return pos_yaw

    def release_trim(self):
        self.current_trim_pos = 0
        self.update_trim()

    def update_trim(self):
        query_set_trim_pos_yaw = build_set_trim_pos_query(self.current_trim_pos, AxisBitmask.Rudder)
        sendThenReceive(query_set_trim_pos_yaw, self.remoteEndpoint, self.sock)

    def set_trim(self):
        self.current_trim_pos = self.get_rudder_pos()
        self.update_trim()

    def trim_left(self):
        self.current_trim_pos -= 0.05
        self.update_trim()

    def trim_right(self):
        self.current_trim_pos += 0.05
        self.update_trim()


class HotkeyHandler:
    def __init__(self, hotkeys):
        self.hotkeys = hotkeys
        self.running = True
        pygame.init()
        pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        self.previous_button_states = {joystick.get_id(): [False] * joystick.get_numbuttons() for joystick in
                                       self.joysticks}
        self.previous_hat_states = {joystick.get_id(): [[0, 0]] * joystick.get_numhats() for joystick in self.joysticks}

        self.RudderTrim = RudderTrim()

    def start(self):
        while self.running:
            pygame.event.pump()
            for joystick in self.joysticks:
                device_name = joystick.get_name()
                device_id = joystick.get_id()

                # Detect button presses
                for i in range(joystick.get_numbuttons()):
                    current_state = joystick.get_button(i)
                    if current_state and not self.previous_button_states[device_id][i]:
                        self.on_key_down(f"{device_name} Button {i}")
                    elif not current_state and self.previous_button_states[device_id][i]:
                        self.on_key_up(f"{device_name} Button {i}")
                    self.previous_button_states[device_id][i] = current_state

                # Detect POV (HAT) presses
                hat_count = joystick.get_numhats()
                for j in range(hat_count):
                    current_hat_state = joystick.get_hat(j)
                    if current_hat_state != self.previous_hat_states[device_id][j]:
                        self.on_hat_change(f"{device_name} POV {j}", current_hat_state)
                    self.previous_hat_states[device_id][j] = current_hat_state

    def on_key_down(self, key):
        for function, bound_key in self.hotkeys.items():
            if key == bound_key:
                print(f"Function {function} triggered on key down: {key}")
                self.trigger_action(function)

    def on_key_up(self, key):
        for function, bound_key in self.hotkeys.items():
            if key == bound_key:
                print(f"Function {function} triggered on key up: {key}")

    def on_hat_change(self, hat, state):
        hat_key = f"{hat} {state}"
        for function, bound_key in self.hotkeys.items():
            if hat_key == bound_key:
                print(f"Function {function} triggered on hat change: {hat_key}")
                self.trigger_action(function)

    def trigger_action(self, function):
        if function == 'Trim Release':
            self.RudderTrim.release_trim()
        elif function == 'Trim Set':
            self.RudderTrim.set_trim()
        elif function == 'Trim Left':
            self.RudderTrim.trim_left()
        elif function == 'Trim Right':
            self.RudderTrim.trim_right()
