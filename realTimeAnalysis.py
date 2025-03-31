import numpy as np
from scapy.all import sniff, IP, IPv6, ARP, ICMP, TCP, UDP
from Kitsune import Kitsune
from thresholdCalculator import ThresholdCalculator
from edgeDevice import EdgeDevice
import threading
import subprocess
import os
import time

sending_started = False  # Prevents sending weights before they are calculated
log_dir = os.path.join(os.path.dirname(__file__), "Logs")
os.makedirs(log_dir, exist_ok=True)


def main():
    # Kitsune-Parameter
    path = "real_time"
    packet_limit = np.inf
    # NUR AUS TESTZWECKEN FÜR DIE WEIGHT AGGREGATION SO NIEDRIG
    FM_grace = 10  # Packet number of Feature Mapping grace period (training phase 1)
    AD_grace = 100  # Packet number of Anomaly Detection grace period (training phase 2)
    max_autoencoder_size = 10

    # interface = "WLAN"  # Network interface name of Host Laptop
    # interface = "enp0s3"  # Network interface name of VM
    interface = "wlan0"  # Network interface name of Raspberry Pi
    threshold_calculator = ThresholdCalculator(FM_grace + AD_grace)
    target_ip = get_host_ip()
    target_ipv6 = get_host_ipv6()
    print(f"IP-Adresse des Hosts: {target_ip}")
    # Initialize Kitsune and EdgeDevice
    kitsune = Kitsune(path, packet_limit, max_autoencoder_size, FM_grace, AD_grace)
    edge_device = EdgeDevice(server_url="http://192.168.0.163:5000", kitsune_instance=kitsune)

    def handle_packet(packet):
        global sending_started
        if packet is None:
            print("Kein Paket erhalten.")
            return

        try:
            dst_ip = None
            protocol = "Unknown"

            # Detect destination IP address and protocol type
            if packet.haslayer(IP):
                dst_ip = packet[IP].dst
                protocol = "IPv4"
            elif packet.haslayer(IPv6):
                dst_ip = packet[IPv6].dst
                protocol = "IPv6"

            # Handle ARP requests to the device
            if packet.haslayer(ARP):
                if packet[ARP].pdst == target_ip or (target_ipv6 and packet[ARP].pdst == target_ipv6):
                    print(f"ARP-Paket für {packet[ARP].pdst} erhalten!")
                    kitsune.proc_next_packet(packet)
                return  # Andere ARP-Pakete ignorieren

            # Handle ICMP (e.g., ping)
            if packet.haslayer(ICMP):
                if dst_ip == target_ip or (target_ipv6 and dst_ip == target_ipv6):
                    print(f"ICMP-Paket für {dst_ip} erhalten!")
                    kitsune.proc_next_packet(packet)
                return

            # Determine transport-layer protocol
            dst_port = "N/A"
            if packet.haslayer(TCP):
                protocol = "TCP"
                dst_port = packet[TCP].dport
            elif packet.haslayer(UDP):
                protocol = "UDP"
                dst_port = packet[UDP].dport

            # Process packets destined for the local device
            if dst_ip == target_ip or (target_ipv6 and dst_ip == target_ipv6):
                print(f"{protocol}-Paket an {dst_ip}:{dst_port} erhalten!")
                rmse = kitsune.proc_next_packet(packet)

                if not sending_started and rmse is not None and rmse > 0.0:
                    print("[edgeDevice] Grace Period vorbei. Starte Sende-Thread.")
                    threading.Thread(target=edge_device.start_sending, daemon=True).start()
                    sending_started = True

                    # Logging
                    model_depth = len(kitsune.AnomDetector.ensembleLayer)
                    timestamp = time.time()
                    with open(f"{log_dir}/model_depth_log.csv", "a") as f:
                        f.write(f"{edge_device.device_id},{model_depth},{timestamp}\n")
                    print(f"[{edge_device.device_id}] Modell abgeschlossen mit {model_depth} Autoencoder-Schichten")

                if rmse is not None and rmse != -1:
                    print(f"RMSE: {rmse}")
                    timestamp = time.time()
                    threshold = threshold_calculator.handle_rmse(rmse)

                    # Logging
                    with open(f"{log_dir}/rmse_log_{edge_device.device_id}.csv", "a") as f:
                        is_anomaly = 1 if threshold and rmse > threshold else 0
                        f.write(f"{timestamp},{rmse:.6f},{threshold if threshold else -1},{is_anomaly}\n")

                    if threshold is not None and rmse > threshold:
                        print("Anomalie erkannt!")
                else:
                    print("Kein RMSE-Wert verfügbar oder Grace Period aktiv.")

            # Drop non-IP packets
            if not dst_ip:
                return
        except Exception as e:
            print(f"Fehler bei der Verarbeitung des Pakets: {e}")

    print(f"Starte die Überwachung des Netzwerkverkehrs auf {interface}...")

    # Starte das Sniffing
    sniff(iface=interface, prn=handle_packet, store=False)


# Extract the host's IPv4 address
def get_host_ip():
    return subprocess.getoutput("hostname -I").split()[0]


# Extract the host's global IPv6 address if available
def get_host_ipv6():
    ipv6_addresses = subprocess.getoutput("ip -6 addr show scope global | grep inet6 | awk '{print $2}'").split()
    return ipv6_addresses[0] if ipv6_addresses else None


if __name__ == "__main__":
    main()
