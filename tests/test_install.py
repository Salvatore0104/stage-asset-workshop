import argparse
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workshop_install", ROOT / "scripts/install.py")
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)


def args(target, **extra):
    values = dict(target=target, name="测试节目", id="test_show", width=640, height=360, duration=8, fps=25, bpm=120,
                  mask=None, mask_channel="luminance", mask_invert=False, audio=None, style="纸片", skip_wowidea=False)
    values.update(extra)
    return argparse.Namespace(**values)


class InstallTests(unittest.TestCase):
    def test_official_install_command_selects_platform_script(self):
        posix = install.official_install_command("linux")
        self.assertEqual(posix[0], "bash")
        self.assertIn("scripts/install.sh", posix[-1])
        self.assertIn("curl -fsSL", posix[-1])
        windows = install.official_install_command("win32")
        self.assertEqual(windows[0], "powershell")
        self.assertIn("scripts/install.ps1", windows[-1])
        self.assertIn("irm ", windows[-1])
        self.assertIn("| iex", windows[-1])

    def test_existing_cli_skips_official_installer(self):
        calls = []
        with patch.object(install.workshop, "find_wowidea", return_value=["/usr/local/bin/wowidea"]):
            found = install.ensure_wowidea_cli(skip=False, runner=lambda *a, **k: calls.append(a))
        self.assertEqual(found, ["/usr/local/bin/wowidea"])
        self.assertEqual(calls, [])

    def test_missing_cli_runs_official_installer(self):
        calls = []
        seen = {"n": 0}

        def finder():
            seen["n"] += 1
            return None if seen["n"] == 1 else ["wowidea"]

        def runner(command, check):
            calls.append(command)
            self.assertTrue(check)

        with patch.object(install.workshop, "find_wowidea", side_effect=finder), patch.object(install, "require_install_tools"):
            found = install.ensure_wowidea_cli(runner=runner)
        self.assertEqual(found, ["wowidea"])
        self.assertEqual(len(calls), 1)
        self.assertIn("scripts/install.sh", calls[0][-1])

    def test_missing_cli_on_windows_uses_powershell_installer(self):
        calls = []
        seen = {"n": 0}

        def finder():
            seen["n"] += 1
            return None if seen["n"] == 1 else ["wowidea.cmd"]

        with patch.object(install.workshop, "find_wowidea", side_effect=finder), patch.object(install, "require_install_tools"):
            found = install.ensure_wowidea_cli(runner=lambda command, check: calls.append(command), platform="win32")
        self.assertEqual(found, ["wowidea.cmd"])
        self.assertEqual(calls[0][0], "powershell")
        self.assertIn("scripts/install.ps1", calls[0][-1])

    def test_skip_flag_does_not_install_when_cli_is_missing(self):
        calls = []
        with patch.object(install.workshop, "find_wowidea", return_value=None):
            with self.assertRaises(RuntimeError):
                install.ensure_wowidea_cli(skip=True, runner=lambda *a, **k: calls.append(a))
        self.assertEqual(calls, [])

    def test_existing_show_skips_workshop_init(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "节目"
            show = target / "03_资产与需求" / "show.json"
            show.parent.mkdir(parents=True)
            show.write_text('{"keep":true}', encoding="utf-8")
            events = []
            with patch.object(install, "ensure_wowidea_cli", return_value=["wowidea"]), \
                 patch.object(install, "prepare_python", side_effect=lambda target, runner=None: events.append(("venv", target))), \
                 patch.object(install.workshop, "ensure_wowidea_project", side_effect=lambda target, name: events.append(("wow", target, name))), \
                 patch.object(install.workshop, "print_usage_prompt"):
                install.install_project(args(target), runner=lambda *a, **k: events.append(("run", a)))
            self.assertEqual(show.read_text(encoding="utf-8"), '{"keep":true}')
            self.assertIn(("venv", target), events)
            self.assertFalse(any(item[0] == "run" for item in events))
            self.assertEqual(events[-1][0], "wow")
            self.assertEqual(events[-1][2], "测试节目")

    def test_new_show_inits_workshop_before_wowidea_project(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "新节目"
            events = []

            def runner(command, check=True):
                events.append(list(command))

            with patch.object(install, "ensure_wowidea_cli", return_value=["wowidea"]) as cli, \
                 patch.object(install, "prepare_python", return_value=Path("/venv/bin/python")), \
                 patch.object(install.workshop, "ensure_wowidea_project", side_effect=lambda target, name: events.append(["wow", name])), \
                 patch.object(install.workshop, "print_usage_prompt", side_effect=lambda: events.append(["prompt"])):
                install.install_project(args(target), runner=runner)
            cli.assert_called_once()
            self.assertEqual(events[0][2], "init")
            self.assertIn("--name", events[0])
            self.assertIn("测试节目", events[0])
            self.assertEqual(events[1], ["wow", "测试节目"])
            self.assertEqual(events[2], ["prompt"])

    def test_already_installed_cli_still_inits_and_prints_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "节目"
            init_calls = []
            runner_calls = []

            def fake_run(command, **kwargs):
                init_calls.append(list(command))
                return "{}"

            def runner(command, check=True):
                runner_calls.append(list(command))
                self.assertTrue(check)

            buffer = io.StringIO()
            with patch.object(install.workshop, "find_wowidea", return_value=["/usr/local/bin/wowidea"]), \
                 patch.object(install, "prepare_python", return_value=Path("/venv/bin/python")), \
                 patch.object(install.workshop, "cli", return_value=["/usr/local/bin/wowidea"]), \
                 patch.object(install.workshop, "run", side_effect=fake_run), \
                 redirect_stdout(buffer):
                install.install_project(args(target), runner=runner)
            text = buffer.getvalue()
            self.assertIn("跳过安装，继续初始化项目", text)
            self.assertFalse(any("install.sh" in " ".join(command) or "install.ps1" in " ".join(command) for command in runner_calls))
            self.assertTrue(any(command[2] == "init" for command in runner_calls))
            self.assertEqual(init_calls[0][1:3], ["project", "init"])
            self.assertIn(str(target.resolve()), init_calls[0])
            self.assertIn("测试节目", init_calls[0])
            self.assertIn(install.workshop.first_install_prompt().strip(), text)
            self.assertIn("docs/prompts/首次安装.txt", text)

    def test_already_installed_cli_skips_existing_project_and_still_prints_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "节目"
            show = target / "03_资产与需求" / "show.json"
            show.parent.mkdir(parents=True)
            show.write_text('{"keep":true}', encoding="utf-8")
            marker = target / ".wowidea" / "project.json"
            marker.parent.mkdir(parents=True)
            marker.write_text('{"name":"kept"}', encoding="utf-8")
            venv_python = install.venv_python(target)
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("", encoding="utf-8")
            init_calls = []
            runner_calls = []
            buffer = io.StringIO()
            with patch.object(install.workshop, "find_wowidea", return_value=["/usr/local/bin/wowidea"]), \
                 patch.object(install, "prepare_python") as prepare, \
                 patch.object(install.workshop, "cli", return_value=["/usr/local/bin/wowidea"]), \
                 patch.object(install.workshop, "run", side_effect=lambda command, **kwargs: init_calls.append(list(command)) or "{}"), \
                 redirect_stdout(buffer):
                install.install_project(args(target), runner=lambda command, check=True: runner_calls.append(list(command)))
            self.assertEqual(marker.read_text(encoding="utf-8"), '{"name":"kept"}')
            self.assertEqual(show.read_text(encoding="utf-8"), '{"keep":true}')
            self.assertEqual(init_calls, [])
            self.assertEqual(runner_calls, [])
            prepare.assert_not_called()
            self.assertIn("跳过 project init，不会覆盖", buffer.getvalue())
            self.assertIn(install.workshop.first_install_prompt().strip(), buffer.getvalue())
            self.assertIn("docs/prompts/首次安装.txt", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
