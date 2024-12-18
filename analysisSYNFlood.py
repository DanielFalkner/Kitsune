import pandas as pd
import matplotlib.pyplot as plt

# 1. Lade die Kitsune-Ergebnisse
results = pd.read_csv("syn_flood_results.csv")  # Datei von Kitsune
print(f"Ergebnisse geladen: {len(results)} Pakete")

# 2. Lade die pcap-Daten
pcap_data = pd.read_csv("packets.csv", encoding="latin1")

# SYN-Flood-Pakete dynamisch erkennen (nur SYN, kein ACK)
syn_flood_packets = pcap_data[
    (pcap_data["Protocol"] == "TCP") &                  # TCP-Pakete
    (pcap_data["Info"].str.contains("SYN")) &           # SYN-Flag ist gesetzt
    (~pcap_data["Info"].str.contains("ACK"))            # ACK-Flag ist nicht gesetzt
]

# Extrahiere die Paketindizes der SYN-Flood-Pakete
syn_flood_indices = syn_flood_packets.index
print(f"Anzahl erkannter SYN-Flood-Pakete: {len(syn_flood_indices)}")

# 3. Dynamischen Schwellenwert berechnen
mean_rmse = results["RMSE"].mean()  # Durchschnittlicher RMSE-Wert
std_rmse = results["RMSE"].std()    # Standardabweichung der RMSE-Werte

# Dynamischer Schwellenwert: Mittelwert + 2 * Standardabweichung
threshold = mean_rmse + 2 * std_rmse
print(f"Dynamischer Schwellenwert (Mean + 2*Std): {threshold:.2f}")

# 4. Visualisierung der RMSE-Werte und SYN-Flood-Pakete
plt.figure(figsize=(10, 6))

# Plot der RMSE-Werte
plt.plot(results.index, results["RMSE"], label="RMSE-Werte", alpha=0.7)

# Anomalien basierend auf Schwellenwert
anomalous_indices = results[results["RMSE"] > threshold].index
plt.scatter(anomalous_indices, results.loc[anomalous_indices, "RMSE"],
            color="red", label="Anomalien")

# SYN-Flood-Pakete hervorheben
plt.scatter(syn_flood_indices, results.loc[syn_flood_indices, "RMSE"],
            color="orange", label="SYN-Flood-Pakete")

# Schwellenwert markieren
plt.axhline(y=threshold, color="r", linestyle="--", label=f"Schwellenwert: {threshold:.2f}")

# Diagrammtitel und Beschriftung
plt.title("RMSE-Werte mit SYN-Flood-Anomalien")
plt.xlabel("Paketindex")
plt.ylabel("RMSE-Wert")
plt.legend()
plt.show()

