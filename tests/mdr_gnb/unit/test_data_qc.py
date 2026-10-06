"""数据 QC(阶段 2.3):冲突标签检测正确 + 冲突率低(数据可用于建模)。"""
from praxis_virtualcell.mdr_gnb.workflows.run_data_qc import qc_species


def test_qc_detects_and_data_is_clean():
    for sp in ("escherichia_coli", "klebsiella_pneumoniae"):
        q = qc_species(sp)
        assert q["n_rows"] > 1000
        assert q["n_missing_genotype"] == 0            # 无缺基因型
        assert len(q["nonstandard_phenotypes"]) == 0   # 无非标准 phenotype 值
        # 冲突标签率(冲突 / genome×药 键总数)必须很低(<1%),否则训练标签噪声过大
        rate = q["n_conflicting_label_keys"] / max(1, q["n_label_keys"])
        assert rate < 0.01, f"{sp} 冲突标签率 {rate:.4f} 过高"
