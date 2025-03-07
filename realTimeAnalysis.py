import numpy as np
import socket
from scapy.all import sniff
from Kitsune import Kitsune
from thresholdCalculator import ThresholdCalculator
from edgeDevice import EdgeDevice
import threading
import json


def main():
    # Parameter für Kitsune
    path = "real_time"  # Echtzeitmodus
    packet_limit = np.inf  # Keine Begrenzung der Pakete
    FM_grace = 500  # Anzahl Pakete für Feature Mapping Grace Period
    AD_grace = 5000  # Anzahl Pakete für Anomaly Detection Grace Period
    max_autoencoder_size = 10  # Maximale Größe des Autoencoders

    # interface = "WLAN"  # Netzwerkschnittstelle vom Host Laptop
    # interface = "enp0s3"  # Netzwerkschnittstelle von der VM
    interface = "wlan0"  # Netzwerkschnittstelle vom Raspberry Pi
    threshold_calculator = ThresholdCalculator(FM_grace + AD_grace)
    target_ip = get_host_ip()  # IP-Adresse des Zielhosts
    print(f"IP-Adresse des Hosts: {target_ip}")
    kitsune = Kitsune(path, packet_limit, max_autoencoder_size, FM_grace, AD_grace)
    # EdgeDevice initialisieren und mit Kitsune verbinden
    edge_device = EdgeDevice(server_url="http://127.0.0.1:5000", kitsune_instance=kitsune)
    # Das Senden der Gewichte im Hintergrund starten
    threading.Thread(target=edge_device.start_sending, daemon=True).start()

    def handle_packet(packet):
        if packet is None:
            print("Kein Paket erhalten.")
        else:
            print(f"Paket erhalten RTA: {packet.summary()}")
        try:
            # Proc_next_packet verarbeitet das nächste Paket
            rmse = kitsune.proc_next_packet(packet)
            if rmse is not None and rmse != -1:
                print(f"RMSE: {rmse}")
                threshold = threshold_calculator.handle_rmse(rmse)
                if threshold is not None and rmse > threshold:
                    print("Anomalie erkannt!")
            else:
                print("Kein RMSE-Wert verfügbar oder Grace Period aktiv.")
        except Exception as e:
            print(f"Fehler bei der Verarbeitung des Pakets: {e}")

    print(f"Starte die Überwachung des Netzwerkverkehrs auf {interface}...")

    # Starte das Sniffing
    sniff(iface=interface, prn=handle_packet, store=False)


def get_host_ip():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)


if __name__ == "__main__":
    main()
