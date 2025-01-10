from Kitsune import Kitsune
import numpy as np
import time
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import os
import pickle

# Load Mirai pcap (a recording of the Mirai botnet malware being activated)
# The first 70,000 observations are clean...
print("Unzipping Sample Capture...")
import zipfile

with zipfile.ZipFile("mirai.zip", "r") as zip_ref:
    zip_ref.extractall()

# File location
path = "mirai.tsv"  # the pcap, pcapng, or tsv file to process.
# path = "network_traffic.pcap"
packet_limit = np.inf  # the number of packets to process

# KitNET params:
maxAE = 10  # maximum size for any autoencoder in the ensemble layer
FMgrace = 5000  # the number of instances taken to learn the feature mapping (the ensemble's architecture)
ADgrace = 50000  # the number of instances used to train the anomaly detector (ensemble itself)

# Build Kitsune
K = Kitsune(path, packet_limit, maxAE, FMgrace, ADgrace)

# Caching RMSE Values
rmse_cache_file = "rmse_cache.pkl"  # File for RMSE Values

if os.path.exists(rmse_cache_file):
    print("Loading RMSE-Values from Cache...")
    with open(rmse_cache_file, "rb") as f:
        RMSEs = pickle.load(f)
    print(f"Loaded RMSE-Values: {len(RMSEs)}")
else:
    print("Starting Kitsune and calculate RMSE-Values...")
    RMSEs = []
    start_time = time.time()
    i = 0
    while True:
        if i % 1000 == 0:
            print(f"Packets: {i}")
        rmse = K.proc_next_packet()
        if rmse == -1:
            break
        RMSEs.append(rmse)
        i += 1
    end_time = time.time()
    print(f"Finished RMSE Calculation in {end_time - start_time:.2f} Seconds.")

    print("Saving RMSE-Values in Cache...")
    with open(rmse_cache_file, "wb") as f:
        pickle.dump(RMSEs, f)
"""

print("Starting Kitsune and calculate RMSE-Values...")
RMSEs = []
start_time = time.time()
i = 0
while True:
    if i % 1000 == 0:
        print(f"Packets: {i}")
    rmse = K.proc_next_packet()
    if rmse == -1:
        break
    RMSEs.append(rmse)
    i += 1
end_time = time.time()
print(f"Finished RMSE Calculation in {end_time - start_time:.2f} Seconds.")
"""

mean_rmse = np.mean(RMSEs)
std_rmse = np.std(RMSEs)
threshold = mean_rmse + 2 * std_rmse  # Vorübergehend dynamisch berechneter Schwellenwert
threshold = 1
print(f"Dynamic Threshold: {threshold:.2f}")

# Analysis: Recognizing Anomalies
results = pd.DataFrame({"PacketIndex": range(len(RMSEs)), "RMSE": RMSEs})
results["IsAnomalous"] = results["RMSE"] > threshold
print(f"Anomalien erkannt: {results['IsAnomalous'].sum()} von {len(results)} Paketen")

results.to_csv("RMSE_results.csv", index=False)
print("Ergebnisse in 'RMSE_results.csv' gespeichert.")

# RMSE scores to a log-normal distribution (useful for finding/setting a cutoff threshold \phi)
from scipy.stats import norm

benignSample = np.log(RMSEs[FMgrace + ADgrace + 1:100000])
logProbs = norm.logsf(np.log(RMSEs), np.mean(benignSample), np.std(benignSample))

# Visualising
plt.figure(figsize=(10, 6))
plt.plot(results["PacketIndex"], results["RMSE"], label="RMSE-Werte")
plt.axhline(y=threshold, color="r", linestyle="--", label=f"Threshold: {threshold:.2f}")
plt.scatter(results[results["IsAnomalous"] == 1]["PacketIndex"],
            results[results["IsAnomalous"] == 1]["RMSE"],
            color="red", label="Anomalies")
plt.title("RMSE-Values and recognized Anomalies (SYN-Flood)")
plt.xlabel("Packet Index")
plt.ylabel("RMSE-Value")
plt.legend()
plt.show()
