#!/usr/bin/env python3
"""
Serial Plotter with Smooth Plotting
Reads data from serial port and plots with smoothing and cubic spline interpolation
"""

import serial
import serial.tools.list_ports
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.interpolate import interp1d
from collections import deque
from statistics import mean
import re

# Configuration
BAUDRATE = 115200
MAX_POINTS = 250
UPDATE_INTERVAL = 40  # milliseconds (25 FPS)
VALUE_MIN = -10000
VALUE_MAX = 2000000

# Kilogram conversion formula: kg ≈ (raw − 400000) / 18571
KG_OFFSET = 400000
KG_DIVISOR = 18571

# Global serial connection
ser = None

# Statistics
count = 0
start = time.time()
latest_reading = 0

# Data storage for plotting
data_queue = deque(maxlen=MAX_POINTS)
kg_queue = deque(maxlen=MAX_POINTS)
sample_buffer = []
plot_stats = {'min': float('inf'), 'max': float('-inf'), 'count': 0, 'sum': 0}
kg_stats = {'min': float('inf'), 'max': float('-inf'), 'count': 0, 'sum': 0}

# Serial stats
serial_stats = {'rate': 0, 'total': 0}
last_log = start
count_last = 0

def find_esp32_port():
    """Automatically find ESP32 serial port on Mac"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # ESP32 typically shows up as cu.usbserial or cu.SLAB_USBtoUART
        if 'usbserial' in port.device or 'SLAB' in port.device or 'USB' in port.device:
            print(f"Found potential ESP32 port: {port.device}")
            return port.device
    return None

def parse_value(line):
    """Extract numeric value from serial line"""
    # Try to find a number in the line (handles various formats)
    # Look for integers or floats
    numbers = re.findall(r'-?\d+\.?\d*', line)
    if numbers:
        try:
            value = float(numbers[-1])  # Take the last number found
            return value
        except ValueError:
            pass
    return None

def raw_to_kg(raw_value):
    """Convert raw sensor value to kilograms"""
    return (raw_value - KG_OFFSET) / KG_DIVISOR

def init_serial(port=None, baudrate=115200):
    """Initialize serial connection"""
    global ser
    
    # Auto-detect port if not specified
    if port is None:
        port = find_esp32_port()
        if port is None:
            print("\nAvailable ports:")
            for p in serial.tools.list_ports.comports():
                print(f"  {p.device} - {p.description}")
            return None
    
    try:
        ser = serial.Serial(port, baudrate, timeout=0.01)
        print(f"Connected to {port} at {baudrate} baud")
        return ser
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return None

print(f"\n{'='*50}")
print(f"Serial Smooth Plotter - HX711 Data")
print(f"{'='*50}")
print(f"Y-axis range: {VALUE_MIN} - {VALUE_MAX}")
print(f"Display window: {MAX_POINTS} samples @ 25 FPS")
print("Smoothing: Averaging all samples per frame")
print("Interpolation: Cubic spline for silky smooth curve")
print("Press Ctrl+C or close window to stop")
print(f"{'='*50}\n")

# Initialize serial connection
ser = init_serial()
if ser is None:
    print("Failed to open serial port. Exiting.")
    exit(1)

# Create figure and axis with dual y-axis
fig, ax1 = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor('#1e1e1e')
ax1.set_facecolor('#2d2d2d')

# Left y-axis for raw values
line1, = ax1.plot([], [], linewidth=2.5, color='#4ECDC4', label='Raw Value (Smoothed)')
ax1.set_xlim(0, MAX_POINTS)
ax1.set_ylim(VALUE_MIN, VALUE_MAX)
ax1.set_xlabel('Sample Number', fontsize=12, color='white', weight='bold')
ax1.set_ylabel('Raw Value', fontsize=12, color='#4ECDC4', weight='bold')
ax1.set_title('Serial Smooth Plotter - HX711 Data @ 25 FPS', 
             fontsize=14, color='white', weight='bold', pad=15)
ax1.grid(True, alpha=0.3, linestyle='--', color='white')
ax1.tick_params(colors='white', labelsize=10)

# Right y-axis for kg values
ax2 = ax1.twinx()
line2, = ax2.plot([], [], linewidth=2.5, color='#FF6B6B', label='Weight (kg)', alpha=0.7)
kg_min = raw_to_kg(VALUE_MIN)
kg_max = raw_to_kg(VALUE_MAX)
ax2.set_ylim(kg_min, kg_max)
ax2.set_ylabel('Weight (kg)', fontsize=12, color='#FF6B6B', weight='bold')
ax2.tick_params(colors='#FF6B6B', labelsize=10)

for spine in ax1.spines.values():
    spine.set_color('white')
    spine.set_linewidth(1.5)

for spine in ax2.spines.values():
    spine.set_color('#FF6B6B')
    spine.set_linewidth(1.5)

# Stats text box
stats_text = ax1.text(0.02, 0.98, '', transform=ax1.transAxes,
                    fontsize=9, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='#2d2d2d', 
                             edgecolor='white', alpha=0.9),
                    color='white', family='monospace')

# Combine legends from both axes
lines = [line1, line2]
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper right', fontsize=10, framealpha=0.9,
         facecolor='#2d2d2d', edgecolor='white')

# Animation update function
def update(frame):
    global count, latest_reading, last_log, count_last, serial_stats, ser
    global kg_stats
    
    if ser is None or not ser.is_open:
        return
    
    # Read all available serial data
    while ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                value = parse_value(line)
                if value is not None:
                    latest_reading = value
                    count += 1
                    
                    # Add reading to sample buffer for plotting
                    if VALUE_MIN <= value <= VALUE_MAX:
                        sample_buffer.append(float(value))
        except (UnicodeDecodeError, serial.SerialException):
            continue
    
    # Update serial stats once per second
    now = time.time()
    if now - last_log >= 1.0:
        dt = now - last_log
        pkt_delta = count - count_last
        rate = pkt_delta / dt if dt > 0 else 0.0
        
        serial_stats = {
            'rate': rate,
            'total': count
        }
        last_log = now
        count_last = count
    
    # Average buffered samples and add smoothed point to plot
    if len(sample_buffer) > 0:
        smoothed_value = sum(sample_buffer) / len(sample_buffer)
        smoothed_kg = raw_to_kg(smoothed_value)
        data_queue.append(smoothed_value)
        kg_queue.append(smoothed_kg)
        
        # Update statistics for raw values
        plot_stats['count'] += 1
        plot_stats['sum'] += smoothed_value
        plot_stats['min'] = min(plot_stats['min'], smoothed_value)
        plot_stats['max'] = max(plot_stats['max'], smoothed_value)
        
        # Update statistics for kg values
        kg_stats['count'] += 1
        kg_stats['sum'] += smoothed_kg
        kg_stats['min'] = min(kg_stats['min'], smoothed_kg)
        kg_stats['max'] = max(kg_stats['max'], smoothed_kg)
        
        sample_buffer.clear()
    
    # Update plot with interpolation
    if len(data_queue) > 0:
        x_data = np.array(range(len(data_queue)))
        y_data = np.array(list(data_queue))
        y_kg_data = np.array(list(kg_queue))
        
        if len(data_queue) >= 4:
            # Interpolate raw values
            f1 = interp1d(x_data, y_data, kind='cubic', 
                        bounds_error=False, fill_value='extrapolate')
            x_smooth = np.linspace(x_data[0], x_data[-1], len(data_queue) * 5)
            y_smooth = f1(x_smooth)
            y_smooth = np.clip(y_smooth, VALUE_MIN, VALUE_MAX)
            line1.set_data(x_smooth, y_smooth)
            
            # Interpolate kg values
            f2 = interp1d(x_data, y_kg_data, kind='cubic', 
                        bounds_error=False, fill_value='extrapolate')
            y_kg_smooth = f2(x_smooth)
            y_kg_smooth = np.clip(y_kg_smooth, kg_min, kg_max)
            line2.set_data(x_smooth, y_kg_smooth)
        else:
            line1.set_data(x_data, y_data)
            line2.set_data(x_data, y_kg_data)
        
        # Update stats text
        if plot_stats['count'] > 0:
            avg_raw = plot_stats['sum'] / plot_stats['count']
            avg_kg = kg_stats['sum'] / kg_stats['count']
            current_raw = data_queue[-1]
            current_kg = kg_queue[-1]
            stats_str = (f"Raw Value:\n"
                       f"  Current: {current_raw:.0f}\n"
                       f"  Average: {avg_raw:.0f}\n"
                       f"  Min: {plot_stats['min']:.0f}\n"
                       f"  Max: {plot_stats['max']:.0f}\n"
                       f"\nWeight (kg):\n"
                       f"  Current: {current_kg:.3f} kg\n"
                       f"  Average: {avg_kg:.3f} kg\n"
                       f"  Min: {kg_stats['min']:.3f} kg\n"
                       f"  Max: {kg_stats['max']:.3f} kg\n"
                       f"\n--- Serial Stats ---\n"
                       f"Rate: {serial_stats['rate']:.1f} samples/s\n"
                       f"Total: {serial_stats['total']}")
            stats_text.set_text(stats_str)

# Handle window close
def on_close(event):
    global ser
    print("\n✓ Closing serial port...")
    if ser is not None and ser.is_open:
        ser.close()
    print("✓ Stopped")

fig.canvas.mpl_connect('close_event', on_close)

# Create animation
anim = FuncAnimation(fig, update, interval=UPDATE_INTERVAL, blit=False, cache_frame_data=False)

try:
    plt.tight_layout()
    plt.show()
except KeyboardInterrupt:
    print("\n✓ Interrupted by user")
finally:
    if ser is not None and ser.is_open:
        ser.close()
    dur = time.time() - start
    print("\n=== Summary ===")
    print(f"Samples: {count}")
    print(f"Duration: {dur:.1f} seconds")
    if dur > 0:
        print(f"Average rate: {count/dur:.1f} samples/s")
    print("✓ Serial port closed")

