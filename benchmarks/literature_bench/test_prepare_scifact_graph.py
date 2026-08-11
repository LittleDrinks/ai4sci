import unittest

from benchmarks.literature_bench.prepare_scifact_graph import graph_documents


def claim(text, evidence):
    return {"claim": text, "evidence": evidence}


class GraphDocumentsTest(unittest.TestCase):
    def test_removes_exact_dev_duplicate(self):
        edge = {"7": [{"sentences": [1], "label": "SUPPORT"}]}
        train = [claim("Same claim", edge), claim("Other claim", edge)]
        result = graph_documents(train, [claim("same  claim", edge)])
        self.assertEqual(result[7], {"Other claim"})

    def test_retains_same_text_with_different_evidence(self):
        train_edge = {"7": [{"sentences": [1], "label": "SUPPORT"}]}
        dev_edge = {"8": [{"sentences": [1], "label": "SUPPORT"}]}
        result = graph_documents([claim("Same", train_edge)], [claim("Same", dev_edge)])
        self.assertEqual(result[7], {"Same"})


if __name__ == "__main__":
    unittest.main()
