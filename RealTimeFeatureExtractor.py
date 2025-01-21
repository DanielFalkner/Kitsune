import numpy as np
import netStat as ns
from scapy.all import IP, TCP, UDP, IPv6


class RealTimeFeatureExtractor:
    def __init__(self, target_ip=None, max_host=100000000000, max_sess=100000000000):
        self.targetIP = target_ip
        self.nstat = ns.netStat(np.nan, max_host, max_sess)
        self.last_features = None  # Speichert den letzten verarbeiteten Vektor
        self.cur_packet_index = 0  # Paketindex zur Nachverfolgung
        print("RealTimeFeatureExtractor gestartet.")

    def process_packet(self, packet):
        try:
            IPtype = np.nan
            timestamp = packet.time
            framelen = len(packet)
            if packet.haslayer(IP):  # IPv4
                srcIP = packet[IP].src
                dstIP = packet[IP].dst
                IPtype = 0
            elif packet.haslayer(IPv6):  # IPv6
                srcIP = packet[IPv6].src
                dstIP = packet[IPv6].dst
                IPtype = 1
            else:
                srcIP = dstIP = ""

            if packet.haslayer(TCP):
                srcproto = str(packet[TCP].sport)
                dstproto = str(packet[TCP].dport)
            elif packet.haslayer(UDP):
                srcproto = str(packet[UDP].sport)
                dstproto = str(packet[UDP].dport)
            else:
                srcproto = dstproto = ""

            return self.nstat.updateGetStats(
                IPtype, packet.src, packet.dst, srcIP, srcproto, dstIP, dstproto,
                framelen, timestamp
            )
        except Exception as e:
            print(f"Error processing packet: {e}")
            return None

    def get_num_features(self):
        num_features = len(self.nstat.getNetStatHeaders())
        return min(num_features, 64)  # Begrenze die Anzahl der Features auf 64

    def get_next_vector(self, packet):
        print(f"Paket erhalten FE: {packet.summary()}")
        try:
            # Überprüfen, ob das Paket notwendig ist
            if packet is None:
                return None

            # Felder extrahieren
            IPtype = packet[IP].version if IP in packet else None
            srcMAC = packet.src if hasattr(packet, 'src') else None
            dstMAC = packet.dst if hasattr(packet, 'dst') else None
            srcIP = packet[IP].src if IP in packet else None
            dstIP = packet[IP].dst if IP in packet else None
            srcProtocol = packet[IP].proto if IP in packet else None
            dstProtocol = packet[TCP].dport if TCP in packet else None
            datagramSize = len(packet) if hasattr(packet, '__len__') else 0
            timestamp = packet.time if hasattr(packet, 'time') else None

            # Nur Pakete weiterverarbeiten, die für das Gerät bestimmt sind - Funktioniert nicht
 #           if dstIP != self.targetIP:
  #             return None

            # Debugging-Ausgaben müssen hier eingefügt werden. Type Issues hier

            # Statistiken aktualisieren
            vector = self.nstat.updateGetStats(IPtype, srcMAC, dstMAC, srcIP, srcProtocol, dstIP, dstProtocol, datagramSize,
                                      timestamp)

            if vector is None or len(vector) == 0:
                return None
            return vector

        except Exception as e:
            print(f"Fehler in get_next_vector: {e}")
            return None
    """
    def get_next_vector(self, packet):
    try:
        # Falls kein Paket übergeben wurde
        if packet is None:
            print("Kein Paket übergeben. Warte auf nächstes Paket...")
            return None

        print(f"Verarbeite Paket {self.cur_packet_index}...")
        self.cur_packet_index += 1

        # Extrahiere Paketinformationen
        IPtype = 4 if packet.haslayer('IP') else 6 if packet.haslayer('IPv6') else None
        srcMAC = getattr(packet, 'src', '00:00:00:00:00:00')
        dstMAC = getattr(packet, 'dst', '00:00:00:00:00:00')
        srcIP = packet['IP'].src if packet.haslayer('IP') else None
        dstIP = packet['IP'].dst if packet.haslayer('IP') else None
        srcProtocol = packet['IP'].proto if packet.haslayer('IP') else None
        dstProtocol = packet['TCP'].dport if packet.haslayer('TCP') else None
        datagramSize = len(packet) if packet else 0
        timestamp = getattr(packet, 'time', 0)

        # Debugging-Ausgaben
        try:
            print(f"IPtype: {IPtype}, srcMAC: {srcMAC}, dstMAC: {dstMAC}")
            print(
                f"srcIP: {srcIP}, dstIP: {dstIP}, srcProtocol: {str(srcProtocol)}, dstProtocol: {str(dstProtocol)}")
            print(f"Datagramm-Größe: {datagramSize}, Timestamp: {timestamp}")
        except Exception as e:
            print(f"Fehler in Debugging-Ausgabe: {e}")

        # Falls wichtige Felder fehlen, überspringe das Paket
        if None in [srcIP, dstIP, srcProtocol, dstProtocol]:
            print("Ein oder mehrere notwendige Felder sind None. Paket wird übersprungen.")
            return None

        # Update der Statistik und Feature-Vektor
        vector = self.nstat.updateGetStats(
            str(IPtype), srcMAC, dstMAC, srcIP, str(srcProtocol), dstIP, str(dstProtocol), datagramSize, timestamp
        )

        if vector is None:
            print("Warnung: Kein Vektor generiert.")
            return None

        print(f"Generierter Vektor: {vector}")
        return vector
    except Exception as e:
        print(f"Fehler in get_next_vector: {e}")
        return None
    """





