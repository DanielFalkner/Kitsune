import threading

from scapy.all import sniff, wrpcap, IP, TCP, send
import time


def capture_traffic(output_file, duration, interface):
    print(f"Starte die Aufzeichnung des Netzwerkverkehrs für {duration} Sekunden...")
    packets = sniff(iface=interface, timeout=duration)  # Pakete erfassen
    wrpcap(output_file, packets)  # Pakete in .pcap speichern
    print(f"Aufzeichnung abgeschlossen. Gespeichert in {output_file}")


def generate_dummy_traffic(target_ip, target_port, packet_count, interface):
    print(f"Generiere {packet_count} Dummy-Pakete an {target_ip}:{target_port} über Interface {interface}...")
    for i in range(packet_count):
        pkt = IP(dst=target_ip) / TCP(dport=target_port, flags="S")
        send(pkt, iface=interface, verbose=0)
        if i % 1000 == 0:
            print(f"{i} Dummy-Pakete gesendet...")
    print("Dummy-Daten generiert.")


if __name__ == "__main__":
    output_file = "network_traffic.pcap"
    capture_duration = 600  # Dauer in Sekunden
    target_ip = "192.168.0.179"  # Host Laptop "192.168.0.1", LinuxVM "192.168.0.179"
    target_port = 80
    dummy_packet_count = 5000
    interface = "enp0s3"  # In Windows "WLAN", für Linux "enp0s3"

    # Starte die Dummy-Daten-Generierung in einem separaten Thread
    #    dummy_thread = threading.Thread(target=generate_dummy_traffic,
    #                                    args=(target_ip, target_port, dummy_packet_count, interface))
    #    dummy_thread.start()
    # Netzwerkverkehr aufzeichnen
    capture_traffic(output_file, capture_duration, interface)

    # Warten, bis die Dummy-Daten-Generierung abgeschlossen ist
#    dummy_thread.join()
