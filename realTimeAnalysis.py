import numpy as np
import requests
from scapy.all import sniff, IP, IPv6, ARP, ICMP, TCP, UDP

from Kitsune import Kitsune
from thresholdCalculator import ThresholdCalculator
from edgeDevice import EdgeDevice
import threading
import subprocess
import os
import time
import socket

sending_started = False  # Prevents sending weights before they are calculated
log_dir = os.path.join(os.path.dirname(__file__), "Logs")
os.makedirs(log_dir, exist_ok=True)

RUN_ID = os.environ.get("RUN_ID", "t1_noFL_5k_homog")
FL_ENABLED = int(os.environ.get("FL_ENABLED", "0"))
DEVICE_ID = socket.gethostname()

csv_path = os.path.join(log_dir, f"edge_log_{RUN_ID}_{DEVICE_ID}.csv")
need_header = (not os.path.exists(csv_path)) or (os.stat(csv_path).st_size == 0)
csv_f = open(csv_path, "a", buffering=1)  # line-buffered append
if need_header:
    csv_f.write("timestamp_ms,run_id,device_id,pkt_idx,phase,rmse,is_anomaly,threshold,fl_enabled,FM_grace,AD_grace\n")


def _log_row(pkt_idx, phase, rmse, is_anom, threshold_val, FM_grace, AD_grace):
    ts = int(time.time() * 1000)
    thr_out = "" if threshold_val is None else f"{threshold_val:.6f}"
    csv_f.write(
        f"{ts},{RUN_ID},{DEVICE_ID},{pkt_idx},{phase},{rmse:.6f},{is_anom},{thr_out},{FL_ENABLED},{FM_grace},{AD_grace}\n")


def main():
    # Kitsune-Parameter
    path = "real_time"
    packet_limit = np.inf
    FM_grace = 250  # Packet number of Feature Mapping grace period (training phase 1)
    AD_grace = 2250  # Packet number of Anomaly Detection grace period (training phase 2)
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

    total_grace = FM_grace + AD_grace  # Ende TRAIN (keine sinnvollen RMSE)
    calib_until = 2 * (FM_grace + AD_grace) # Ende CALIB (Threshold fertig)

    # >>> STATE für die Callback-Funktion
    state = {
        "pkt_idx": 0,
        "phase": "TRAIN",  # TRAIN -> CALIB -> DETECT
        "threshold_value": None,
        "total_grace": total_grace,
        "calib_until": calib_until
    }

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

                if not sending_started:
                    if int(time.time()) % 20 == 0:  # every 20 seconds
                        try:
                            dummy_payload = {
                                "device_id": edge_device.device_id,
                                "weights": edge_device.get_model_weights()
                            }
                            requests.post(f"{edge_device.server_url}/upload_weights", json=dummy_payload, timeout=1)
                            print(f"[{edge_device.device_id}] Test-Gewichte gesendet während Grace Period.")
                        except Exception as e:
                            print(f"[{edge_device.device_id}] Fehler beim Dummy-Senden während Grace Period: {e}")

                if not sending_started and rmse is not None and rmse > 0.0:
                    print("[edgeDevice] Grace Period vorbei. Starte Sende-Thread.")
                    threading.Thread(target=edge_device.start_sending, daemon=True).start()
                    sending_started = True

                    # Logging
                    model_depth = len(kitsune.AnomDetector.ensembleLayer)
                    timestamp = time.time()
                    mpath = f"{log_dir}/model_depth_log.csv"
                    need_h = (not os.path.exists(mpath)) or (os.stat(mpath).st_size == 0)
                    with open(mpath, "a") as f:
                        if need_h:
                            f.write("device_id,model_depth,timestamp\n")
                        f.write(f"{edge_device.device_id},{model_depth},{timestamp}\n")
                    print(f"[{edge_device.device_id}] Modell abgeschlossen mit {model_depth} Autoencoder-Schichten")

                if rmse is not None and rmse != -1:

                    print(f"RMSE: {rmse}")
                    timestamp = time.time()
                    threshold = threshold_calculator.handle_rmse(rmse)

                    s = state  # Abkürzung
                    s["pkt_idx"] += 1
                    # Phase per Index ableiten – deine Schwellenlogik bleibt unberührt:
                    if s["pkt_idx"] <= s["total_grace"]:
                        s["phase"] = "TRAIN"
                        is_anom = 0

                    elif s["pkt_idx"] <= s["calib_until"]:
                        s["phase"] = "CALIB"
                        is_anom = 0
                        # Schwellenwert (falls bereits gesetzt) lesen – NICHT berechnen:
                        try:
                            s["threshold_value"] = threshold
                        except Exception:
                            pass

                    else:
                        s["phase"] = "DETECT"
                        try:
                            s["threshold_value"] = threshold
                        except Exception:
                            pass
                        is_anom = 1 if (s["threshold_value"] is not None and rmse > s["threshold_value"]) else 0

                    _log_row(s["pkt_idx"], s["phase"], rmse, is_anom, s["threshold_value"], FM_grace, AD_grace)

                    # Logging
                    """
                    with open(f"{log_dir}/rmse_log_{edge_device.device_id}.csv", "w") as f:
                        is_anomaly = 1 if threshold and rmse > threshold else 0
                        f.write(f"{timestamp},{rmse:.6f},{threshold if threshold else -1},{is_anomaly}\n")
                    """
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
