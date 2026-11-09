import os
import glob
import csv
import numpy as np
import matplotlib.pyplot as plt

plt.style.use("seaborn-v0_8-whitegrid")  # Alternatives: "ggplot", "fivethirtyeight"
#plt.style.use("ggplot")

# Ordner definieren (aktuellstes Tagesverzeichnis verwenden)
base_dir = os.getcwd()
date_folders = sorted([f for f in os.listdir(base_dir) if os.path.isdir(f) and f[:4].isdigit()], reverse=True)
if not date_folders:
    raise FileNotFoundError("Kein Datumsordner gefunden.")
data_dir = date_folders[0]  # z. B. '2025-05-29'

# CSV-Dateien finden
hr_files = sorted(glob.glob(os.path.join(data_dir, "hr_data_*.csv")))
rr_files = sorted(glob.glob(os.path.join(data_dir, "rr_data_*.csv")))
combined_files = sorted(glob.glob(os.path.join(data_dir, "combined_data_*.csv")))

# Initialisierung
all_hr = []
all_rr = []
all_combined = []

# Ladefunktion
def load_csv_data(files, columns):
    data = []
    for file in files:
        with open(file) as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                try:
                    parsed = [float(x) if x else np.nan for x in row[:columns]]
                    data.append(parsed)
                except ValueError:
                    continue
    return data

# Daten laden
all_hr = load_csv_data(hr_files, 2)
all_rr = load_csv_data(rr_files, 2)
all_combined = load_csv_data(combined_files, 6)

# Plot
fig, axs = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
fig.suptitle("Alle Messungen: HR, RR, HRV", fontsize=18)

# Herzfrequenz
if all_hr:
    x_hr, y_hr = zip(*all_hr)
    axs[0].plot(x_hr, y_hr, color="tab:blue", label="HR (bpm)")
    axs[0].set_ylabel("Herzfrequenz")
    axs[0].legend()
    axs[0].grid(True)

# RR
if all_rr:
    x_rr, y_rr = zip(*all_rr)
    axs[1].plot(x_rr, y_rr, color="tab:orange", label="RR (ms)")
    axs[1].set_ylabel("RR Intervall")
    axs[1].legend()
    axs[1].grid(True)

# HRV-Metriken
if all_combined:
    x_comb, hr, rr, rmssd, sdnn, pnn50 = zip(*all_combined)
    axs[2].plot(x_comb, rmssd, label="RMSSD", color="green")
    axs[2].plot(x_comb, sdnn, label="SDNN", color="purple")
    axs[2].plot(x_comb, pnn50, label="pNN50", color="red")
    axs[2].set_ylabel("HRV")
    axs[2].set_xlabel("Zeit (s)")
    axs[2].legend()
    axs[2].grid(True)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# HR Histogram
if all_hr:
    hr_values = [v for _, v in all_hr if not np.isnan(v)]

    plt.figure(figsize=(10, 5))
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.hist(hr_values, bins=30, color="#007ACC", edgecolor="black", alpha=0.85)
    plt.title("Histogramm der Herzfrequenz", fontsize=16, fontweight='bold')
    plt.xlabel("Herzfrequenz (bpm)", fontsize=12)
    plt.ylabel("Anzahl", fontsize=12)
    plt.grid(True, which='major', linestyle='--', linewidth=0.5)
    plt.tight_layout()

    for zone in [94, 113, 132, 150, 169]:
        plt.axvline(zone, color='gray', linestyle='--', linewidth=1)

    plt.show()

# RR Histogramm
if all_rr:
    rr_values = [v for _, v in all_rr if not np.isnan(v)]

    plt.figure(figsize=(10, 5))
    plt.hist(rr_values, bins=30, color="tab:orange", edgecolor="black", alpha=0.85)
    plt.title("Histogramm der RR-Intervalle", fontsize=16, fontweight='bold')
    plt.xlabel("RR-Intervall (ms)", fontsize=12)
    plt.ylabel("Anzahl", fontsize=12)
    plt.grid(True, which='major', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.show()

# Time-in-Zone Balkendiagramm (für Herzfrequenzbereiche)
if all_hr:
    hr_zones = [94, 113, 132, 150, 169, 188]  # Grenzen (z.B. Z0: <94, Z1: 94–113, ...)
    zone_labels = ["<94", "94–113", "113–132", "132–150", "150–169", "169–188", ">188"]
    zone_durations = [0] * len(zone_labels)

    # Zeitdifferenzen berechnen
    for i in range(1, len(all_hr)):
        t_prev, hr_prev = all_hr[i - 1]
        t_curr, hr_curr = all_hr[i]
        dt = t_curr - t_prev

        # Verwende den vorherigen HR-Wert
        hr_val = hr_prev
        zone_index = 0
        while zone_index < len(hr_zones) and hr_val > hr_zones[zone_index]:
            zone_index += 1
        zone_durations[zone_index] += dt

    # Bar Chart
    plt.figure(figsize=(10, 5))
    bars = plt.bar(zone_labels, zone_durations, color="steelblue", edgecolor="black", alpha=0.85)
    plt.title("Time-in-Zone Analyse (Herzfrequenz)", fontsize=16, fontweight='bold')
    plt.xlabel("Herzfrequenz-Zone", fontsize=12)
    plt.ylabel("Dauer (s)", fontsize=12)
    plt.grid(True, axis='y', linestyle='--', linewidth=0.5)
    plt.tight_layout()

    # Dauer beschriften
    for bar, duration in zip(bars, zone_durations):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                 f"{int(duration)}s", ha='center', va='bottom', fontsize=10)

    plt.show()