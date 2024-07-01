import time

import sdl2
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from sdl_driver import SDLDriver, update_joysticks_binding
from BrunnerDrive import RudderTrim
import json
import os


class Binding:
    def __init__(self):
        self.bindings_file = 'bindings.json'
        self.bindings = {}
        self.current_function = None

    # Load Binding From Files
    def load_bindings(self):
        print('loaded')
        if os.path.exists(self.bindings_file):
            with open(self.bindings_file, 'r') as file:
                loaded_bindings = json.load(file)
                self.bindings = update_joysticks_binding(loaded_bindings)
            self.save_bindings()
        print(self.bindings)

    def save_bindings(self):
        with open(self.bindings_file, 'w') as file:
            json.dump(self.bindings, file)


class MyApp:
    def __init__(self):
        self.app = Flask(__name__, static_folder='static')
        self.app.config['SECRET_KEY'] = 'secret!'
        self.app.config['DEBUG'] = True
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins='*')

        self.driver = SDLDriver()
        self.driver.start()

        self.rudderTrim = RudderTrim()
        self.binding = Binding()
        self.binding.load_bindings()

        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def serve():
            return send_from_directory(self.app.static_folder, 'index.html')

        @self.app.route('/<path:path>')
        def static_proxy(path):
            return send_from_directory(self.app.static_folder, path)

        @self.app.route('/bind', methods=['POST'])
        def bind_action():
            data = request.json
            self.driver.clear_callbacks()
            self.driver.add_event_listener(sdl2.SDL_JOYBUTTONDOWN, self.button_down_binding_callback)
            self.driver.add_event_listener(sdl2.SDL_JOYHATMOTION, self.hat_motion_binding_callback)
            self.binding.current_function = data['function']
            return jsonify(success=True)

        @self.app.route('/delete', methods=['POST'])
        def delete():
            data = request.json
            function = data['function']
            self.binding.bindings.pop(function)
            self.socketio.emit('bindings_updated', self.binding.bindings)  # Notify Frontend
            return jsonify(success=True)

        @self.app.route('/bindings', methods=['GET'])
        def get_bindings():
            return jsonify(self.binding.bindings)

        @self.app.route('/reload', methods=['POST'])
        def reload_bindings():
            self.binding.load_bindings()
            return jsonify(success=True)

        @self.app.route('/clear_bindings', methods=['POST'])
        def clear_bindings():
            self.binding.bindings = {}
            if os.path.exists(self.binding.bindings_file):
                os.remove(self.binding.bindings_file)
            return jsonify(success=True)

        @self.app.route('/start', methods=['POST'])
        def start():
            self.driver.status = 'running'
            self.driver.clear_callbacks()
            self.driver.add_event_listener(sdl2.SDL_JOYBUTTONDOWN, self.brunner_running_button_callbacks)
            self.driver.add_event_listener(sdl2.SDL_JOYHATMOTION, self.brunner_running_hat_callbacks)
            return jsonify(success=True)

        @self.app.route('/stop', methods=['POST'])
        def stop():
            self.driver.clear_callbacks()
            self.driver.status = 'waiting'
            return jsonify(success=True)

        @self.app.route('/status', methods=['GET'])
        def get_status():
            return jsonify(status=self.driver.status)

    def button_down_binding_callback(self, instance_id, name, button):
        self.driver.clear_callbacks()
        event_data = {
            'device_id': instance_id,
            'device_name': name,
            'button': button,
            'event_type': 'down'
        }
        print(f"keydown:{event_data}")
        self.bind_button(event_data)

    def hat_motion_binding_callback(self, instance_id, name, value):
        self.driver.clear_callbacks()
        event_data = {
            'device_id': instance_id,
            'device_name': name,
            'pov': value,
            'event_type': 'pov'
        }
        print(f"hat:{event_data}")
        self.bind_button(event_data)

    def bind_button(self, data):
        function = self.binding.current_function
        new_device_id = data['device_id']
        new_device_name = data['device_name']
        new_button = data.get('button')
        new_pov = data.get('pov')

        # Remove Anomalous Input
        if new_button is None and new_pov is None:
            self.socketio.emit('bindings_updated', self.binding.bindings)  # Notify Frontend
            return

        if new_button == 0 or (new_pov is not None and new_pov == 0):
            self.socketio.emit('bindings_updated', self.binding.bindings)  # Notify Frontend
            return
        print(f'new{data}')

        # Remove Repeated Binding
        if new_device_id is not None:
            for func, key in list(self.binding.bindings.items()):
                if key['device_id'] == new_device_id:
                    if new_button is not None and new_button != 0 and key.get('button') == new_button:
                        self.binding.bindings.pop(func)
                    elif new_pov is not None and new_pov != 0 and key.get('pov') == new_pov:
                        self.binding.bindings.pop(func)

        if new_device_id is None:
            self.binding.bindings.pop(function, None)
        else:
            self.binding.bindings[function] = {
                'device_id': new_device_id,
                'device_name': new_device_name,
                'button': new_button,
                'pov': new_pov
            }
        self.binding.save_bindings()
        print(f"current binding:{self.binding.bindings}")
        self.socketio.emit('bindings_updated', self.binding.bindings)  # Notify Frontend

    def get_function_from_binding(self, instance_id, button_or_pov, type):
        for function, key in self.binding.bindings.items():
            if key['device_id'] == instance_id:
                if ((type == 'pov' and key.get('pov') == button_or_pov) or
                        type == 'button' and key.get('button') == button_or_pov):
                    return function
        return None

    def brunner_running_button_callbacks(self, instance_id, name, value):
        function = self.get_function_from_binding(instance_id, value, 'button')
        if function:
            self.execute_function(function)
            self.socketio.emit('log', function)

    def brunner_running_hat_callbacks(self, instance_id, name, value):
        function = self.get_function_from_binding(instance_id, value, 'pov')
        if function:
            self.execute_function(function)
            self.socketio.emit('log', function)

    def execute_function(self, function):
        if function == 'Trim Set':
            print('Trim Set')
            self.rudderTrim.set_trim()
        elif function == 'Trim Release':
            print('release')
            self.rudderTrim.release_trim()
        elif function == 'Trim Left':
            print('left')
            self.rudderTrim.trim_left()
        elif function == 'Trim Right':
            print('right')
            self.rudderTrim.trim_right()

    def run(self):
        self.socketio.run(self.app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True, debug=False)


if __name__ == '__main__':
    app_instance = MyApp()
    app_instance.run()
