from praxis2.md.sim_params import validate_sim_params


def test_standard_no_extras_ok():
    err = validate_sim_params("standard", {})
    assert err is None


def test_standard_ignores_extra_fields():
    """standard 不要 sim_params,有多余字段也不报错(宽松)。"""
    err = validate_sim_params("standard", {"foo": "bar"})
    assert err is None


def test_smd_missing_pull_rate():
    err = validate_sim_params("smd_pulling", {
        "pull_coord_geometry": "distance",
        "pull_k1": 1000,
        "pull_group1_name": "A",
        "pull_group2_name": "B",
        # 缺 pull_rate
    })
    assert err == "missing: pull_rate"


def test_smd_all_required_ok():
    err = validate_sim_params("smd_pulling", {
        "pull_coord_geometry": "distance",
        "pull_rate": 0.01,
        "pull_k1": 1000,
        "pull_group1_name": "A",
        "pull_group2_name": "B",
    })
    assert err is None


def test_smd_pull_rate_must_be_number():
    err = validate_sim_params("smd_pulling", {
        "pull_coord_geometry": "distance",
        "pull_rate": "fast",   # 应是数
        "pull_k1": 1000,
        "pull_group1_name": "A",
        "pull_group2_name": "B",
    })
    assert err == "type: pull_rate"


def test_metadynamics_missing_plumed():
    err = validate_sim_params("metadynamics", {})
    assert err == "missing: plumed_file_id"


def test_metadynamics_ok():
    err = validate_sim_params("metadynamics", {
        "plumed_file_id": "550e8400-e29b-41d4-a716-446655440000",
    })
    assert err is None


def test_unknown_sim_type():
    err = validate_sim_params("umbrella", {})
    assert err == "unsupported_sim_type"
