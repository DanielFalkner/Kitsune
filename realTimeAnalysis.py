import numpy as np
from scapy.all import sniff, IP, IPv6, ARP, ICMP, TCP, UDP
from Kitsune import Kitsune
from thresholdCalculator import ThresholdCalculator
from edgeDevice import EdgeDevice
import threading
import subprocess

sending_started = False


def main():
    # Parameter für Kitsune
    path = "real_time"  # Echtzeitmodus
    packet_limit = np.inf  # Keine Begrenzung der Pakete
    #NUR AUS TESTZWECKEN FÜR DIE WEIGHT AGGREGATION SO NIEDRIG
    FM_grace = 10  # Anzahl Pakete für Feature Mapping Grace Period
    AD_grace = 100  # Anzahl Pakete für Anomaly Detection Grace Period
    max_autoencoder_size = 10  # Maximale Größe des Autoencoders

    # interface = "WLAN"  # Netzwerkschnittstelle vom Host Laptop
    # interface = "enp0s3"  # Netzwerkschnittstelle von der VM
    interface = "wlan0"  # Netzwerkschnittstelle vom Raspberry Pi
    threshold_calculator = ThresholdCalculator(FM_grace + AD_grace)
    target_ip = get_host_ip()  # IP-Adresse des Zielhosts
    target_ipv6 = get_host_ipv6()  # IPv6-Adresse des Zielhosts
    print(f"IP-Adresse des Hosts: {target_ip}")
    kitsune = Kitsune(path, packet_limit, max_autoencoder_size, FM_grace, AD_grace)
    # EdgeDevice initialisieren und mit Kitsune verbinden
    edge_device = EdgeDevice(server_url="http://192.168.0.163:5000", kitsune_instance=kitsune)

    """
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
    """

    def handle_packet(packet):
        global sending_started
        """Verarbeitet empfangene Pakete, falls sie für das Edge Device bestimmt sind"""
        if packet is None:
            print("Kein Paket erhalten.")
            return

        try:
            dst_ip = None
            protocol = "Unknown"

            # IPv4- oder IPv6-Adresse ermitteln
            if packet.haslayer(IP):
                dst_ip = packet[IP].dst
                protocol = "IPv4"
            elif packet.haslayer(IPv6):
                dst_ip = packet[IPv6].dst
                protocol = "IPv6"

            # Falls kein IP-Header vorhanden → Paket ignorieren
            if not dst_ip:
                return

            # ARP-Pakete verarbeiten (diese haben keine IP-Adressen!)
            if packet.haslayer(ARP):
                if packet[ARP].pdst == target_ip or (target_ipv6 and packet[ARP].pdst == target_ipv6):
                    print(f"ARP-Paket für {packet[ARP].pdst} erhalten!")
                    kitsune.proc_next_packet(packet)
                return  # Andere ARP-Pakete ignorieren

            # ICMP-Pakete (z. B. Ping) verarbeiten
            if packet.haslayer(ICMP):
                if dst_ip == target_ip or (target_ipv6 and dst_ip == target_ipv6):
                    print(f"ICMP-Paket für {dst_ip} erhalten!")
                    kitsune.proc_next_packet(packet)
                return

            # TCP & UDP-Pakete erkennen
            dst_port = "N/A"
            if packet.haslayer(TCP):
                protocol = "TCP"
                dst_port = packet[TCP].dport
            elif packet.haslayer(UDP):
                protocol = "UDP"
                dst_port = packet[UDP].dport

            # Prüfen, ob das Paket wirklich für das Edge Device bestimmt ist
            if dst_ip == target_ip or (target_ipv6 and dst_ip == target_ipv6):
                print(f"{protocol}-Paket an {dst_ip}:{dst_port} erhalten!")
                rmse = kitsune.proc_next_packet(packet)

                if not sending_started and rmse is not None and rmse > 0.0:
                    print("[edgeDevice] Grace Period vorbei. Starte Sende-Thread.")
                    threading.Thread(target=edge_device.start_sending, daemon=True).start()
                    sending_started = True

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


# Funktion, um die IP-Adresse des Hosts zu erhalten
def get_host_ip():
    return subprocess.getoutput("hostname -I").split()[0]


# Funktion, um die IPv6-Adresse des Hosts zu erhalten
def get_host_ipv6():
    ipv6_addresses = subprocess.getoutput("ip -6 addr show scope global | grep inet6 | awk '{print $2}'").split()
    return ipv6_addresses[0] if ipv6_addresses else None  # Falls keine IPv6-Adresse existiert, None zurückgeben


if __name__ == "__main__":
    main()
