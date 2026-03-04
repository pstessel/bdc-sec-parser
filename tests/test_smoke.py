def test_import():
    import bdc_sched  # noqa: F401


def test_run_metadata_shape():
    from bdc_sched.cli import _new_run_metadata

    meta = _new_run_metadata("parse")
    assert set(meta.keys()) == {"run_id", "generated_at", "parser_version"}
    assert meta["run_id"].startswith("parse_")
    assert meta["generated_at"].endswith("Z")
