import importlib.util
from pathlib import Path
import runpy
import subprocess
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "getnonce.py"
spec = importlib.util.spec_from_file_location("getnonce", SCRIPT)
getnonce = importlib.util.module_from_spec(spec)
with patch("atexit.register"), patch("signal.signal"):
    spec.loader.exec_module(getnonce)


class DeviceWaitTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.patches = [
            patch.object(getnonce.time, "monotonic", side_effect=lambda: self.now),
            patch.object(getnonce.time, "sleep", side_effect=self.sleep),
            patch.object(getnonce, "print"),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def sleep(self, seconds):
        self.now += seconds

    def test_device_available_in_each_mode(self):
        for mode, command in (
            ("normal", ("idevicediagnostics", "diagnostics")),
            ("recovery", ("irecovery", "-m")),
        ):
            with self.subTest(mode=mode), patch.object(getnonce, "run_process", return_value="ready") as run:
                getnonce.wait_for_device(mode)
                run.assert_called_once_with(*command, silence_errors=True, timeout=5)
                self.assertEqual(self.now, 0)

    def test_retries_in_each_mode(self):
        for mode in ("normal", "recovery"):
            with self.subTest(mode=mode), patch.object(getnonce, "run_process", side_effect=[None, "ready"]) as run:
                before = self.now
                getnonce.wait_for_device(mode)
                self.assertEqual(run.call_count, 2)
                self.assertEqual(self.now - before, 1)

    def test_timeout_in_each_mode(self):
        for mode in ("normal", "recovery"):
            with self.subTest(mode=mode), patch.object(getnonce, "run_process", return_value=None):
                before = self.now
                with self.assertRaises(SystemExit) as error:
                    getnonce.wait_for_device(mode, timeout=2)
                self.assertEqual(error.exception.code, 1)
                self.assertEqual(self.now - before, 2)
                self.assertIn(f"waiting for device in {mode} mode", getnonce.print.call_args.args[0])

    def test_probe_and_sleep_respect_remaining_time(self):
        with patch.object(getnonce, "run_process", return_value=None) as run:
            with self.assertRaises(SystemExit):
                getnonce.wait_for_device("recovery", timeout=0.25)
            run.assert_called_once_with("irecovery", "-m", silence_errors=True, timeout=0.25)
            self.assertEqual(self.now, 0.25)

    def test_hung_probe_is_bounded_by_deadline(self):
        def hung_probe(command, *args, **kwargs):
            self.now += kwargs["timeout"]
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        with patch.object(getnonce.subprocess, "run", side_effect=hung_probe) as run:
            with self.assertRaises(SystemExit):
                getnonce.wait_for_device("normal", timeout=7)
            self.assertEqual([call.kwargs["timeout"] for call in run.call_args_list], [5, 1])
            self.assertEqual(self.now, 7)

    def test_default_timeout(self):
        with patch.object(getnonce, "run_process", return_value=None):
            with self.assertRaises(SystemExit):
                getnonce.wait_for_device("normal")
            self.assertEqual(self.now, 120)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            getnonce.wait_for_device("invalid")


class DependencyTests(unittest.TestCase):
    def test_missing_ideviceenterrecovery_exits_before_device_commands(self):
        def which(binary):
            return None if binary == "ideviceenterrecovery" else f"/usr/bin/{binary}"

        with patch("atexit.register"), patch("signal.signal"), patch("shutil.which", side_effect=which), \
                patch("rich.console.Console.print") as output, patch("subprocess.run") as run, \
                patch("rich.prompt.Confirm.ask") as ask, patch.dict("os.environ"):
            with self.assertRaises(SystemExit) as error:
                runpy.run_path(str(SCRIPT), run_name="__main__")
            self.assertEqual(error.exception.code, 1)
            self.assertIn("ideviceenterrecovery not found", output.call_args.args[0])
            run.assert_not_called()
            ask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
