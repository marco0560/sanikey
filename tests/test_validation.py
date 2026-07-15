"""Repository validation command tests."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


def _load_script_module(script_name: str, module_name: str) -> ModuleType:
    """Load a repository script as a test module.

    Parameters
    ----------
    script_name : str
        Script file name under ``scripts/``.
    module_name : str
        Synthetic module name used for the import.

    Returns
    -------
    types.ModuleType
        Loaded script module.

    Raises
    ------
    AssertionError
        If the script import specification cannot be created.
    """

    script = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        message = f"impossibile caricare scripts/{script_name}"
        raise AssertionError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_repo_includes_privacy_guard() -> None:
    """Verify standard validation starts with privacy and Codira checks.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    validate_repo = _load_script_module("validate_repo.py", "validate_repo")
    commands = validate_repo.build_validation_commands(python="python")

    assert commands[0][-1] == "scripts/privacy_guard.py"
    assert commands[1][-2:] == ("codira", "index")
    assert commands[2][-2:] == ("codira", "audit")


def test_validate_repo_render_run_and_main(
    monkeypatch: object,
    capsys: object,
) -> None:
    """Verify validation command rendering, execution and CLI branches.

    Parameters
    ----------
    monkeypatch : object
        Pytest monkeypatch fixture.
    capsys : object
        Pytest capture fixture.

    Returns
    -------
    None
    """

    validate_repo = _load_script_module("validate_repo.py", "validate_repo")
    commands = (("python", "tool.py", "ok"), ("python", "tool.py", "fail"))
    calls: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], *, cwd: Path, check: bool) -> object:
        calls.append(command)
        return subprocess.CompletedProcess(command, 1 if command[-1] == "fail" else 0)

    monkeypatch.setattr(validate_repo.subprocess, "run", fake_run)

    assert validate_repo.run_validation(commands) == 1
    assert calls == list(commands)

    rendered = validate_repo.render_validation_commands((("python", "a b.py"),))
    assert rendered == "python 'a b.py'"

    monkeypatch.setattr(
        validate_repo,
        "build_validation_commands",
        lambda: (("python", "scripts/run_repo_tool.py", "ruff", "check", "."),),
    )
    assert validate_repo.main(["--dry-run"]) == 0
    assert "scripts/run_repo_tool.py" in capsys.readouterr().out

    monkeypatch.setattr(validate_repo, "run_validation", lambda commands: len(commands))
    assert validate_repo.main([]) == 1


def test_validate_repo_run_validation_defaults(monkeypatch: object) -> None:
    """Verify ``run_validation`` builds default commands when omitted.

    Parameters
    ----------
    monkeypatch : object
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    validate_repo = _load_script_module("validate_repo.py", "validate_repo")
    monkeypatch.setattr(validate_repo, "build_validation_commands", lambda: (("ok",),))
    monkeypatch.setattr(
        validate_repo.subprocess,
        "run",
        lambda command, *, cwd, check: subprocess.CompletedProcess(command, 0),
    )

    assert validate_repo.run_validation() == 0


def test_run_repo_tool_path_state_and_environment(tmp_path: Path) -> None:
    """Verify path containment, state root and redirected environment.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    run_repo_tool = _load_script_module("run_repo_tool.py", "run_repo_tool")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    assert run_repo_tool.path_is_inside(repo_root, repo_root)
    assert run_repo_tool.path_is_inside(repo_root / "src", repo_root)
    assert not run_repo_tool.path_is_inside(tmp_path / "other", repo_root)

    state_root = run_repo_tool.tool_state_root(repo_root, temp_root=tmp_path / "tmp")
    assert state_root.parent.name == "sanikey-tool-state"
    assert state_root.name.startswith("repo-")

    try:
        run_repo_tool.tool_state_root(repo_root, temp_root=repo_root / "tmp")
    except run_repo_tool.ToolStateInsideRepositoryError as exc:
        assert str(repo_root / "tmp") in str(exc)
    else:
        message = "tool_state_root deve rifiutare temp_root dentro il repo"
        raise AssertionError(message)

    env = run_repo_tool.tool_environment({"PATH": "x"}, state_root=state_root)
    assert env["PATH"] == "x"
    assert env["SANIKEY_TOOL_STATE_ROOT"] == str(state_root)
    assert env["COVERAGE_FILE"] == str(state_root / "coverage" / ".coverage")
    assert env["TMPDIR"] == str(state_root / "tmp")

    pytest_basetemp = run_repo_tool.create_pytest_basetemp(state_root)
    assert pytest_basetemp.parent == state_root / "tmp"
    assert not pytest_basetemp.exists()


def test_run_repo_tool_build_tool_argv_variants(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    """Verify argv construction for supported wrapper variants.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : object
        Pytest monkeypatch fixture.

    Returns
    -------
    None
    """

    run_repo_tool = _load_script_module("run_repo_tool.py", "run_repo_tool")
    python = str(tmp_path / "venv" / "bin" / "python")

    assert run_repo_tool.build_tool_argv(
        "python",
        ("script.py",),
        state_root=tmp_path,
        python=python,
    ) == (python, "script.py")
    assert run_repo_tool.build_tool_argv(
        "mypy",
        ("src",),
        state_root=tmp_path,
        python=python,
    ) == (python, "-m", "mypy", "src")
    assert run_repo_tool.build_tool_argv(
        "ruff",
        ("check", "."),
        state_root=tmp_path,
        python=python,
    ) == (python, "-m", "ruff", "check", "--cache-dir", str(tmp_path / "ruff"), ".")
    assert run_repo_tool.build_tool_argv(
        "pytest",
        ("tests",),
        state_root=tmp_path,
        python=python,
        pytest_basetemp=tmp_path / "pytest-base",
    ) == (
        python,
        "-m",
        "pytest",
        "-o",
        f"cache_dir={tmp_path / 'pytest-cache'}",
        "--basetemp",
        str(tmp_path / "pytest-base"),
        "tests",
    )

    monkeypatch.setattr(run_repo_tool.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert (
        run_repo_tool.resolve_python_sibling_executable(
            "codira",
            python=python,
        )
        == "/usr/bin/codira"
    )
    monkeypatch.setattr(run_repo_tool.shutil, "which", lambda _name: None)
    assert run_repo_tool.resolve_python_sibling_executable(
        "missing", python=python
    ) == ("missing")

    try:
        run_repo_tool.build_tool_argv(
            "unknown",
            (),
            state_root=tmp_path,
            python=python,
        )
    except run_repo_tool.UnsupportedToolError as exc:
        assert "Unsupported tool 'unknown'" in str(exc)
    else:
        message = "build_tool_argv deve rifiutare tool non supportati"
        raise AssertionError(message)

    run_repo_tool.SUPPORTED_TOOLS["dummy"] = None
    try:
        run_repo_tool.build_tool_argv(
            "dummy",
            (),
            state_root=tmp_path,
            python=python,
        )
    except run_repo_tool.UnsupportedToolError as exc:
        assert "Unsupported tool 'dummy'" in str(exc)
    else:
        message = "build_tool_argv deve rifiutare tool senza modulo"
        raise AssertionError(message)


def test_run_repo_tool_supports_codira_console_script(tmp_path: Path) -> None:
    """Verify the repository tool wrapper can invoke Codira.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
    """

    run_repo_tool = _load_script_module("run_repo_tool.py", "run_repo_tool")
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    python = bin_dir / "python"
    codira = bin_dir / "codira"
    python.write_text("", encoding="utf-8")
    codira.write_text("", encoding="utf-8")

    argv = run_repo_tool.build_tool_argv(
        "codira",
        ("audit",),
        state_root=tmp_path,
        python=str(python),
    )

    assert argv == (str(codira), "audit")


def test_run_repo_tool_output_parse_and_main(
    tmp_path: Path,
    monkeypatch: object,
    capsys: object,
) -> None:
    """Verify output replay, argument parsing and main orchestration.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    monkeypatch : object
        Pytest monkeypatch fixture.
    capsys : object
        Pytest capture fixture.

    Returns
    -------
    None
    """

    run_repo_tool = _load_script_module("run_repo_tool.py", "run_repo_tool")
    completed = subprocess.CompletedProcess(
        ("tool",),
        0,
        stdout="out\n",
        stderr="err\n",
    )

    run_repo_tool.replay_completed_output(completed)
    captured = capsys.readouterr()
    assert captured.out == "out\n"
    assert captured.err == "err\n"

    monkeypatch.setattr(sys, "argv", ["run_repo_tool.py", "ruff", "check", "."])
    parsed = run_repo_tool.parse_args()
    assert parsed.tool == "ruff"
    assert parsed.tool_args == ["check", "."]

    monkeypatch.setattr(
        run_repo_tool,
        "parse_args",
        lambda: SimpleNamespace(tool="pre-commit-noncode", tool_args=("run",)),
    )
    monkeypatch.setattr(run_repo_tool, "tool_state_root", lambda _repo_root: tmp_path)
    captured_env: dict[str, str] = {}
    captured_argv: list[tuple[str, ...]] = []

    def fake_build_tool_argv(
        tool: str,
        tool_args: tuple[str, ...],
        *,
        state_root: Path,
        python: str,
    ) -> tuple[str, ...]:
        captured_argv.append((tool, *tool_args, str(state_root), python))
        return ("wrapped-tool",)

    def fake_run(
        argv: tuple[str, ...],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
    ) -> object:
        captured_env.update(env)
        return subprocess.CompletedProcess(argv, 7)

    monkeypatch.setattr(run_repo_tool, "build_tool_argv", fake_build_tool_argv)
    monkeypatch.setattr(run_repo_tool.subprocess, "run", fake_run)

    assert run_repo_tool.main() == 7
    assert captured_env["SKIP"] == "ruff,ruff-format,mypy"
    assert captured_argv[0][0:2] == ("pre-commit-noncode", "run")
