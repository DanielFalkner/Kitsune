import pandas as pd
import matplotlib.pyplot as plt

# Schritt 1: RMSE-Ergebnisse laden
rmse_data = pd.read_csv("rmse_results.csv", encoding="latin1")

# Schritt 2: PCAP-Daten aus Wireshark laden
pcap_data = pd.read_csv("packets.csv", encoding="latin1")

# Überprüfen der ersten Zeilen zur Kontrolle
print("RMSE-Daten Vorschau:")
print(rmse_data.head())

print("PCAP-Daten Vorschau:")
print(pcap_data.head())

# Schritt 3: Verknüpfen der beiden Dateien
# Prüfe, ob die Spalte 'PacketIndex' existiert und verknüpfe RMSE-Werte
if 'PacketIndex' not in rmse_data.columns:
    print("Fehler: 'PacketIndex' fehlt in rmse_results.csv")
else:
    pcap_data["RMSE"] = rmse_data["RMSE"]
    pcap_data["IsAnomalous"] = rmse_data["IsAnomalous"]

# Speichere die kombinierte Datei
pcap_data.to_csv("annotated_packets.csv", index=False)
print("Datei 'annotated_packets.csv' erfolgreich erstellt!")

# Schritt 4: Anomalien analysieren
# Pakete, die als Anomalien markiert wurden
anomalies = pcap_data[pcap_data["IsAnomalous"] == 1]
print(f"Anzahl erkannter Anomalien: {len(anomalies)}")
print(anomalies.head())

# Schritt 5: Visualisierung der Anomalien
print("Visualisierung der Anomalien...")
plt.figure(figsize=(10, 6))
plt.plot(pcap_data.index, pcap_data["RMSE"], label="RMSE-Wert", alpha=0.7)
plt.scatter(pcap_data[pcap_data["IsAnomalous"] == 1].index,
            pcap_data[pcap_data["IsAnomalous"] == 1]["RMSE"],
            color="red", label="Anomalien")
plt.axhline(y=rmse_data["RMSE"].quantile(0.95), color="r", linestyle="--", label="Schwellenwert (95. Perzentil)")
plt.xlabel("Paketindex")
plt.ylabel("RMSE-Wert")
plt.title("Erkannte Anomalien im Netzwerkverkehr")
plt.legend()
plt.show()

# Schritt 6: Exportiere nur die Anomalien in eine neue Datei
anomalies.to_csv("anomalous_packets.csv", index=False)
print("Anomalien wurden in 'anomalous_packets.csv' gespeichert.")


