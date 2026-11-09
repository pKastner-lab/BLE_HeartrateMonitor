import asyncio
import threading
import os
import datetime
import csv
from collections import deque

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from bleak import BleakClient, BleakError

# BLE Parameter
HRM_ADDRESS = "E8:AB:A6:10:75:AB"
HRM_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
terminate = False

# Datenordner erzeugen
now = datetime.datetime.now()
date_str = now.strftime("%Y-%m-%d")
time_str = now.strftime("%Y%m%d_%H%M%S")
data_dir = date_str
os.makedirs(data_dir, exist_ok=True)

hr_path = os.path.join(data_dir, f"hr_data_{time_str}.csv")
rr_path = os.path.join(data_dir, f"rr_data_{time_str}.csv")
combined_path = os.path.join(data_dir, f"combined_data_{time_str}.csv")

# BLE Handler
class BLEHandler:
    def __init__(self, queue_hr, queue_rr):
        self.queue_hr = queue_hr
        self.queue_rr = queue_rr
        self.last_data_time = datetime.datetime.now()

    def _notification_handler(self, _, data: bytearray):
        self.last_data_time = datetime.datetime.now()
        flags = data[0]
        hr_format = flags & 0x01
        rr_present = flags & 0x10

        index = 1
        if hr_format == 0 and len(data) > 1:
            hr = data[1]
            index = 2
        elif len(data) >= 3:
            hr = int.from_bytes(data[1:3], byteorder='little')
            index = 3
        else:
            hr = None

        if hr and 30 <= hr <= 220:
            asyncio.get_event_loop().call_soon_threadsafe(self.queue_hr.put_nowait, (datetime.datetime.now(), hr))

        if rr_present:
            while index + 1 < len(data):
                rr_raw = int.from_bytes(data[index:index+2], byteorder='little')
                rr_ms = rr_raw * 1000 / 1024
                asyncio.get_event_loop().call_soon_threadsafe(self.queue_rr.put_nowait, (datetime.datetime.now(), rr_ms))
                index += 2

    async def run(self):
        while not terminate:
            try:
                print(f"🔗 Verbinde mit {HRM_ADDRESS}...")
                async with BleakClient(HRM_ADDRESS) as client:
                    print("✅ Verbunden:", client.is_connected)
                    await client.start_notify(HRM_CHAR_UUID, self._notification_handler)
                    print("📡 HRM Notifications aktiv...")

                    while not terminate:
                        await asyncio.sleep(1)
                        now = datetime.datetime.now()
                        if (now - self.last_data_time).total_seconds() > 6:
                            print("⚠️ Kein Datenempfang >30s, versuche Reconnect...")
                            raise BleakError("Timeout")

                    await client.stop_notify(HRM_CHAR_UUID)
                    break
            except BleakError as e:
                print(f"❌ Verbindungsfehler: {e}, neuer Versuch in 5 Sekunden...")
                await asyncio.sleep(5)

# Plotter
class Plotter:
    def __init__(self, queue_hr, queue_rr):
        self.queue_hr = queue_hr
        self.queue_rr = queue_rr
        self.hr_data = []
        self.rr_data = []
        self.combined_data = []
        self.start_time = datetime.datetime.now()
        self.hr_file = open(hr_path, 'a', newline='')
        self.rr_file = open(rr_path, 'a', newline='')
        self.combined_file = open(combined_path, 'a', newline='')
        self.hr_writer = csv.writer(self.hr_file)
        self.rr_writer = csv.writer(self.rr_file)
        self.combined_writer = csv.writer(self.combined_file)
        self.hr_writer.writerow(["Time_s", "HR_bpm"])
        self.rr_writer.writerow(["Time_s", "RR_ms"])
        self.combined_writer.writerow(["Time_s", "HR_bpm", "RR_ms", "RMSSD", "SDNN", "pNN50"])

    def compute_hrv_metrics(self):
        rr_values = [val for _, val in self.rr_data[-60:]]
        if len(rr_values) < 2:
            return 0.0, 0.0, 0.0
        rr_diff = np.diff(rr_values)
        rmssd = np.sqrt(np.mean(rr_diff ** 2))
        sdnn = np.std(rr_values)
        nn50 = np.sum(np.abs(rr_diff) > 50)
        pnn50 = 100.0 * nn50 / len(rr_diff)
        return rmssd, sdnn, pnn50

    def detect_anomalies(self):
        self.anomaly_points = []
        rr_values = [val for _, val in self.rr_data]
        if len(rr_values) < 2:
            return
        diffs = np.abs(np.diff(rr_values))
        mean_diff = np.mean(diffs)
        threshold = mean_diff * 2
        for i in range(1, len(rr_values)):
            if abs(rr_values[i] - rr_values[i-1]) > threshold:
                self.anomaly_points.append(i)

    def run_plot(self):
        plt.style.use("seaborn-v0_8-darkgrid")
        fig, (ax_hr, ax_rr) = plt.subplots(
            2, 1,
            figsize=(12, 7),
            sharex=True,
            gridspec_kw={'height_ratios': [3, 1]}
        )
        fig.suptitle("Live Herzfrequenz & HRV", fontsize=16)

        hr_zones = [94, 113, 132, 150, 169, 188]
        colors = ['lightgray', 'lightblue', 'lightgreen', 'khaki', 'orange', 'lightcoral', 'crimson']
        lower = 77
        upper = 188
        upperBound = 130
        bounds = [lower] + hr_zones + [upper]
        for i in range(len(bounds) - 1):
            ax_hr.axhspan(bounds[i], bounds[i + 1], facecolor=colors[i], alpha=0.3)

        line_hr, = ax_hr.plot([], [], lw=4, label="Herzfrequenz", color="tab:blue")
        line_rr, = ax_rr.plot([], [], lw=2, label="RR-Intervall", color="tab:orange")
        scatter_rr = ax_rr.scatter([], [], color='red', s=30, label="Anomalie")

        ax_hr.set_ylim(lower, upperBound)
        ax_rr.set_ylim(300, 1500)
        ax_hr.set_ylabel("HR (bpm)", fontsize=12)
        ax_rr.set_ylabel("RR (ms)", fontsize=12)
        ax_rr.set_xlabel("Zeit (s)", fontsize=12)

        text_handle = ax_rr.text(0.98, 0.02, "", ha="right", va="bottom", transform=ax_rr.transAxes,
                                 fontsize=10, bbox=dict(boxstyle="round", facecolor="white", alpha=0.7))

        time_text = ax_hr.text(0.02, 0.95, "", ha="left", va="top", transform=ax_hr.transAxes,
                               fontsize=10, bbox=dict(boxstyle="round", facecolor="white", alpha=0.7))

        def update(_):
            now = datetime.datetime.now()
            t = (now - self.start_time).total_seconds()

            while not self.queue_hr.empty():
                ts, hr = self.queue_hr.get_nowait()
                dt = (ts - self.start_time).total_seconds()
                self.hr_data.append((dt, hr))
                self.hr_writer.writerow([dt, hr])
                self.hr_file.flush()

            while not self.queue_rr.empty():
                ts, rr = self.queue_rr.get_nowait()
                dt = (ts - self.start_time).total_seconds()
                self.rr_data.append((dt, rr))
                self.rr_writer.writerow([dt, rr])
                self.rr_file.flush()

            x_hr = [t for t, _ in self.hr_data]
            y_hr = [v for _, v in self.hr_data]
            x_rr = [t for t, _ in self.rr_data]
            y_rr = [v for _, v in self.rr_data]

            if x_hr:
                line_hr.set_data(x_hr, y_hr)
                ax_hr.set_xlim(max(0, x_hr[-1] - 180), x_hr[-1])
            if x_rr:
                line_rr.set_data(x_rr, y_rr)
                ax_rr.set_xlim(max(0, x_rr[-1] - 180), x_rr[-1])

            self.detect_anomalies()
            if self.anomaly_points:
                x_anomalies = [x_rr[i] for i in self.anomaly_points if i < len(x_rr)]
                y_anomalies = [y_rr[i] for i in self.anomaly_points if i < len(y_rr)]
                scatter_rr.set_offsets(np.column_stack((x_anomalies, y_anomalies)))
            else:
                scatter_rr.set_offsets(np.empty((0, 2)))

            rmssd, sdnn, pnn50 = self.compute_hrv_metrics()
            text_handle.set_text(f"RMSSD: {rmssd:.1f} ms\nSDNN: {sdnn:.1f} ms\npNN50: {pnn50:.1f} %")
            time_text.set_text(f"Dauer: {int(t)} s")

            self.combined_data.append((t, y_hr[-1] if y_hr else '', y_rr[-1] if y_rr else '', rmssd, sdnn, pnn50))
            self.combined_writer.writerow(self.combined_data[-1])
            self.combined_file.flush()
            return line_hr, line_rr, scatter_rr, text_handle, time_text

        ani = animation.FuncAnimation(fig, update, interval=500, blit=True)
        plt.tight_layout()
        plt.show()
        self.save_final_plot()

    def save_final_plot(self):
        plt.figure(figsize=(10, 4))
        x_rr = [t for t, _ in self.rr_data]
        y_rr = [v for _, v in self.rr_data]
        plt.plot(x_rr, y_rr, label="RR Intervall", color='tab:orange')
        for i in self.anomaly_points:
            if i < len(x_rr):
                plt.scatter(x_rr[i], y_rr[i], color='red', s=30)

        plt.xlabel("Zeit (s)")
        plt.ylabel("RR (ms)")
        plt.title("RR Intervall mit Anomalien")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(data_dir, f"rr_plot_with_anomalies_{time_str}.png"))
        print("🖼️ Plot gespeichert.")

    def close_files(self):
        self.hr_file.close()
        self.rr_file.close()
        self.combined_file.close()

# Benutzerabbruch

def user_input_thread():
    global terminate
    while True:
        if input().strip().lower() == 'c':
            terminate = True
            break

# Main
async def main():
    queue_hr = asyncio.Queue()
    queue_rr = asyncio.Queue()
    ble = BLEHandler(queue_hr, queue_rr)
    plotter = Plotter(queue_hr, queue_rr)

    t_plot = threading.Thread(target=plotter.run_plot, daemon=True)
    t_plot.start()

    t_input = threading.Thread(target=user_input_thread, daemon=True)
    t_input.start()

    await ble.run()
    plotter.close_files()

if __name__ == "__main__":
    asyncio.run(main())
