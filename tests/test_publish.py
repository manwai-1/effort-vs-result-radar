import subprocess

from scanner.cli import main
from scanner.models import ScanError
from scanner.publish import git_publish, publish_allowed


def test_publish_gate_refuses_local_and_fixture_runs(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    try:
        publish_allowed(fixture_mode=False)
        refused = None
    except ScanError as exc:
        refused = exc
    assert refused is not None
    assert refused.code == 4
    assert "Refusing to publish" in str(refused)

    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "manwai-1/effort-vs-result-radar")
    try:
        publish_allowed(fixture_mode=True)
        refused = None
    except ScanError as exc:
        refused = exc
    assert refused is not None
    assert refused.code == 4
    assert "--bars" in str(refused)


def test_cli_push_does_not_write_or_commit_locally(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    radar = tmp_path / "radar.json"
    history = tmp_path / "history.json"
    before = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
    code = main(
        [
            "--push",
            "--bars",
            "tests/fixtures/mini_bars.json",
            "--watchlist",
            "tests/fixtures/mini_watchlist.json",
            "--radar",
            str(radar),
            "--history",
            str(history),
            "--now",
            "2026-11-27T15:00:00-05:00",
        ]
    )
    captured = capsys.readouterr()
    assert code == 4
    assert "Refusing to publish" in captured.err
    assert not radar.exists()
    assert not history.exists()
    after = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
    assert before.stdout == after.stdout


def test_git_publish_commits_and_pushes_without_force(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    target = tmp_path / "public" / "data" / "history_results.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    env_commit = ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "init"]
    subprocess.run(env_commit, cwd=tmp_path, check=True, capture_output=True)
    target.write_text('{"updated": true}\n', encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "manwai-1/effort-vs-result-radar")
    pushed: list[list[str]] = []
    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if isinstance(cmd, list) and cmd[:1] == ["git"] and "push" in cmd:
            pushed.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr("scanner.publish.subprocess.run", fake_run)
    git_publish(tmp_path, [target], "scan: update radar and history ledger")
    assert len(pushed) == 1
    assert pushed[0][-1] == "push"
    assert "--force" not in pushed[0]
    assert "force" not in " ".join(pushed[0])
    log = real_run(
        ["git", "-C", str(tmp_path), "log", "-1", "--format=%s"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert log.stdout.strip() == "scan: update radar and history ledger"


def test_actions_fixture_push_is_refused_before_write(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "manwai-1/effort-vs-result-radar")
    radar = tmp_path / "radar.json"
    code = main(
        [
            "--push",
            "--bars",
            "tests/fixtures/mini_bars.json",
            "--watchlist",
            "tests/fixtures/mini_watchlist.json",
            "--radar",
            str(radar),
            "--history",
            str(tmp_path / "history.json"),
            "--now",
            "2026-11-27T15:00:00-05:00",
        ]
    )
    captured = capsys.readouterr()
    assert code == 4
    assert "--bars" in captured.err
    assert not radar.exists()
