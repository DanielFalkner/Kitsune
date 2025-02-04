class ThresholdCalculator:
    def __init__(self, grace_period_total):
        self.grace_period_total = grace_period_total
        self.packet_counter = -1  # Starte bei -1, um die Grace Period zu starten
        self.threshold_calculated = False
        self.rmse_values_for_threshold = []
        self.threshold = None
        self.in_threshold_phase = False

    def handle_rmse(self, rmse):
        # Zähle die Pakete während der gesamten Phase (Grace Period + Threshold-Erfassung)
        if not self.threshold_calculated:
            self.packet_counter += 1

            # Nach der Grace Period Threshold-Erfassung starten
            if self.packet_counter >= self.grace_period_total and not self.in_threshold_phase:
                print("Grace Period abgeschlossen. Threshold-Erfassung gestartet.")
                self.in_threshold_phase = True
                self.packet_counter = 0  # Zähler für die Threshold-Erfassung zurücksetzen

            if self.in_threshold_phase:
                # RMSE-Werte für Threshold-Erfassung sammeln
                self.rmse_values_for_threshold.append(rmse)

                # Sobald die zweite Phase abgeschlossen ist, berechne den Threshold
                if self.packet_counter >= self.grace_period_total:
                    self.calculate_threshold()
                    self.threshold_calculated = True
                    print("Threshold-Berechnung abgeschlossen.")

        return self.threshold

    def calculate_threshold(self):
        # Berechne den Threshold basierend auf den RMSE-Werten
        mean_rmse = sum(self.rmse_values_for_threshold) / len(self.rmse_values_for_threshold)
        self.threshold = mean_rmse * 4  # Beispielhafte Schwellenwert-Berechnung
        print(f"Threshold berechnet: {self.threshold}")
