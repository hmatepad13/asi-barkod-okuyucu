import io
import json
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

import asi_barkod_receiver as receiver


class UserDataTests(unittest.TestCase):
    def test_logs_are_created_under_appdata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}):
                expected = os.path.join(temp_dir, "AsiBarkod", "logs")
                self.assertEqual(receiver.ensure_logs_dir(), expected)
                self.assertTrue(os.path.isdir(expected))

    def test_settings_are_persisted_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}):
                receiver.save_settings({
                    "writeEnabled": False,
                    "successSoundEnabled": False,
                    "suffix": "tab",
                    "gsMode": "pipe",
                    "prefixMode": "aim_datamatrix_gs1",
                })
                self.assertEqual(receiver.load_settings(), {
                    "writeEnabled": False,
                    "successSoundEnabled": False,
                    "suffix": "TAB",
                    "gsMode": "pipe",
                    "prefixMode": "aim_datamatrix_gs1",
                })

    def test_success_sound_is_enabled_by_default(self) -> None:
        self.assertTrue(receiver.sanitize_settings({})["successSoundEnabled"])

    def test_invalid_settings_fall_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"APPDATA": temp_dir}):
                os.makedirs(receiver.user_data_dir(), exist_ok=True)
                with open(receiver.settings_path(), "w", encoding="utf-8") as handle:
                    handle.write("not-json")
                self.assertEqual(receiver.load_settings(), receiver.sanitize_settings({}))


class UpdateTests(unittest.TestCase):
    def test_version_comparison_handles_v_prefix_and_padding(self) -> None:
        self.assertTrue(receiver.is_newer_version("v0.2.1", "0.2.0"))
        self.assertFalse(receiver.is_newer_version("0.2", "0.2.0"))
        self.assertFalse(receiver.is_newer_version("bad-version", "0.2.0"))

    def test_latest_release_finds_windows_installer(self) -> None:
        payload = {
            "tag_name": "v0.5.1",
            "html_url": "https://github.com/example/releases/tag/v0.5.1",
            "body": "## Windows\n- Güncelleme notları eklendi.",
            "assets": [
                {
                    "name": "Asi-Barkod-Windows-Kurulum-v0.5.1.exe",
                    "browser_download_url": "https://example.test/installer.exe",
                }
            ],
        }
        tls_context = object()
        with mock.patch.object(receiver, "github_ssl_context", return_value=tls_context), mock.patch.object(
            receiver.urllib.request,
            "urlopen",
            return_value=io.BytesIO(json.dumps(payload).encode("utf-8")),
        ) as urlopen:
            info = receiver.fetch_latest_release()

        self.assertTrue(info.is_newer)
        self.assertEqual(info.version, "0.5.1")
        self.assertEqual(info.filename, "Asi-Barkod-Windows-Kurulum-v0.5.1.exe")
        self.assertEqual(info.download_url, "https://example.test/installer.exe")
        self.assertEqual(info.notes, "Windows\n- Güncelleme notları eklendi.")
        self.assertIs(urlopen.call_args.kwargs["context"], tls_context)

    def test_pwa_release_requires_a_release_value(self) -> None:
        tls_context = object()
        with mock.patch.object(receiver, "github_ssl_context", return_value=tls_context), mock.patch.object(
            receiver.urllib.request,
            "urlopen",
            return_value=io.BytesIO(b'{"release":"2026.08.05.3"}'),
        ) as urlopen:
            self.assertEqual(receiver.fetch_pwa_release(), "2026.08.05.3")
        self.assertIn("api/release", urlopen.call_args.args[0].full_url)
        self.assertIs(urlopen.call_args.kwargs["context"], tls_context)

    def test_release_notes_have_fallback_and_length_limit(self) -> None:
        self.assertEqual(receiver.format_release_notes(""), "Sürüm notu bulunmuyor.")
        self.assertEqual(receiver.format_release_notes("# Başlık\n- Madde"), "Başlık\n- Madde")
        self.assertEqual(receiver.format_release_notes("123456", max_length=5), "12...")

    def test_update_error_opens_release_page(self) -> None:
        app = receiver.ReceiverApp.__new__(receiver.ReceiverApp)
        app.message_queue = receiver.queue.Queue()
        app.message_queue.put(("update_error", "certificate verify failed"))
        app.update_button = mock.MagicMock()
        app.status_var = mock.MagicMock()
        app.root = mock.MagicMock()
        app.next_network_check = float("inf")

        fake_messagebox = mock.MagicMock()
        fake_tk = mock.MagicMock()
        fake_tk.NORMAL = "normal"
        with mock.patch.object(receiver, "tk", fake_tk), mock.patch.object(
            receiver,
            "messagebox",
            fake_messagebox,
        ), mock.patch.object(
            receiver.webbrowser,
            "open",
            return_value=True,
        ) as open_browser:
            app.pump_messages()

        open_browser.assert_called_once_with(receiver.RELEASES_URL)


class KeyboardWriterTests(unittest.TestCase):
    def test_fixed_delay_is_applied_after_every_character(self) -> None:
        writer = receiver.KeyboardWriter.__new__(receiver.KeyboardWriter)
        writer._send_unicode_char = mock.Mock()
        writer._send_group_separator = mock.Mock()
        writer._send_vk = mock.Mock()
        writer.user32 = mock.Mock()
        writer.user32.GetKeyState.return_value = 0

        with mock.patch.object(receiver.time, "sleep") as sleep:
            writer.send_text("AB", "f8")

        self.assertEqual(writer._send_unicode_char.call_args_list, [mock.call("A"), mock.call("B")])
        self.assertEqual(sleep.call_args_list, [mock.call(0.005), mock.call(0.005)])

    def test_altgr_modifiers_are_pressed_and_released(self) -> None:
        writer = receiver.KeyboardWriter.__new__(receiver.KeyboardWriter)
        writer.user32 = mock.Mock()
        writer.user32.VkKeyScanW.return_value = ord("I") | (0x06 << 8)
        writer.user32.GetKeyState.return_value = 0
        writer._send_inputs = mock.Mock()

        writer._send_unicode_char("i")

        inputs = writer._send_inputs.call_args.args[0]
        self.assertEqual(
            [item.union.ki.wVk for item in inputs],
            [writer.VK_CONTROL, writer.VK_MENU, ord("I"), ord("I"), writer.VK_MENU, writer.VK_CONTROL],
        )
        self.assertEqual(inputs[3].union.ki.dwFlags, writer.KEYEVENTF_KEYUP)

    def test_caps_lock_is_temporarily_disabled_while_writing(self) -> None:
        writer = receiver.KeyboardWriter.__new__(receiver.KeyboardWriter)
        writer.user32 = mock.Mock()
        writer.user32.GetKeyState.return_value = 1
        writer._send_unicode_char = mock.Mock()
        writer._send_group_separator = mock.Mock()
        writer._send_vk = mock.Mock()

        with mock.patch.object(receiver.time, "sleep"):
            writer.send_text("a", "f8")

        self.assertEqual(writer._send_vk.call_args_list, [mock.call(writer.VK_CAPITAL), mock.call(writer.VK_CAPITAL)])
        writer._send_unicode_char.assert_called_once_with("a")


class TrayTests(unittest.TestCase):
    @unittest.skipUnless(receiver.TRAY_AVAILABLE, "pystray/Pillow not installed")
    def test_tray_image_has_expected_size(self) -> None:
        app = receiver.ReceiverApp.__new__(receiver.ReceiverApp)
        image = app.tray_image()
        self.assertEqual(image.size, (64, 64))
        self.assertEqual(image.mode, "RGBA")

    def test_tray_callbacks_are_forwarded_to_gui_queue(self) -> None:
        app = receiver.ReceiverApp.__new__(receiver.ReceiverApp)
        app.message_queue = receiver.queue.Queue()
        app.request_show_window()
        app.request_exit_application()
        self.assertEqual(app.message_queue.get_nowait(), ("show_window", None))
        self.assertEqual(app.message_queue.get_nowait(), ("exit_application", None))


def configured_gui_app(write_enabled: bool = True) -> receiver.ReceiverApp:
    app = receiver.ReceiverApp.__new__(receiver.ReceiverApp)
    app.suffix_var = mock.Mock(get=mock.Mock(return_value="ENTER"))
    app.write_enabled_var = mock.Mock(get=mock.Mock(return_value=write_enabled))
    app.success_sound_enabled_var = mock.Mock(get=mock.Mock(return_value=True))
    app.gs_mode_var = mock.Mock(get=mock.Mock(return_value="f8"))
    app.prefix_mode_var = mock.Mock(get=mock.Mock(return_value="none"))
    app.writer = mock.Mock()
    app.last_event = None
    app.last_error = ""
    app.scan_count = 0
    app.history = []
    app.scan_lock = threading.Lock()
    app.message_queue = receiver.queue.Queue()
    app.log_event = mock.Mock()
    return app


class ScanHandlingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.beep_patcher = mock.patch.object(receiver, "play_success_beep")
        self.play_success_beep = self.beep_patcher.start()

    def tearDown(self) -> None:
        self.beep_patcher.stop()

    def test_gui_scan_still_writes_when_logging_fails(self) -> None:
        app = configured_gui_app()
        app.log_event.side_effect = PermissionError("log denied")
        event = receiver.test_event("0108699839961105")

        self.assertTrue(app.handle_scan(event))
        app.writer.send_text.assert_called_once_with(event.data, "f8")
        app.writer.send_suffix.assert_called_once_with("ENTER")
        self.assertEqual(app.scan_count, 1)
        self.assertIn("log denied", app.last_error)
        self.play_success_beep.assert_called_once_with()

    def test_pc_suffix_setting_overrides_phone_payload(self) -> None:
        app = configured_gui_app()
        app.suffix_var.get.return_value = "TAB"
        event = receiver.test_event("ABC")
        event.suffix = "ENTER"

        self.assertTrue(app.handle_scan(event))
        app.writer.send_suffix.assert_called_once_with("TAB")

    def test_beep_is_not_played_when_keyboard_write_fails(self) -> None:
        app = configured_gui_app()
        app.writer.send_text.side_effect = OSError("write failed")

        self.assertFalse(app.handle_scan(receiver.test_event("ABC")))
        self.play_success_beep.assert_not_called()

    def test_beep_can_be_disabled_in_settings(self) -> None:
        app = configured_gui_app()
        app.success_sound_enabled_var.get.return_value = False

        self.assertTrue(app.handle_scan(receiver.test_event("ABC")))
        self.play_success_beep.assert_not_called()

    def test_concurrent_scans_do_not_interleave_keyboard_writes(self) -> None:
        class SlowWriter:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def send_text(self, data: str, gs_mode: str) -> None:
                self.calls.append(f"text:{data}")
                time.sleep(0.02)

            def send_suffix(self, suffix: str) -> None:
                self.calls.append(f"suffix:{suffix}")

        app = configured_gui_app()
        app.writer = SlowWriter()
        threads = [threading.Thread(target=app.handle_scan, args=(receiver.test_event(value),)) for value in ("A", "B")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertIn(app.writer.calls, [
            ["text:A", "suffix:ENTER", "text:B", "suffix:ENTER"],
            ["text:B", "suffix:ENTER", "text:A", "suffix:ENTER"],
        ])


class SingleInstanceTests(unittest.TestCase):
    def test_show_existing_instance_signals_the_windows_event(self) -> None:
        kernel32 = mock.MagicMock()
        kernel32.OpenEventW.return_value = 123
        with mock.patch.object(receiver.sys, "platform", "win32"), mock.patch.object(
            receiver.ctypes,
            "WinDLL",
            return_value=kernel32,
        ):
            self.assertTrue(receiver.show_existing_instance())
        kernel32.SetEvent.assert_called_once()
        kernel32.CloseHandle.assert_called_once()


if __name__ == "__main__":
    unittest.main()
