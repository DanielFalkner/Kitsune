class ThresholdCalculator:
    def __init__(self, grace_period_total):
        self.grace_period_total = grace_period_total  # Duration before threshold collection starts
        self.packet_counter = -1  # Packet count tracker (starts negative to include grace)
        self.threshold_calculated = False  # Indicates whether threshold is already computed
        self.rmse_values_for_threshold = []  # Collected RMSE values to compute threshold
        self.threshold = None
        self.in_threshold_phase = False   # Whether we are currently collecting threshold data

    def handle_rmse(self, rmse):
        # Increments packet count and manages state between grace, thresholding, and detection
        if not self.threshold_calculated:
            self.packet_counter += 1

            # Start threshold collection after grace period
            if self.packet_counter >= self.grace_period_total and not self.in_threshold_phase:
                print("Grace Period abgeschlossen. Threshold-Erfassung gestartet.")
                self.in_threshold_phase = True
                self.packet_counter = 0  # Restart counter for threshold collection

            if self.in_threshold_phase:
                self.rmse_values_for_threshold.append(rmse)

                # Once enough values are collected, calculate the threshold
                if self.packet_counter >= self.grace_period_total:
                    self.calculate_threshold()
                    self.threshold_calculated = True
                    print("Threshold-Berechnung abgeschlossen.")

        return self.threshold

    def calculate_threshold(self):
        # Basic threshold calculation using mean * factor of RMSEs
        mean_rmse = sum(self.rmse_values_for_threshold) / len(self.rmse_values_for_threshold)
        self.threshold = mean_rmse * 4  # Customizable multiplier for sensitivity
        print(f"Threshold berechnet: {self.threshold}")
