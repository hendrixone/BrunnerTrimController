from enum import IntEnum
import socket
import struct


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

        self.trim_increment = 0.05

        self.current_trim_pos = 0


    def get_rudder_pos(self):
        query_readpos = build_get_pos_query(AxisBitmask.Rudder)
        pos_response = sendThenReceive(query_readpos, self.remoteEndpoint, self.sock)
        print(f"pos_response length: {len(pos_response)}")
        length, status, node_yaw, pos_yaw = struct.unpack('<HBHf', pos_response[0:15])
        return pos_yaw

    def update_trim(self):
        query_set_trim_pos_yaw = build_set_trim_pos_query(self.current_trim_pos, AxisBitmask.Rudder)
        sendThenReceive(query_set_trim_pos_yaw, self.remoteEndpoint, self.sock)

    def set_trim(self):
        self.current_trim_pos = self.get_rudder_pos()
        self.update_trim()

    def release_trim(self):
        self.current_trim_pos = 0
        self.update_trim()

    def trim_left(self):
        self.current_trim_pos -= self.trim_increment
        self.update_trim()

    def trim_right(self):
        self.current_trim_pos += self.trim_increment
        self.update_trim()
