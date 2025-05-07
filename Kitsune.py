from FeatureExtractor import *
from RealTimeFeatureExtractor import RealTimeFeatureExtractor
from KitNET.KitNET import KitNET


# MIT License
#
# Copyright (c) 2018 Yisroel mirsky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

class Kitsune:
    def __init__(self, file_path, limit, max_autoencoder_size=10, FM_grace_period=None, AD_grace_period=10000,
                 learning_rate=0.1, hidden_ratio=0.75, ):
        # Initialize the feature extractor based on mode (real-time or from pcap file)
        if file_path is None or file_path == "real_time":
            print("Kitsune im Echtzeitmodus gestartet.")
            self.FE = RealTimeFeatureExtractor()
        else:
            print("Kitsune im Dateimodus gestartet.")
            self.FE = FE(file_path, limit)

        # Initialize KitNET using number of extracted features
        num_features = self.FE.get_num_features()
        print(f"Anzahl der erwarteten Features: {num_features}")
        self.AnomDetector = KitNET(self.FE.get_num_features(), max_autoencoder_size, FM_grace_period, AD_grace_period,
                                   learning_rate, hidden_ratio)

    """
    def proc_next_packet(self):
        # create feature vector
        x = self.FE.get_next_vector()
        if len(x) == 0:
            return -1 #Error or no packets left
        if x is None:
            print("Keine Pakete verarbeitet. Kein Vektor verfügbar.")
            return -1  # Oder einen anderen passenden Wert

        # process KitNET
        return self.AnomDetector.process(x)  # will train during the grace periods, then execute on all the rest.
    """

    def proc_next_packet(self, packet):
        try:
            if packet is None:
                # No packet received, small delay
                time.sleep(0.01)
                return -1

            # Generate feature vector from packet
            vector = self.FE.get_next_vector(packet)
            if vector is None:
                print("Warnung: Kein Vektor generiert.")
                return -1

            print(f"[DEBUG] Generierter Feature-Vektor: {vector}")
            print(f"[DEBUG] Länge des Vektors: {len(vector)}")

            # Compute RMSE anomaly score using KitNET
            rmse = self.AnomDetector.process(vector)
            print(f"[DEBUG] RMSE-Wert: {rmse}")
            return rmse
        except Exception as e:
            print(f"Fehler in proc_next_packet: {e}")
            return -1
