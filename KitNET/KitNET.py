import numpy as np
import KitNET.dA as AE
import KitNET.corClust as CC
import json
import os


# This class represents a KitNET machine learner.
# KitNET is a lightweight online anomaly detection algorithm based on an ensemble of autoencoders.
# For more information and citation, please see our NDSS'18 paper: Kitsune: An Ensemble of Autoencoders for Online Network Intrusion Detection
# For licensing information, see the end of this document

class KitNET:
    # n: the number of features in your input dataset (i.e., x \in R^n)
    # m: the maximum size of any autoencoder in the ensemble layer
    # AD_grace_period: the number of instances the network will learn from before producing anomaly scores
    # FM_grace_period: the number of instances which will be taken to learn the feature mapping. If 'None', then FM_grace_period=AM_grace_period
    # learning_rate: the default stochastic gradient descent learning rate for all autoencoders in the KitNET instance.
    # hidden_ratio: the default ratio of hidden to visible neurons. E.g., 0.75 will cause roughly a 25% compression in the hidden layer.
    # feature_map: One may optionally provide a feature map instead of learning one. The map must be a list,
    #           where the i-th entry contains a list of the feature indices to be assingned to the i-th autoencoder in the ensemble.
    #           For example, [[2,5,3],[4,0,1],[6,7]]
    def __init__(self, n, max_autoencoder_size=10, FM_grace_period=None, AD_grace_period=10000, learning_rate=0.1,
                 hidden_ratio=0.75, feature_map=None):
        # Parameters:
        self.AD_grace_period = AD_grace_period
        if FM_grace_period is None:
            self.FM_grace_period = AD_grace_period
        else:
            self.FM_grace_period = FM_grace_period
        if max_autoencoder_size <= 0:
            self.m = 1
        else:
            self.m = max_autoencoder_size
        self.lr = learning_rate
        self.hr = hidden_ratio
        self.n = n

        # Variables
        self.n_trained = 0  # the number of training instances so far
        self.n_executed = 0  # the number of executed instances so far

        feature_map_path = "fixed_feature_map.json"
        if os.path.exists(feature_map_path):
            # Fixed Feature Map aus JSON-Datei laden
            with open("fixed_feature_map.json", "r") as f:
                feature_map_data = json.load(f)
            if isinstance(feature_map, list) and all(isinstance(i, list) for i in feature_map):
                self.v = feature_map_data["feature_map"]
                print("[DEBUG] Feature-Map erfolgreich aus JSON-Datei geladen:", self.v)
            else:
                raise ValueError("Feature-Map JSON-Datei hat ein ungültiges Format.")
        else:
            raise FileNotFoundError("Feature-Map JSON-Datei fehlt. Bitte erstellen und speichern.")
        self.ensembleLayer = []
        self.__createAD__()
        print("Feature-Mapper: execute-mode, Anomaly-Detector: train-mode")
        self.FM = CC.corClust(self.n)  # incremental feature cluatering for the feature mapping process
        self.outputLayer = None

    # If FM_grace_period+AM_grace_period has passed, then this function executes KitNET on x. Otherwise, this function learns from x.
    # x: a numpy array of length n
    # Note: KitNET automatically performs 0-1 normalization on all attributes.
    def process(self, x):
        try:
            print(f"[DEBUG] Training Counter: {self.n_trained}")
            if self.n_trained > self.FM_grace_period + self.AD_grace_period:  # If both the FM and AD are in execute-mode
                return self.execute(x)
            else:
                self.train(x)
                print(f"[DEBUG] Training Vector Processed: {x}")
                return 0.0
        except Exception as e:
            print(f"[KitNET-Fehler in process()]: {e}")
            return -1

    """
    #force train KitNET on x
    #returns the anomaly score of x during training (do not use for alerting)
    def train(self,x):
        if self.n_trained <= self.FM_grace_period and self.v is None: #If the FM is in train-mode, and the user has not supplied a feature mapping
            #update the incremetnal correlation matrix
            self.FM.update(x)
            if self.n_trained == self.FM_grace_period: #If the feature mapping should be instantiated
                self.v = self.FM.cluster(self.m)
                self.__createAD__()
                print("The Feature-Mapper found a mapping: "+str(self.n)+" features to "+str(len(self.v))+" autoencoders.")
                print("Feature-Mapper: execute-mode, Anomaly-Detector: train-mode")
        else: #train
            ## Ensemble Layer
            S_l1 = np.zeros(len(self.ensembleLayer))
            for a in range(len(self.ensembleLayer)):
                # make sub instance for autoencoder 'a'
                xi = x[self.v[a]]
                S_l1[a] = self.ensembleLayer[a].train(xi)
            ## OutputLayer
            self.outputLayer.train(S_l1)
            if self.n_trained == self.AD_grace_period+self.FM_grace_period:
                print("Feature-Mapper: execute-mode, Anomaly-Detector: execute-mode")
                from edgeDevice import device_id
                self.log_feature_map(device_id)
        self.n_trained += 1
    """

    def train(self, x):
        if self.v is None:  # Wenn keine Feature-Map existiert, Feature-Mapping durchführen
            print("[DEBUG] Feature-Map existiert nicht. Feature-Mapping wird erstellt.")
            if self.n_trained <= self.FM_grace_period:  # FM-Phase
                self.FM.update(x)
                print(f"[DEBUG] Feature-Map-Update: Paket {self.n_trained}")
                if self.n_trained == self.FM_grace_period:  # Wenn FM-Phase abgeschlossen
                    self.v = self.FM.cluster(self.m)
                    self.__createAD__()
                    print("The Feature-Mapper found a mapping: " + str(self.n) + " features to " + str(
                        len(self.v)) + " autoencoders.")
                    print("Feature-Mapper: execute-mode, Anomaly-Detector: train-mode")
        else:
            print("[DEBUG] Training der Autoencoder...")
            # Training der Autoencoder mit der festen Feature-Map
            S_l1 = np.zeros(len(self.ensembleLayer))
            print(f"[DEBUG] Anzahl Autoencoder in EnsembleLayer: {len(self.ensembleLayer)}")
            for a in range(len(self.ensembleLayer)):
                print(f"[DEBUG] Schleife wird durchlaufen")
                try:
                    xi = x[self.v[a]]
                    print(f"[DEBUG] Training Autoencoder {a} mit Features: {xi}")
                    S_l1[a] = self.ensembleLayer[a].train(xi)
                    print(f"[DEBUG] Autoencoder {a} trainiert. RMSE: {S_l1[a]}")
                except Exception as e:
                    print(f"[ERROR] Fehler beim Training von Autoencoder {a}: {e}")

            # Training des Output-Layers
            if self.outputLayer is not None:
                print("[DEBUG] Training Output Layer...")
                self.outputLayer.train(S_l1)

            if self.n_trained == self.AD_grace_period + self.FM_grace_period:
                print("Feature-Mapper: execute-mode, Anomaly-Detector: execute-mode")
                from edgeDevice import device_id
                self.log_feature_map(device_id)

        print(f"[DEBUG] Training abgeschlossen - Paket {self.n_trained}")
        self.n_trained += 1

    # force execute KitNET on x
    def execute(self, x):
        if self.v is None:
            raise RuntimeError(
                'KitNET Cannot execute x, because a feature mapping has not yet been learned or provided. Try running process(x) instead.')
        else:
            self.n_executed += 1
            ## Ensemble Layer
            S_l1 = np.zeros(len(self.ensembleLayer))
            for a in range(len(self.ensembleLayer)):
                # make sub inst
                xi = x[self.v[a]]
                S_l1[a] = self.ensembleLayer[a].execute(xi)
            ## OutputLayer
            return self.outputLayer.execute(S_l1)

    """
    def __createAD__(self):
        # construct ensemble layer
        for map in self.v:
            params = AE.dA_params(n_visible=len(map), n_hidden=0, lr=self.lr, corruption_level=0, gracePeriod=0,
                                  hiddenRatio=self.hr)
            self.ensembleLayer.append(AE.dA(params))

        # construct output layer
        params = AE.dA_params(len(self.v), n_hidden=0, lr=self.lr, corruption_level=0, gracePeriod=0,
                              hiddenRatio=self.hr)
        self.outputLayer = AE.dA(params)
    """

    def __createAD__(self):
        print("[DEBUG] Erstelle Autoencoder basierend auf fester Feature-Map:")
        for idx, feature_indices in enumerate(self.v):
            try:
                params = AE.dA_params(
                    n_visible=len(feature_indices),
                    n_hidden=0,
                    lr=self.lr,
                    corruption_level=0,
                    gracePeriod=0,
                    hiddenRatio=self.hr
                )
                autoencoder = AE.dA(params)
                self.ensembleLayer.append(autoencoder)
                print(f"[DEBUG] Autoencoder {idx} erstellt für Features: {feature_indices}")
            except Exception as e:
                print(f"[ERROR] Fehler beim Erstellen von Autoencoder {idx}: {e}")

        # construct output layer
        try:
            params = AE.dA_params(
                n_visible=len(self.v),
                n_hidden=0,
                lr=self.lr,
                corruption_level=0,
                gracePeriod=0,
                hiddenRatio=self.hr
            )
            self.outputLayer = AE.dA(params)
            print("[DEBUG] Output-Layer erfolgreich erstellt.")
        except Exception as e:
            print(f"[ERROR] Fehler beim Erstellen des Output-Layers: {e}")

    def log_feature_map(self, device_id="default", output_dir="Logs"):
        import os
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/feature_map_log_{device_id}.csv"

        with open(output_file, "w") as f:
            f.write("Autoencoder,Feature_Indices\n")
            for i, feature_indices in enumerate(self.v):
                feature_str = ','.join(map(str, feature_indices))
                f.write(f"autoencoder_{i},{feature_str}\n")
        print(f"[KitNET] Feature-Mapping für {device_id} wurde geloggt.")

# Copyright (c) 2017 Yisroel Mirsky
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
