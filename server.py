from flask import Flask, request, jsonify
import numpy as np

app = Flask(__name__)

# In-memory storage for received weights, last aggregation result and previous weights
received_weights = {}
last_aggregated_weights = {}
previous_received_weights = {}


def aggregate_weights():
    if not received_weights:
        print("[Server] Keine empfangenen Gewichte, Aggregation übersprungen.")
        return {}

    aggregated_weights = {}

    # Collect all layer keys from all devices
    all_keys = set()
    for device_weights in received_weights.values():
        all_keys.update(device_weights.keys())

    print(f"[Server] Aggregation gestartet auf Basis von {len(received_weights)} Geräten.")
    skipped_W = skipped_hbias = skipped_vbias = 0

    for key in sorted(all_keys):
        weight_arrays = []
        hbias_arrays = []
        vbias_arrays = []

        for device_id, weights in received_weights.items():
            if key not in weights:
                print(f"[Server] Schlüssel '{key}' fehlt bei Gerät {device_id}, überspringe diesen Layer.")
                continue

            value = weights[key]

            if not isinstance(value, dict):
                print(f"[Server] Ungültige Struktur bei {key} von {device_id}, übersprungen.")
                continue

            try:
                weight_arrays.append(np.array(value["W"], dtype=np.float64))
                hbias_arrays.append(np.array(value["hbias"], dtype=np.float64))
                vbias_arrays.append(np.array(value["vbias"], dtype=np.float64))
            except KeyError:
                print(f"[Server] Fehlende Werte bei {key} von {device_id}, übersprungen.")
                continue
            except ValueError:
                print(f"[Server] Nicht konvertierbare Werte bei {key} von {device_id}, übersprungen.")
                continue

        # Validate all arrays have the same shape and minimum count
        if len(weight_arrays) < 2:
            print(f"[Server] Nicht genügend gültige Werte für Layer '{key}', Aggregation übersprungen.")
            continue

        if not all(arr.shape == weight_arrays[0].shape for arr in weight_arrays):
            print(f"[Server] Unterschiedliche Shapes bei '{key}' - W, Aggregation übersprungen.")
            skipped_W += 1
            continue
        if not all(arr.shape == hbias_arrays[0].shape for arr in hbias_arrays):
            print(f"[Server] Unterschiedliche Shapes bei '{key}' - hbias, Aggregation übersprungen.")
            skipped_hbias += 1
            continue
        if not all(arr.shape == vbias_arrays[0].shape for arr in vbias_arrays):
            print(f"[Server] Unterschiedliche Shapes bei '{key}' - vbias, Aggregation übersprungen.")
            skipped_vbias += 1
            continue

        # Compute mean of each parameter across devices
        aggregated_weights[key] = {
            "W": np.mean(weight_arrays, axis=0).tolist(),
            "hbias": np.mean(hbias_arrays, axis=0).tolist(),
            "vbias": np.mean(vbias_arrays, axis=0).tolist()
        }

    print(f"\n[Server] Aggregation abgeschlossen.")
    print(f"[Server] Übersprungene Layer:")
    print(f"    - W: {skipped_W}")
    print(f"    - hbias: {skipped_hbias}")
    print(f"    - vbias: {skipped_vbias}")
    print(f"[Server] Aggregiertes Modell enthält {len(aggregated_weights)} Layer.\n")

    return aggregated_weights


@app.route('/upload_weights', methods=['POST'])
def upload_weights():
    global last_aggregated_weights, previous_received_weights
    try:
        data = request.json
        device_id = data.get("device_id")
        weights = data.get("weights")

        if not device_id or not weights:
            return jsonify({"error": "Ungültige Daten"}), 400

        if not previous_received_weights:
            previous_received_weights[device_id] = weights
            print(f"[Server] Erstes Gerät gespeichert, warte auf zweites.")
            return jsonify({"info": "Noch kein zweites Gerät, Aggregation später."}), 202
        else:
            previous_received_weights[device_id] = weights
            print(f"[Server] Zweites Gerät erkannt, Aggregation startet.")

            aggregated_weights = aggregate_weights()

            received_weights.clear()
            previous_received_weights.clear()

            if last_aggregated_weights:
                print("[Server] Veränderung gegenüber vorherigem globalem Modell:")
                for key in aggregated_weights:
                    if key in last_aggregated_weights:
                        try:
                            diff = np.linalg.norm(
                                np.array(aggregated_weights[key]["W"]) - np.array(last_aggregated_weights[key]["W"])
                            )
                            print(f"- {key} (W): Δ = {diff:.6f}")
                        except Exception as e:
                            print(f"- {key}: Fehler beim Vergleich: {e}")
            else:
                print("[Server] Erstes globales Modell gespeichert.")

            last_aggregated_weights = aggregated_weights.copy()

            return jsonify(aggregated_weights), 200

    except Exception as e:
        print(f"[Server ERROR] Fehler beim Empfangen der Gewichte: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/get_aggregated_weights', methods=['GET'])
def get_aggregated_weights():
    if not last_aggregated_weights:
        return jsonify({"error": "Noch keine Gewichte verfügbar"}), 404

    print("[Server] API sendet aggregierte Gewichte.")
    return jsonify(last_aggregated_weights), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
