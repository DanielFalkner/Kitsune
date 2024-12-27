import pandas as pd
import matplotlib.pyplot as plt

# Loading Kitsune-Results
results = pd.read_csv("syn_flood_results.csv")  # Datei von Kitsune
print(f"Ergebnisse geladen: {len(results)} Pakete")

# Loading die pcap-Data
pcap_data = pd.read_csv("packets.csv", encoding="latin1")

# SYN-Flood-Pakete dynamisch erkennen (nur SYN, kein ACK)
syn_flood_packets = pcap_data[
    (pcap_data["Protocol"] == "TCP") &                  # TCP-Pakete
    (pcap_data["Info"].str.contains("SYN")) &           # SYN-Flag ist gesetzt
    (~pcap_data["Info"].str.contains("ACK"))            # ACK-Flag ist nicht gesetzt
]

# Extracting the Packet Indices of the SYN-Flood
syn_flood_indices = syn_flood_packets.index
print(f"Anzahl erkannter SYN-Flood-Pakete: {len(syn_flood_indices)}")

# Dynamischen Schwellenwert berechnen
mean_rmse = results["RMSE"].mean()  # Durchschnittlicher RMSE-Wert
std_rmse = results["RMSE"].std()    # Standardabweichung der RMSE-Werte

# Dynamischer Schwellenwert: Mittelwert + 2 * Standardabweichung
threshold = mean_rmse + 2 * std_rmse
print(f"Dynamischer Schwellenwert (Mean + 2*Std): {threshold:.2f}")

# Visualising
plt.figure(figsize=(10, 6))

# Plot of the RMSE-Values
plt.plot(results.index, results["RMSE"], label="RMSE-Werte", alpha=0.7)

# Anomalies based on the Threshold
anomalous_indices = results[results["RMSE"] > threshold].index
plt.scatter(anomalous_indices, results.loc[anomalous_indices, "RMSE"],
            color="red", label="Anomaly")

# highlighting SYN-Flood-Packets
plt.scatter(syn_flood_indices, results.loc[syn_flood_indices, "RMSE"],
            color="orange", label="SYN-Flood-Packets")

# Marking the Threshold
plt.axhline(y=threshold, color="r", linestyle="--", label=f"Threshold: {threshold:.2f}")

# Beschriftung
plt.title("RMSE-Values with SYN-Flood-Anomalies")
plt.xlabel("Packet Indices")
plt.ylabel("RMSE-Values")
plt.legend()
plt.show()

