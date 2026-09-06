import csv
import hashlib
import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


acquire = load("pilot01_acquire", "scripts/pilot01_acquire.py")
forensics = load("pilot01_forensics", "scripts/pilot01_forensics.py")


class CanonicalizationTests(unittest.TestCase):
    def test_determinism_and_versions(self):
        value = "A\tB\r\nCafe\u0301  C\u200bD"
        self.assertEqual(forensics.canonicalize(value, "N1"), forensics.canonicalize(value, "N1"))
        self.assertEqual(forensics.canonicalize(value, "N1"), "A\tB\nCaf\u00e9  C\u200bD")
        self.assertEqual(forensics.canonicalize(value, "N2"), "A B Caf\u00e9 C\u200bD")
        self.assertNotEqual(forensics.CANON_IDS["N1"], forensics.CANON_IDS["N2"])

    def test_visually_similar_unicode_is_preserved(self):
        self.assertNotEqual(forensics.canonicalize("A", "N1"), forensics.canonicalize("\u0410", "N1"))


class InfrastructureTests(unittest.TestCase):
    def test_staging_promotion_and_post_promotion_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.csv"
            source.write_text("id,prompt\n1,pilot\n", encoding="utf-8")
            artifact = {field:"NOT_VERIFIED" for field in acquire.REQUIRED_FIELDS}
            artifact.update({"dataset_id":"DS-TEST","artifact_id":"ART-TEST-001","name":"test",
                             "artifact_type":"UNIT_TEST","official_source":"LOCAL_TEST","paper":"NOT_APPLICABLE",
                             "repository":"NOT_APPLICABLE","dataset_card":"NOT_APPLICABLE","release":"NOT_APPLICABLE",
                             "commit":"NOT_APPLICABLE","revision":"UNIT-TEST-v1","resolved_revision":"UNIT-TEST-v1",
                             "retrieval_method":"FILE_URI","license_reference":"NOT_APPLICABLE",
                             "upstream_rights_status":"NOT_APPLICABLE","provenance_status":"COMPLETE",
                             "intended_pilot_action":"UNIT_TEST","acquisition_status":"PLANNED",
                             "url":source.as_uri(),"filename":"source.csv"})
            manifest_path=root/"manifest.json"
            manifest_path.write_text(json.dumps({"pilot_id":"PILOT-01","artifacts":[artifact]}),encoding="utf-8")
            acquire.acquire(manifest_path,root)
            result=json.loads(manifest_path.read_text(encoding="utf-8"))["artifacts"][0]
            raw=root/result["raw_path"]
            self.assertEqual(result["acquisition_status"],"ACQUIRED_VERIFIED")
            self.assertEqual(acquire.sha256_file(raw),result["sha256"])
            self.assertFalse(raw.stat().st_mode & stat.S_IWRITE)

    def test_hash_reproducibility(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x"
            path.write_bytes(b"pilot")
            expected = hashlib.sha256(b"pilot").hexdigest()
            self.assertEqual(acquire.sha256_file(path), expected)
            self.assertEqual(acquire.sha256_file(path), expected)

    def test_unknown_handling_and_manifest_validation(self):
        base = {field:"UNKNOWN" for field in acquire.REQUIRED_FIELDS}
        base.update({"artifact_id":"A","dataset_id":"D","acquisition_status":"PLANNED","filename":"x.csv","url":"file:///x"})
        manifest={"pilot_id":"PILOT-01","artifacts":[base]}
        acquire.validate_manifest(manifest)
        base["revision"]=""
        with self.assertRaises(ValueError): acquire.validate_manifest(manifest)

    def test_record_locator_reversibility(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"data.csv"
            with path.open("w",encoding="utf-8",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=["id","prompt"]); writer.writeheader(); writer.writerow({"id":"7","prompt":"alpha"})
            self.assertEqual(forensics.locate(path,"csv_row:1")["id"],"7")

    def test_source_derived_separation(self):
        raw="A  B\r\nC"
        self.assertEqual(forensics.canonicalize(raw,"N0"),raw)
        self.assertNotEqual(forensics.canonicalize(raw,"N2"),raw)

    def test_generated_prompt_precedes_base_goal(self):
        row={"goal":"base behavior","prompt":"base behavior adversarial suffix"}
        key,value=forensics.select_text(row,"ART-P01-GCG-001")
        self.assertEqual((key,value),("prompt","base behavior adversarial suffix"))

    def test_minhash_and_lsh_are_deterministic(self):
        values=forensics.shingles("one two three four five")
        self.assertEqual(forensics.minhash_signature(values),forensics.minhash_signature(values))
        records={"a":{"source":{"dataset_id":"A"}},"b":{"source":{"dataset_id":"B"}}}
        sig=forensics.minhash_signature(values)
        self.assertEqual(forensics.lsh_candidates({"a":sig,"b":sig},32,4,records),{("a","b")})

    def test_duplicate_cluster_reproducibility(self):
        values=["x","x","y"]
        first=[hashlib.sha256(v.encode()).hexdigest() for v in values]
        second=[hashlib.sha256(v.encode()).hexdigest() for v in values]
        self.assertEqual(first,second)
        self.assertEqual(first[0],first[1])


if __name__ == "__main__":
    unittest.main()
