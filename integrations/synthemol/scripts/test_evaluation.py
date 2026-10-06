import math
import unittest
import numpy as np
import pandas as pd
from evaluate_synthemol import identity, mic_label, weighted_metrics


class EvaluationTests(unittest.TestCase):
    def test_salt_forms_share_parent(self):
        self.assertEqual(identity("CCN.Cl")[:2], identity("CCN")[:2])

    def test_stereoisomers_are_conservatively_grouped(self):
        self.assertEqual(identity("C[C@H](O)C(=O)O")[:2], identity("C[C@@H](O)C(=O)O")[:2])

    def test_invalid_is_not_a_negative(self):
        self.assertEqual(identity("not_a_smiles"), ("", "", ""))

    def test_censoring_at_cutoff(self):
        cutoff = math.log2(8)
        self.assertEqual(mic_label(cutoff, cutoff, True, cutoff), 1)
        self.assertEqual(mic_label(-np.inf, cutoff, True, cutoff), 1)
        self.assertTrue(np.isnan(mic_label(cutoff, np.inf, True, cutoff)))
        self.assertEqual(mic_label(cutoff, np.inf, False, cutoff), 0)
        self.assertEqual(mic_label(4, np.inf, True, cutoff), 0)
        self.assertTrue(np.isnan(mic_label(2, 4, True, cutoff)))
        self.assertTrue(np.isnan(mic_label(np.nan, np.nan, True, cutoff)))

    def test_repeated_measurements_do_not_reweight_compounds(self):
        original = pd.DataFrame(dict(parent=["a", "b", "c", "d"], study=["x"] * 4,
            label=[0, 1, 0, 1], score=[0.1, 0.4, 0.6, 0.9], cohort=["screen"] * 4,
            censor=[""] * 4))
        duplicated = pd.concat([original, original.iloc[[1, 1, 1]]], ignore_index=True)
        a, b = weighted_metrics(original, "score"), weighted_metrics(duplicated, "score")
        for metric in ("roc_auc", "average_precision", "positive_prevalence"):
            self.assertAlmostEqual(a[metric], b[metric])


if __name__ == "__main__":
    unittest.main()
