# Heart Rate Monitoring and Analysis

Python scripts in `Software/` for recording Bluetooth Low Energy (BLE) heart rate data and reviewing saved measurements.

## Contents

| File | Purpose |
| --- | --- |
| `Software/02_HRM.py` | Connects to a BLE heart rate monitor, displays live heart rate and RR intervals, marks RR anomalies, and records CSV data. Calculates RMSSD, SDNN, and pNN50 using the latest 60 RR intervals. |
| `Software/01_LoadAndPlot.py` | Loads all matching CSV files from the latest date folder and displays HR, RR, and HRV time series, HR/RR histograms, and time spent in heart rate zones. |

## Setup

Requires Python 3, a graphical desktop, and a Bluetooth adapter plus a compatible BLE heart rate monitor for live recording. RR-based metrics require a monitor that transmits RR intervals.

```bash
python -m pip install numpy matplotlib bleak
```

Set `HRM_ADDRESS` in `Software/02_HRM.py` to your monitor's BLE address or platform-specific identifier before recording.

## Usage

Run from the repository root so both scripts use the same data location:

```bash
# Record and view live measurements
python Software/02_HRM.py

# Review saved measurements
python Software/01_LoadAndPlot.py
```

Recording creates a `YYYY-MM-DD/` folder in the current working directory containing:

- `hr_data_<timestamp>.csv`: elapsed time (s) and heart rate (bpm).
- `rr_data_<timestamp>.csv`: elapsed time (s) and RR interval (ms).
- `combined_data_<timestamp>.csv`: elapsed time, latest HR/RR, RMSSD (ms), SDNN (ms), and pNN50 (%).

Close the live plot window to save `rr_plot_with_anomalies_<timestamp>.png`, then enter `c` and press Enter in the terminal to stop the BLE connection and close the CSV files.

The review script selects the latest date-named folder automatically; at least one such folder must exist. Close each plot window to advance through the figures. Heart rate zone thresholds and plot limits are hard-coded and can be adjusted in the scripts. For time-in-zone analysis, use a single recording per folder: elapsed times restart for each recording, while the review script concatenates files.
