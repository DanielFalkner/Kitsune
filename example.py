from Kitsune import Kitsune
import numpy as np
import time
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import os
import pickle

##############################################################################
# Kitsune a lightweight online network intrusion detection system based on an ensemble of autoencoders (kitNET).
# For more information and citation, please see our NDSS'18 paper: Kitsune: An Ensemble of Autoencoders for Online Network Intrusion Detection

# This script demonstrates Kitsune's ability to incrementally learn, and detect anomalies in recorded a pcap of the Mirai Malware.
# The demo involves an m-by-n dataset with n=115 dimensions (features), and m=100,000 observations.
# Each observation is a snapshot of the network's state in terms of incremental damped statistics (see the NDSS paper for more details)

#The runtimes presented in the paper, are based on the C++ implimentation (roughly 100x faster than the python implimentation)
###################  Last Tested with Anaconda 3.6.3   #######################

# Load Mirai pcap (a recording of the Mirai botnet malware being activated)
# The first 70,000 observations are clean...
print("Unzipping Sample Capture...")
import zipfile
with zipfile.ZipFile("mirai.zip","r") as zip_ref:
    zip_ref.extractall()


# File location
path = "mirai.tsv"  #the pcap, pcapng, or tsv file to process.
packet_limit = np.inf #the number of packets to process

# KitNET params:
maxAE = 10 #maximum size for any autoencoder in the ensemble layer
FMgrace = 5000 #the number of instances taken to learn the feature mapping (the ensemble's architecture)
ADgrace = 50000 #the number of instances used to train the anomaly detector (ensemble itself)

# Build Kitsune
K = Kitsune(path,packet_limit,maxAE,FMgrace,ADgrace)

# 3. SYN-Flood-Angriff parallel starten
print("Starte SYN-Flood-Angriff parallel...")
subprocess.Popen(["python", "syn_flood.py"])  # Angriff starten

# 3. RMSE-Werte zwischenspeichern (Caching)
rmse_cache_file = "rmse_cache.pkl"  # Datei für Zwischenspeicherung der RMSE-Werte


# Prüfen, ob Cache vorhanden ist
if os.path.exists(rmse_cache_file):
    print("Lade RMSE-Werte aus Cache...")
    with open(rmse_cache_file, "rb") as f:
        RMSEs = pickle.load(f)
    print(f"Geladene RMSE-Werte: {len(RMSEs)}")
else:
    print("Starte Kitsune und berechne RMSE-Werte...")
    RMSEs = []
    start_time = time.time()
    i = 0
    while True:
        if i % 1000 == 0:
            print(f"Verarbeite Paket {i}")
        rmse = K.proc_next_packet()
        if rmse == -1:
            break
        RMSEs.append(rmse)
        i += 1
    end_time = time.time()
    print(f"RMSE-Berechnung abgeschlossen in {end_time - start_time:.2f} Sekunden.")

    # RMSE-Werte speichern
    print("Speichere RMSE-Werte in Cache...")
    with open(rmse_cache_file, "wb") as f:
        pickle.dump(RMSEs, f)

"""
print("Running Kitsune:")
RMSEs = []
i = 0
start = time.time()
# Here we process (train/execute) each individual packet.
# In this way, each observation is discarded after performing process() method.
while True:
    i+=1
    if i % 1000 == 0:
        print(i)
    rmse = K.proc_next_packet()
    if rmse == -1:
        break
    RMSEs.append(rmse)
stop = time.time()
print("Complete. Time elapsed: "+ str(stop - start))
"""

mean_rmse = np.mean(RMSEs)
std_rmse = np.std(RMSEs)
threshold = mean_rmse + 2 * std_rmse  # Dynamischer Schwellenwert
print(f"Dynamischer Schwellenwert: {threshold:.2f}")

# 6. Analyse: Anomalien erkennen und speichern
results = pd.DataFrame({"PacketIndex": range(len(RMSEs)), "RMSE": RMSEs})
results["IsAnomalous"] = results["RMSE"] > threshold
print(f"Anomalien erkannt: {results['IsAnomalous'].sum()} von {len(results)} Paketen")

# Ergebnisse speichern
results.to_csv("syn_flood_results.csv", index=False)
print("Ergebnisse in 'syn_flood_results.csv' gespeichert.")

# Here we demonstrate how one can fit the RMSE scores to a log-normal distribution (useful for finding/setting a cutoff threshold \phi)
from scipy.stats import norm
benignSample = np.log(RMSEs[FMgrace+ADgrace+1:100000])
logProbs = norm.logsf(np.log(RMSEs), np.mean(benignSample), np.std(benignSample))

# 7. Visualisierung der RMSE-Werte und Anomalien
plt.figure(figsize=(10, 6))
plt.plot(results["PacketIndex"], results["RMSE"], label="RMSE-Werte")
plt.axhline(y=threshold, color="r", linestyle="--", label=f"Schwellenwert: {threshold:.2f}")
plt.scatter(results[results["IsAnomalous"] == 1]["PacketIndex"],
            results[results["IsAnomalous"] == 1]["RMSE"],
            color="red", label="Anomalien")
plt.title("RMSE-Werte und erkannte Anomalien (SYN-Flood)")
plt.xlabel("Paketindex")
plt.ylabel("RMSE-Wert")
plt.legend()
plt.show()
