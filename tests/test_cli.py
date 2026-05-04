from __future__ import annotations

from typer.testing import CliRunner

from podcast import app

runner = CliRunner()


def test_help_shows_all_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for sub in [
        "transcribe", "subtitle", "label", "status",
        "moments", "thumbnail", "describe", "linkedin", "chapters",
        "publish-youtube", "publish-spotify",
    ]:
        assert sub in result.stdout, f"Missing subcommand in help: {sub}"


def test_moments_stub_exits_zero(tmp_path) -> None:
    (tmp_path / "Episode99").mkdir()
    result = runner.invoke(app, ["moments", str(tmp_path / "Episode99")])
    assert result.exit_code == 0
    assert "not implemented yet" in result.stdout


def test_status_on_missing_folder_exits_2(tmp_path) -> None:
    result = runner.invoke(app, ["status", str(tmp_path / "Episode404")])
    assert result.exit_code == 2
