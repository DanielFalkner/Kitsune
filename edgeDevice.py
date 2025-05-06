import socket
import requests
import time
import numpy as np
import os

log_dir = os.path.join(os.path.dirname(__file__), "Logs")
os.makedirs(log_dir, exist_ok=True)
device_id = socket.gethostname()


# Represents an Edge Device, which sends model weights periodically to a server
# and receives aggregated weights from the server to update local model
class EdgeDevice:
    def __init__(self, server_url, kitsune_instance, send_interval=60):
        self.server_url = server_url
        self.device_id = device_id
        self.kitnet = kitsune_instance.AnomDetector  # Uses KitNET from Kitsune
        self.send_interval = send_interval  # Time interval between sending model weights in seconds

        print(f"[Edge Device] Starte mit ID: {self.device_id}")

    def get_model_weights(self):
        weights_dict = {}

        # Extract weights from the ensemble layer
        for i, autoencoder in enumerate(self.kitnet.ensembleLayer):
            weights_dict[f"autoencoder_{i}"] = {
                "W": autoencoder.W.tolist(),
                "hbias": autoencoder.hbias.tolist(),
                "vbias": autoencoder.vbias.tolist()
            }

        # Extract weights from the output layer
        weights_dict["output_layer"] = {
            "W": self.kitnet.outputLayer.W.tolist(),
            "hbias": self.kitnet.outputLayer.hbias.tolist(),
            "vbias": self.kitnet.outputLayer.vbias.tolist()
        }

        return weights_dict

    def set_model_weights(self, new_weights):
        try:
            # Update ensemble layer with new weights
            for i, autoencoder in enumerate(self.kitnet.ensembleLayer):
                autoencoder.W = np.array(new_weights[f"autoencoder_{i}"]["W"])
                autoencoder.hbias = np.array(new_weights[f"autoencoder_{i}"]["hbias"])
                autoencoder.vbias = np.array(new_weights[f"autoencoder_{i}"]["vbias"])

            # Update output layer with new weights
            self.kitnet.outputLayer.W = np.array(new_weights["output_layer"]["W"])
            self.kitnet.outputLayer.hbias = np.array(new_weights["output_layer"]["hbias"])
            self.kitnet.outputLayer.vbias = np.array(new_weights["output_layer"]["vbias"])

            print(f"[{self.device_id}] Gewichte erfolgreich aktualisiert.")
        except Exception as e:
            print(f"[{self.device_id}] Fehler beim Setzen der Gewichte: {e}")

    def send_weights(self):
        try:
            # Package and send model weights to the central server
            payload = {
                "device_id": self.device_id,
                "weights": self.get_model_weights()
            }
            response = requests.post(f"{self.server_url}/upload_weights", json=payload)

            if response.status_code == 200:
                # Receive and apply aggregated weights from the server
                aggregated_weights = response.json()
                print(f"[{self.device_id}] Aggregierte Gewichte empfangen. Modell wird aktualisiert.")

                # Logging differences between old and new weights
                old_weights = self.get_model_weights()
                for key in aggregated_weights:
                    if key in old_weights:
                        try:
                            diff = np.linalg.norm(
                                np.array(aggregated_weights[key]["W"]) - np.array(old_weights[key]["W"])
                            )
                            with open(f"{log_dir}/model_diff_log_{self.device_id}.csv", "w") as f:
                                f.write(f"{key},{diff:.6f},{time.time()}\n")
                        except Exception as e:
                            print(f"[{self.device_id}] Vergleich bei {key} fehlgeschlagen: {e}")

                self.set_model_weights(aggregated_weights)
            else:
                print(f"[{self.device_id}] Unerwartete Server-Antwort ({response.status_code}): {response.text}")

        except Exception as e:
            print(f"[{self.device_id}] Fehler beim Senden oder Aktualisieren der Gewichte: {e}")

    def start_sending(self):
        # Loop to send model weights at defined intervals
        while True:
            self.send_weights()
            time.sleep(self.send_interval)
