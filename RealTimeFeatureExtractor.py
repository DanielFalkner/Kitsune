import numpy as np
import netStat as ns
import socket
from scapy.all import IP, TCP, UDP, IPv6, ARP, DNS, DNSQR, ICMP


class RealTimeFeatureExtractor:
    def __init__(self, max_host=100000000000, max_sess=100000000000):
        self.targetIP = get_host_ip()
        self.nstat = ns.netStat(np.nan, max_host, max_sess)
        self.last_features = None  # Stores the last feature vector
        self.cur_packet_index = 0  # Packet index for tracking
        print("RealTimeFeatureExtractor gestartet.")

    def process_packet(self, packet):
        try:
            IPtype = np.nan
            timestamp = packet.time
            framelen = len(packet)

            # Determine source/destination IP and protocol type
            if packet.haslayer(IP):  # IPv4
                srcIP = packet[IP].src
                dstIP = packet[IP].dst
                IPtype = 0
            elif packet.haslayer(IPv6):  # IPv6
                srcIP = packet[IPv6].src
                dstIP = packet[IPv6].dst
                IPtype = 1
            else:
                srcIP = ''
                dstIP = ''

            # Determine transport protocol and ports
            if packet.haslayer(TCP):
                srcproto = str(packet[TCP].sport)
                dstproto = str(packet[TCP].dport)
            elif packet.haslayer(UDP):
                srcproto = str(packet[UDP].sport)
                dstproto = str(packet[UDP].dport)
            else:
                srcproto = ''
                dstproto = ''

            # Handle non-IP protocols like ARP or ICMP
            if srcproto == '':  # it's a L2/L1 level protocol
                if packet.haslayer(ARP):  # is ARP
                    srcproto = 'arp'
                    dstproto = 'arp'
                    srcIP = packet[ARP].psrc  # src IP (ARP)
                    dstIP = packet[ARP].pdst  # dst IP (ARP)
                    IPtype = 0
                elif packet.haslayer(ICMP):  # is ICMP
                    srcproto = 'icmp'
                    dstproto = 'icmp'
                    if packet.haslayer(IP):
                        srcIP = packet[IP].src
                        dstIP = packet[IP].dst
                    elif packet.haslayer(IPv6):
                        srcIP = packet[IPv6].src
                        dstIP = packet[IPv6].dst
                    IPtype = 0
                elif srcIP + srcproto + dstIP + dstproto == '':  # some other protocol
                    srcIP = packet.src  # src MAC
                    dstIP = packet.dst  # dst MAC

            # Default MAC values if not available
            srcMAC = getattr(packet, 'src', '00:00:00:00:00:00')
            dstMAC = getattr(packet, 'dst', '00:00:00:00:00:00')

            """
            # Nur Pakete weiterverarbeiten, die für das Gerät bestimmt sind
            # Entweder so lassen oder das ganze Netzwerk analysieren
            print(f"Target-IP: {self.targetIP}, Empfangenes Paket für: {dstIP}")
            if dstIP != self.targetIP:
                print("Paket nicht für Target-IP. Übersprungen.")
                return None
            """
            # Compute feature vector via netStat
            return self.nstat.updateGetStats(
                str(IPtype), srcMAC, dstMAC, srcIP, str(srcproto), dstIP, str(dstproto),
                framelen, timestamp
            )
        except Exception as e:
            print(f"Error processing packet: {e}")
            return None

    # Return the number of computed features (capped at 100)
    def get_num_features(self):
        # num_features = len(self.nstat.getNetStatHeaders())
        # return min(num_features, 100)
        return 100

    def get_next_vector(self, packet):
        try:
            if packet is None:
                print("Warnung: Kein Paket erhalten. Vektor wird nicht generiert.")
                return None

            print(f"Verarbeite Paket {self.cur_packet_index}...")
            self.cur_packet_index += 1

            vector = self.process_packet(packet)

            if vector is None or len(vector) == 0:
                print("Warnung: Kein Vektor generiert.")
                return None

            return vector

        except Exception as e:
            print(f"Fehler in get_next_vector: {e}")
            return None


def get_host_ip():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)
