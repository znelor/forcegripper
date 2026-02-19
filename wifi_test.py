#!/usr/bin/env python3
"""
UDP Receiver with Smooth Plotting
Receives HX711 data via UDP and plots with smoothing and cubic spline interpolation
"""

import socket
import struct
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.interpolate import interp1d
from collections import deque
from statistics import mean, pstdev

# Configuration
IP = "0.0.0.0"
PORT = 5005
PAYLOAD = 100
MAX_POINTS = 250
UPDATE_INTERVAL = 40  # milliseconds (25 FPS)
VALUE_MIN = 0
VALUE_MAX = 2000000

# UDP socket setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((IP, PORT))
sock.settimeout(0.01)  # Short timeout for non-blocking behavior

# Statistics
count = 0
last_seq = None
lost = 0
latencies = []
start = time.time()
latest_reading = 0

# Clock alignment
offset_us = None
EWMA_ALPHA = 0.995

# Data storage for plotting
data_queue = deque(maxlen=MAX_POINTS)
sample_buffer = []
plot_stats = {'min': float('inf'), 'max': float('-inf'), 'count': 0, 'sum': 0}

# UDP stats
udp_stats = {'pkt_rate': 0, 'throughput': 0, 'avg_latency': 0, 'total': 0, 'lost': 0}
last_log = start
count_last = 0

print(f"\n{'='*50}")
print(f"UDP Smooth Plotter - HX711 Data")
print(f"{'='*50}")
print(f"Listening on UDP {IP}:{PORT}")
print(f"Y-axis range: {VALUE_MIN} - {VALUE_MAX}")
print(f"Display window: {MAX_POINTS} samples @ 25 FPS")
print("Smoothing: Averaging all samples per frame")
print("Interpolation: Cubic spline for silky smooth curve")
print("Press Ctrl+C or close window to stop")
print(f"{'='*50}\n")

# Create figure and axis
fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor('#1e1e1e')
ax.set_facecolor('#2d2d2d')

line, = ax.plot([], [], linewidth=2.5, color='#4ECDC4', label='Smoothed & Interpolated')
ax.set_xlim(0, MAX_POINTS)
ax.set_ylim(VALUE_MIN, VALUE_MAX)
ax.set_xlabel('Sample Number', fontsize=12, color='white', weight='bold')
ax.set_ylabel('Value', fontsize=12, color='white', weight='bold')
ax.set_title('UDP Smooth Plotter - HX711 Data @ 25 FPS', 
             fontsize=14, color='white', weight='bold', pad=15)
ax.grid(True, alpha=0.3, linestyle='--', color='white')
ax.tick_params(colors='white', labelsize=10)

for spine in ax.spines.values():
    spine.set_color('white')
    spine.set_linewidth(1.5)

# Stats text box
stats_text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                    fontsize=9, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='#2d2d2d', 
                             edgecolor='white', alpha=0.9),
                    color='white', family='monospace')

ax.legend(loc='upper right', fontsize=10, framealpha=0.9,
         facecolor='#2d2d2d', edgecolor='white')

# Animation update function
def update(frame):
    global count, last_seq, lost, latencies, latest_reading, offset_us
    global last_log, count_last, udp_stats
    
    # Read all available UDP packets
    packets_read = 0
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            packets_read += 1
        except (socket.timeout, BlockingIOError, OSError):
            break
        
        now_us = time.time() * 1e6
        if len(data) != PAYLOAD:
            continue

        seq, sent_us, reading = struct.unpack_from("<IIi", data, 0)

        # Loss tracking
        if last_seq is not None and seq != last_seq + 1:
            lost += (seq - last_seq - 1)
        last_seq = seq

        # Establish/track clock offset
        if offset_us is None:
            offset_us = now_us - sent_us
        else:
            measured = now_us - sent_us
            offset_us = EWMA_ALPHA * offset_us + (1 - EWMA_ALPHA) * measured

        # One-way latency estimate (ms)
        lat_ms = (now_us - sent_us - offset_us) / 1000.0
        if lat_ms < -5.0:
            lat_ms = 0.0
        latencies.append(lat_ms)
        latest_reading = reading
        count += 1
        
        # Add reading to sample buffer for plotting
        if VALUE_MIN <= reading <= VALUE_MAX:
            sample_buffer.append(float(reading))
    
    # Update UDP stats once per second
    now = time.time()
    if now - last_log >= 1.0:
        dt = now - last_log
        pkt_delta = count - count_last
        bytes_delta = pkt_delta * PAYLOAD
        throughput = bytes_delta / dt if dt > 0 else 0.0
        if pkt_delta > 0 and len(latencies) >= pkt_delta:
            avg_lat = mean(latencies[-pkt_delta:])
        else:
            avg_lat = 0.0
        
        udp_stats = {
            'pkt_rate': pkt_delta,
            'throughput': throughput,
            'avg_latency': avg_lat,
            'total': count,
            'lost': lost
        }
        last_log = now
        count_last = count
    
    # Average buffered samples and add smoothed point to plot
    if len(sample_buffer) > 0:
        smoothed_value = sum(sample_buffer) / len(sample_buffer)
        data_queue.append(smoothed_value)
        
        # Update statistics
        plot_stats['count'] += 1
        plot_stats['sum'] += smoothed_value
        plot_stats['min'] = min(plot_stats['min'], smoothed_value)
        plot_stats['max'] = max(plot_stats['max'], smoothed_value)
        
        sample_buffer.clear()
    
    # Update plot with interpolation
    if len(data_queue) > 0:
        x_data = np.array(range(len(data_queue)))
        y_data = np.array(list(data_queue))
        
        if len(data_queue) >= 4:
            f = interp1d(x_data, y_data, kind='cubic', 
                       bounds_error=False, fill_value='extrapolate')
            x_smooth = np.linspace(x_data[0], x_data[-1], len(data_queue) * 5)
            y_smooth = f(x_smooth)
            y_smooth = np.clip(y_smooth, VALUE_MIN, VALUE_MAX)
            line.set_data(x_smooth, y_smooth)
        else:
            line.set_data(x_data, y_data)
        
        # Update stats text
        if plot_stats['count'] > 0:
            avg = plot_stats['sum'] / plot_stats['count']
            current_val = data_queue[-1]
            stats_str = (f"Current: {current_val:.2f}\n"
                       f"Average: {avg:.2f}\n"
                       f"Min: {plot_stats['min']:.2f}\n"
                       f"Max: {plot_stats['max']:.2f}\n"
                       f"Samples: {plot_stats['count']}\n"
                       f"--- UDP Stats ---\n"
                       f"Rate: {udp_stats['pkt_rate']} pkt/s\n"
                       f"Lost: {udp_stats['lost']}\n"
                       f"Latency: {udp_stats['avg_latency']:.2f} ms")
            stats_text.set_text(stats_str)

# Handle window close
def on_close(event):
    print("\n✓ Closing UDP socket...")
    sock.close()
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
    sock.close()
    dur = time.time() - start
    throughput = (count * PAYLOAD / dur) if dur > 0 else 0.0
    print("\n=== Summary ===")
    print(f"Packets: {count}, Lost: {lost}")
    print(f"Throughput: {throughput:.1f} B/s ({throughput/1024:.2f} KiB/s)")
    if latencies:
        print(f"Latency ms: mean={mean(latencies):.2f}, sd={pstdev(latencies):.2f}, "
              f"min={min(latencies):.2f}, max={max(latencies):.2f}")
    print("✓ UDP socket closed")
