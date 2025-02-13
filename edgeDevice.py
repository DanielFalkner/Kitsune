import requests
import time
import numpy as np


class EdgeDevice:
    def __init__(self, server_url, device_id, kitsune_instance, send_interval=60):
        """
        :param server_url: URL des Servers, an den die Gewichte gesendet werden
        :param device_id: Eindeutige ID des Edge Devices
        :param kitsune_instance: Instanz von Kitsune, die KitNET enthält
        :param send_interval: Intervall in Sekunden, in dem die Gewichte gesendet werden
        """
        self.server_url = server_url
        self.device_id = device_id
        self.kitnet = kitsune_instance.AnomDetector  # Verwende KitNET aus Kitsune
        self.send_interval = send_interval

    def get_model_weights(self):
        """Extrahiert die Gewichte aller Autoencoder aus dem KitNET-Modell"""
        weights_dict = {}

        # Ensemble Layer Gewichte
        for i, autoencoder in enumerate(self.kitnet.ensembleLayer):
            weights_dict[f"autoencoder_{i}"] = {
                "W": autoencoder.W.tolist(),
                "hbias": autoencoder.hbias.tolist(),
                "vbias": autoencoder.vbias.tolist()
            }

        # Output Layer Gewichte
        weights_dict["output_layer"] = {
            "W": self.kitnet.outputLayer.W.tolist(),
            "hbias": self.kitnet.outputLayer.hbias.tolist(),
            "vbias": self.kitnet.outputLayer.vbias.tolist()
        }

        return weights_dict

    def set_model_weights(self, new_weights):
        """Setzt die Gewichte des KitNET-Modells mit neuen Werten"""
        try:
            # Ensemble Layer aktualisieren
            for i, autoencoder in enumerate(self.kitnet.ensembleLayer):
                autoencoder.W = np.array(new_weights[f"autoencoder_{i}"]["W"])
                autoencoder.hbias = np.array(new_weights[f"autoencoder_{i}"]["hbias"])
                autoencoder.vbias = np.array(new_weights[f"autoencoder_{i}"]["vbias"])

            # Output Layer aktualisieren
            self.kitnet.outputLayer.W = np.array(new_weights["output_layer"]["W"])
            self.kitnet.outputLayer.hbias = np.array(new_weights["output_layer"]["hbias"])
            self.kitnet.outputLayer.vbias = np.array(new_weights["output_layer"]["vbias"])

            print(f"[{self.device_id}] Gewichte erfolgreich aktualisiert.")
        except Exception as e:
            print(f"[{self.device_id}] Fehler beim Setzen der Gewichte: {e}")

    def send_weights(self):
        """Sendet die Gewichte an den Server"""
        try:
            payload = {
                "device_id": self.device_id,
                "weights": self.get_model_weights()
            }
            response = requests.post(f"{self.server_url}/upload_weights", json=payload)
            print(f"[{self.device_id}] Antwort des Servers: {response.json()}")
        except Exception as e:
            print(f"[{self.device_id}] Fehler beim Senden der Gewichte: {e}")

    def start_sending(self):
        """Startet das regelmäßige Senden der Gewichte"""
        while True:
            self.send_weights()
            time.sleep(self.send_interval)
