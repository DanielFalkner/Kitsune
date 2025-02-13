from flask import Flask, request, jsonify
import numpy as np

app = Flask(__name__)

# Temporäre Speicherung der empfangenen Gewichte
received_weights = {}


def aggregate_weights():
    """Berechnet den Mittelwert der empfangenen Gewichte"""
    if not received_weights:
        print("[Server] Keine empfangenen Gewichte, Aggregation übersprungen.")
        return {}

    aggregated_weights = {}

    # Initialisiere aggregierte Gewichte mit den Keys des ersten Geräts
    first_device = list(received_weights.keys())[0]
    print(f"[Server] Aggregation gestartet. Beispiel-Daten: {received_weights[first_device]}")

    for key in received_weights[first_device]:
        weight_arrays = []

        for device in received_weights:
            value = received_weights[device][key]
            print(f"[Server] Debug: Wert für {key} von {device} - Typ: {type(value)}, Inhalt: {value}")

            if isinstance(value, dict):
                # Prüfe, ob es ein Dictionary mit 'W', 'hbias', 'vbias' ist
                if "W" in value and "hbias" in value and "vbias" in value:
                    value = np.array(value["W"])  # Nehme nur die Gewichtsmatrix
                else:
                    print(f"[Server] ⚠ Unerwartete Struktur für {key} von {device}: {value}")
                    continue

            # Falls Wert eine Liste oder ein NumPy-Array ist, hinzufügen
            if isinstance(value, (list, np.ndarray)):
                try:
                    weight_arrays.append(
                        np.array(value, dtype=np.float64))  # Sicherstellen, dass alle Werte floats sind
                except ValueError:
                    print(f"[Server] Ungültige Datenstruktur für {key} von {device}, überspringe.")
                    continue

        if not weight_arrays:
            print(f"[Server] Keine gültigen Werte für {key}, überspringe.")
            continue

        # Prüfen, ob alle Werte die gleiche Form haben
        if not all(arr.shape == weight_arrays[0].shape for arr in weight_arrays):
            print(f"[Server] Unterschiedliche Shapes für {key}, Aggregation übersprungen.")
            continue

        mean_values = np.mean(weight_arrays, axis=0)

        # Falls der Mittelwert ein einzelner Wert ist, in eine Liste umwandeln
        if isinstance(mean_values, np.ndarray):
            aggregated_weights[key] = mean_values.tolist()
        else:
            aggregated_weights[key] = [mean_values]

    print(f"[Server] Aggregierte Gewichte: {aggregated_weights}")
    return aggregated_weights


@app.route('/upload_weights', methods=['POST'])
def upload_weights():
    """Empfängt Gewichte von einem Edge Device"""
    try:
        data = request.json
        device_id = data.get("device_id")
        weights = data.get("weights")

        if not device_id or not weights:
            return jsonify({"error": "Ungültige Daten"}), 400

        received_weights[device_id] = weights

        # Debugging: Überprüfe, ob die Gewichte korrekt gespeichert werden
        print("Uploaded_weights funktioniert und gibt nicht noch extra weights aus")

        return jsonify({"message": "Gewichte erfolgreich empfangen"}), 200
    except Exception as e:
        print(f"[Server ERROR] Fehler beim Empfangen der Gewichte: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/get_aggregated_weights', methods=['GET'])
def get_aggregated_weights():
    """Sendet die aggregierten Gewichte an die Edge Devices zurück"""
    aggregated_weights = aggregate_weights()

    print(f"[Server] API sendet aggregierte Gewichte: {aggregated_weights}")

    if not aggregated_weights:  # Prüfen, ob Aggregation funktioniert hat
        return jsonify({"error": "Noch keine Gewichte verfügbar"}), 400

    return jsonify({"aggregated_weights": aggregated_weights}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
