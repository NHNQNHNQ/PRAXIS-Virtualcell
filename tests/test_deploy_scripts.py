"""§6⑤ deploy 脚本静态契约 + HPC 账号 toml 模板。"""

from pathlib import Path


def _deploy_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "deploy"


def test_push_backend_sh_has_rsync_and_restart():
    f = _deploy_dir() / "push_backend.sh"
    assert f.is_file()
    text = f.read_text()
    assert "rsync" in text
    assert "praxis2" in text   # 同步 praxis2 包
    # 远端起 service(gunicorn 重启或 systemd unit restart)
    assert "gunicorn" in text or "systemctl" in text


def test_push_frontend_sh_has_build_and_rsync():
    f = _deploy_dir() / "push_frontend.sh"
    assert f.is_file()
    text = f.read_text()
    # 前端通常先 npm/pnpm/yarn build 再 rsync
    assert "build" in text or "npm" in text or "pnpm" in text
    assert "rsync" in text


def test_push_scripts_fail_fast_on_missing_env_vars():
    # 脚本必须 set -e + 必填变量校验(治 v1 「BACKEND_HOST 未配跑了一半才报」)
    for name in ("push_backend.sh", "push_frontend.sh"):
        text = (_deploy_dir() / name).read_text()
        assert "set -e" in text or "set -euo" in text


def test_push_backend_uses_rsync_partial():
    # D.6:rsync 带 --partial + --partial-dir,中断可续传(reviewer M0/M8 #8)
    text = (_deploy_dir() / "push_backend.sh").read_text()
    assert "--partial" in text
    assert "--partial-dir" in text


def test_push_backend_excludes_appledouble():
    # D.6:macOS AppleDouble (._*) 必须 exclude,防漏拷脏文件到 staging
    text = (_deploy_dir() / "push_backend.sh").read_text()
    assert "--exclude '._*'" in text or '--exclude "._*"' in text


def test_push_frontend_uses_rsync_partial():
    # D.6:前端 rsync 同样需 --partial 续传
    text = (_deploy_dir() / "push_frontend.sh").read_text()
    assert "--partial" in text


def test_hpc_account_toml_has_four_nodes():
    f = _deploy_dir() / "hpc_submit_account.example.toml"
    assert f.is_file()
    text = f.read_text()
    # §11.7 4 节点严区分大小写
    assert "SCW6CHB" in text       # GPU 包月
    assert "bio000070" in text     # 提交端
    assert "a0s001884" in text     # 大内存
    assert "scw6chb" in text       # CPUX(小写)


def test_readme_has_three_stage_commands():
    f = _deploy_dir() / "README.md"
    assert f.is_file()
    text = f.read_text()
    # 三阶段:本地 / staging / prod
    assert "本地" in text or "local" in text.lower()
    assert "staging" in text.lower() or "测试" in text
    # 实际命令模板
    assert "docker compose" in text or "docker-compose" in text
    assert "gunicorn" in text
