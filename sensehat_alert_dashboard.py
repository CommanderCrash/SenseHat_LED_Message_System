#!/usr/bin/env python3

import os
import socket
import select
from sense_hat import SenseHat
import subprocess
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Set
from flask import Flask, render_template, jsonify, request
from flask import url_for
from flask import send_file
import json
from datetime import datetime, timedelta
import math

app = Flask(__name__, static_folder='static')
sense = SenseHat()
sense.set_rotation(90)

# Configuration
sock_path = "/mnt/ram/sense_hat_socket"
tcp_port = 5150
web_port = 5003

# Global variables for sensor data and message history
last_sensor_update = 0
sensor_data = {}
message_history = []
MAX_HISTORY = 100
ignored_messages = {}  # Store ignored messages and their expiry times

@dataclass
class Message:
    text: str
    priority: int
    color: List[int]
    speed: float
    wav_path: str
    use_espeak: bool
    id: str = ""
    timestamp: float = 0.0
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()
    
    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp

    def to_dict(self):
        return {
            'text': self.text,
            'priority': self.priority,
            'color': self.color,
            'timestamp': datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'id': self.id
        }

class MessageQueue:
    def __init__(self):
        self.queue = queue.PriorityQueue()
        self.queue_lock = threading.Lock()
        self.recent_messages: Set[str] = set()
        self.recent_messages_lock = threading.Lock()
        self.audio_lock = threading.Lock()

    def add_message(self, msg: Message) -> bool:
        with self.recent_messages_lock:
            message_key = f"{msg.text}_{msg.priority}"
            
            # Check if message is ignored
            now = datetime.now()
            if msg.text in ignored_messages:
                if now < ignored_messages[msg.text]:
                    print(f"Message ignored: {msg.text}")
                    return False
                else:
                    # Remove expired ignore
                    del ignored_messages[msg.text]
            
            if message_key not in self.recent_messages:
                self.recent_messages.add(message_key)
                self.queue.put((msg.priority, msg))
                
                # Add to message history
                message_history.append(msg.to_dict())
                if len(message_history) > MAX_HISTORY:
                    message_history.pop(0)
                
                def remove_from_recent():
                    with self.recent_messages_lock:
                        self.recent_messages.discard(message_key)
                
                threading.Timer(2.0, remove_from_recent).start()
                return True
            return False

    def get_message(self) -> Optional[Message]:
        try:
            with self.queue_lock:
                if not self.queue.empty():
                    _, msg = self.queue.get_nowait()
                    return msg
        except queue.Empty:
            pass
        return None

class AudioPlayer:
    def __init__(self):
        self.audio_lock = threading.Lock()
        
    def play_audio(self, wav_path: str):
        if not wav_path or not os.path.exists(wav_path):
            return
            
        with self.audio_lock:
            try:
                subprocess.run(['pkill', 'mplayer'], stderr=subprocess.DEVNULL)
                subprocess.Popen(['mplayer', wav_path], 
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing audio: {e}")

    def speak_text(self, text: str):
        with self.audio_lock:
            try:
                subprocess.run(['pkill', 'espeak'], stderr=subprocess.DEVNULL)
                subprocess.run(["espeak", text], 
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error with espeak: {e}")

class DisplayManager:
    def __init__(self):
        self.sense = sense
        self.display_lock = threading.Lock()
        
    def show_message(self, text: str, color: List[int], speed: float):
        with self.display_lock:
            try:
                sense.set_rotation(90)
                self.sense.show_message(
                    text,
                    text_colour=color,
                    scroll_speed=speed
                )
            except Exception as e:
                print(f"Error displaying message: {e}")

def get_sensor_data():
    global last_sensor_update, sensor_data
    current_time = time.time()
    
    if current_time - last_sensor_update > 60 or not sensor_data:
        temp_c = sense.get_temperature()
        temp_f = (temp_c * 9/5) + 32
        humidity = sense.get_humidity()
        pressure = sense.get_pressure()
        
        # Calculate dew point
        b = 17.62
        c = 243.12
        gamma = (b * temp_c) / (c + temp_c) + math.log(humidity / 100.0)
        dew_point_c = (c * gamma) / (b - gamma)
        dew_point_f = (dew_point_c * 9/5) + 32
        
        # Calculate altitude
        altitude = 44330 * (1 - (pressure/1013.25)**(1/5.255))
        
        # Get motion sensors
        orientation = sense.get_orientation()
        acceleration = sense.get_accelerometer_raw()
        compass = sense.get_compass_raw()
        
        sensor_data = {
            'temperature_f': temp_f,
            'temperature_c': temp_c,
            'humidity': humidity,
            'pressure': pressure,
            'dew_point_f': dew_point_f,
            'dew_point_c': dew_point_c,
            'altitude': altitude,
            'gyro_x': orientation['pitch'],
            'gyro_y': orientation['roll'],
            'gyro_z': orientation['yaw'],
            'accel_x': acceleration['x'],
            'accel_y': acceleration['y'],
            'accel_z': acceleration['z'],
            'mag_x': compass['x'],
            'mag_y': compass['y'],
            'mag_z': compass['z'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        last_sensor_update = current_time
    
    return sensor_data

@app.route('/sounds/<filename>')
def serve_sound(filename):
    try:
        sound_dir = '/home/pi/startup-scripts/main/sensehat_alert/sounds'
        file_path = os.path.join(sound_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"Sound file not found: {file_path}")
            return "File not found", 404
            
        return send_file(file_path, mimetype='audio/wav')
    except Exception as e:
        print(f"Error serving sound file: {str(e)}")
        return str(e), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sensor-data')
def api_sensor_data():
    return jsonify(get_sensor_data())

@app.route('/api/message-history')
def api_message_history():
    return jsonify(message_history)

@app.route('/api/ignore-message', methods=['POST'])
def ignore_message():
    try:
        data = request.json
        message = data.get('message')
        duration = float(data.get('duration', 60))  # Default 60 minutes if not specified
        
        if message:
            expiry_time = datetime.now() + timedelta(minutes=duration)
            ignored_messages[message] = expiry_time
            print(f"Added message to ignore list until {expiry_time}: {message}")
            return jsonify({'success': True})
    except Exception as e:
        print(f"Error setting ignore: {e}")
    return jsonify({'success': False})

@app.route('/api/clear-messages', methods=['POST'])
def clear_messages():
    try:
        global message_history
        message_history = []
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error clearing messages: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-message', methods=['POST'])
def send_test_message():
    try:
        data = request.json.get('message')
        if data:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(sock_path)
            sock.send(data.encode())
            sock.close()
            return jsonify({'success': True})
    except Exception as e:
        print(f"Error sending test message: {e}")
        return jsonify({'success': False, 'error': str(e)})

def message_handler(message_queue: MessageQueue, 
                   audio_player: AudioPlayer,
                   display_manager: DisplayManager):
    while True:
        try:
            msg = message_queue.get_message()
            if msg:
                print(f"Handling message: {msg.text}")
                
                if msg.wav_path:
                    threading.Thread(
                        target=audio_player.play_audio,
                        args=(msg.wav_path,),
                        daemon=True
                    ).start()
                
                if msg.use_espeak:
                    threading.Thread(
                        target=audio_player.speak_text,
                        args=(msg.text,),
                        daemon=True
                    ).start()
                
                display_manager.show_message(msg.text, msg.color, msg.speed)
                
        except Exception as e:
            print(f"Error in message handler: {e}")
        time.sleep(0.1)

def parse_and_queue_message(data: str, message_queue: MessageQueue):
    try:
        print(f"Received data: {data}")
        priority, text, color_str, speed, wav_path, use_espeak = data.split("|")
        
        color = list(map(int, color_str.strip('[]').split(",")))
        
        msg = Message(
            text=text,
            priority=int(priority),
            color=color,
            speed=float(speed),
            wav_path=wav_path,
            use_espeak=bool(int(use_espeak.strip())) if use_espeak.strip() else False
        )
        
        return message_queue.add_message(msg)
        
    except Exception as e:
        print(f"Failed to parse message: {e}")
        return False

def socket_server(message_queue):
    try:
        os.unlink(sock_path)
    except OSError:
        if os.path.exists(sock_path):
            raise

    local_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    local_sock.bind(sock_path)
    local_sock.listen(1)

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_sock.bind(('0.0.0.0', tcp_port))
    tcp_sock.listen(5)

    print(f"Socket server started on port {tcp_port}")
    print(f"Local socket: {sock_path}")

    while True:
        try:
            read_sockets, _, _ = select.select([local_sock, tcp_sock], [], [])
            for sock in read_sockets:
                try:
                    connection, _ = sock.accept()
                    data = connection.recv(1024).decode().strip()
                    if data:
                        parse_and_queue_message(data, message_queue)
                    connection.close()
                except Exception as e:
                    print(f"Error handling connection: {e}")
                    if connection:
                        connection.close()
        except Exception as e:
            print(f"Error in socket server: {e}")
            time.sleep(1)

def main():
    message_queue = MessageQueue()
    audio_player = AudioPlayer()
    display_manager = DisplayManager()
    
    handler_thread = threading.Thread(
        target=message_handler,
        args=(message_queue, audio_player, display_manager),
        daemon=True
    )
    handler_thread.start()

    socket_thread = threading.Thread(
        target=socket_server,
        args=(message_queue,),
        daemon=True
    )
    socket_thread.start()

    app.run(host='0.0.0.0', port=web_port, threaded=True)

if __name__ == "__main__":
    main()
