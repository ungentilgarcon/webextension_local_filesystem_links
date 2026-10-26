import importlib.util
import io
import json
import ntpath
import posixpath
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


HOST_PATH = Path(__file__).parents[1] / "src" / "local-link-messaging-host.py"
NATIVE_HOST_DIR = HOST_PATH.parent
SPEC = importlib.util.spec_from_file_location("local_messaging_host", HOST_PATH)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)
BIN_TYPE_PATH = HOST_PATH.with_name("get_binary_type.py")
BIN_TYPE_SPEC = importlib.util.spec_from_file_location("get_binary_type", BIN_TYPE_PATH)
binary_type = importlib.util.module_from_spec(BIN_TYPE_SPEC)
BIN_TYPE_SPEC.loader.exec_module(binary_type)


class ChunkedReader:
    def __init__(self, data, max_chunk_size=2):
        self.data = io.BytesIO(data)
        self.max_chunk_size = max_chunk_size

    def read(self, size=-1):
        if size < 0:
            size = self.max_chunk_size
        return self.data.read(min(size, self.max_chunk_size))


class NativeHostTests(unittest.TestCase):
    def setUp(self):
        self.output = io.BytesIO()
        self.stdout = SimpleNamespace(buffer=self.output, flush=lambda: None)

    def decode_response(self):
        data = self.output.getvalue()
        length = struct.unpack("<I", data[:4])[0]
        return json.loads(data[4:4 + length].decode("utf-8"))

    def test_prepare_path_decodes_utf8_percent_escapes(self):
        with patch.object(host, "currentOS", "linux"), patch.object(
            host.os.path, "normpath", side_effect=posixpath.normpath
        ):
            path = host.preparePath("file:///tmp/Dossier%20%C3%A9t%C3%A9.docx")
        self.assertEqual(path, "/tmp/Dossier été.docx")

    def test_windows_paths_preserve_drive_letters_and_unc_server(self):
        with patch.object(host, "currentOS", "win32"), patch.object(
            host.os.path, "normpath", side_effect=ntpath.normpath
        ):
            drive_path = host.preparePath(
                "file:///C:/Documents/Dossier%20%C3%A9t%C3%A9.docx"
            )
            unc_path = host.preparePath("file:///dfsburo/Donnees/Dossier%20partage.docx")

        self.assertEqual(drive_path, "C:\\Documents\\Dossier été.docx")
        self.assertEqual(unc_path, "\\\\dfsburo\\Donnees\\Dossier partage.docx")

    def test_direct_windows_drive_paths_are_normalized(self):
        with patch.object(host, "currentOS", "win32"), patch.object(
            host.os.path, "normpath", side_effect=ntpath.normpath
        ):
            network_drive = host.preparePath("g:\\Donnees\\")
            windows_folder = host.preparePath("c:\\windows\\")

        self.assertEqual(network_drive, "g:\\Donnees")
        self.assertEqual(windows_folder, "c:\\windows")

    def test_native_host_manifests_allow_current_and_legacy_addon_ids(self):
        extension_ids = {
            "jid1-JAzC7z53jemo5Q@jetpack",
            "{b0875df6-5b25-4907-a2c1-10ca04249fb8}",
        }
        for filename in (
            "webextension_local_filesystem_links.json",
            "webextension_local_filesystem_links_win.json",
        ):
            manifest_path = NATIVE_HOST_DIR / filename
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(extension_ids.issubset(manifest["allowed_extensions"]))

        installer_script = (
            NATIVE_HOST_DIR.parent / "build" / "windows" / "InnoSetupScript.iss"
        ).read_text(encoding="utf-8")
        for extension_id in extension_ids:
            self.assertIn(extension_id, installer_script)

    def test_windows_installer_includes_pyinstaller_internal_runtime(self):
        installer_script = (
            NATIVE_HOST_DIR.parent / "build" / "windows" / "InnoSetupScript.iss"
        ).read_text(encoding="utf-8")
        host_file_entry = next(
            line
            for line in installer_script.splitlines()
            if line.startswith('Source: "{#HostDirectory}\\*"')
        )
        self.assertIn("recursesubdirs", host_file_entry)
        self.assertIn("createallsubdirs", host_file_entry)

    def test_fallback_path_uses_server_and_preserves_encoded_path(self):
        with patch.object(host, "currentOS", "linux"), patch.object(
            host.os.path, "normpath", side_effect=posixpath.normpath
        ):
            path = host.getFallbackPath(
                "file:///dfsburo/Donnees/Dossier%20partage.docx",
                "villeurbanne.fr",
            )
        self.assertEqual(
            path, "//villeurbanne.fr/dfsburo/Donnees/Dossier partage.docx"
        )

    def test_fallback_server_rejects_url_or_path(self):
        with patch.object(host, "currentOS", "linux"), patch.object(
            host.os.path, "normpath", side_effect=posixpath.normpath
        ), self.assertRaises(ValueError):
            host.getFallbackPath("file:///share/file.docx", "https://server")

    def test_send_json_writes_native_messaging_binary_frame(self):
        with patch.object(host.sys, "stdout", self.stdout):
            host.send_json({"error": None})

        self.assertEqual(self.decode_response(), {"error": None})

    def test_read_message_handles_partial_reads(self):
        message = json.dumps({"url": "file:///tmp/file.txt"}).encode("utf-8")
        frame = struct.pack("<I", len(message)) + message
        stdin = SimpleNamespace(buffer=ChunkedReader(frame))
        with patch.object(host.sys, "stdin", stdin), patch.object(
            host, "process_message"
        ) as process_message:
            host.read_thread_func(None)

        process_message.assert_called_once_with({"url": "file:///tmp/file.txt"})

    def test_truncated_frame_returns_native_host_error(self):
        stdin = SimpleNamespace(buffer=ChunkedReader(b"\x05\x00"))
        with patch.object(host.sys, "stdin", stdin), patch.object(
            host.sys, "stdout", self.stdout
        ), patch.object(host.logger, "exception"):
            with self.assertRaises(SystemExit):
                host.read_thread_func(None)

        response = self.decode_response()
        self.assertEqual(response["error"], "ERROR_NATIVE_HOST")
        self.assertIn("Incomplete native messaging frame header", response["detail"])

    def test_binary_type_reads_python3_bytes(self):
        executable = bytearray(70)
        executable[:2] = b"MZ"
        struct.pack_into("<L", executable, 60, 64)
        struct.pack_into("<H", executable, 68, binary_type.IMAGE_FILE_MACHINE_I386)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.exe"
            path.write_bytes(executable)
            result = binary_type.GetBinaryType(str(path))
        self.assertEqual(result["readable"], "IA-32 (32-bit x86)")


if __name__ == "__main__":
    unittest.main()
