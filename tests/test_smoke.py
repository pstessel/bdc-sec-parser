def test_import():
    import bdc_sched  # noqa: F401


import json


def test_run_metadata_shape():
    from bdc_sched.cli import _new_run_metadata

    meta = _new_run_metadata("parse")
    assert set(meta.keys()) == {"run_id", "generated_at", "parser_version"}
    assert meta["run_id"].startswith("parse_")
    assert meta["generated_at"].endswith("Z")


def test_write_run_manifest(tmp_path):
    from bdc_sched.cli import _new_run_metadata, _write_run_manifest

    meta = _new_run_metadata("parse")
    out = _write_run_manifest(
        tmp_path,
        "parse",
        meta,
        {"input": {"raw_dir": "x"}, "output": {"rows": 10}},
    )

    assert out.name == "parse_run_manifest.json"
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["stage"] == "parse"
    assert body["run_id"] == meta["run_id"]
    assert body["output"]["rows"] == 10
