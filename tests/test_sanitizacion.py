"""Pruebas automáticas de sanitización y detección de fugas de datos sensibles."""

import os
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class SanitizationAndLeakTests(unittest.TestCase):
    """Garantiza que ningún archivo del paquete contenga credenciales ni datos privados."""

    FORBIDDEN_PATTERNS = [
        # Tokens reales de feeds de Javier
        (r"01d5b5488ec0e3ebe3704e7ebeef491d5cc5bacc", "Token de calendario UVA real"),
        (r"de8f2e48143396cd45e4923d2b0b6b38e18a8b96", "Token de calendario Educacyl real"),
        # Parámetros con IDs de usuario específicos en URLs de exportación
        (r"userid=9062", "ID de usuario UVA real"),
        (r"userid=3584", "ID de usuario Educacyl real"),
        # Chat ID de Telegram personal
        (r"2059774206", "Telegram Chat ID de Javier"),
        # Correo personal de sincronización
        (r"deljavierher@gmail\.com", "Correo personal en ruta de sincronización"),
        # Rutas a directorios privados de Hermes o Google Drive
        (r"Library/CloudStorage", "Ruta a Google Drive personal"),
        (r"\.hermes/scripts/moodle_creds\.json", "Ruta a credenciales de Moodle"),
        (r"\.hermes/\.env", "Ruta a variables de entorno de Hermes"),
        # IDs de cursos específicos de Javier
        (r"10344", "ID de curso UVA de Javier (Química)"),
        (r"10319", "ID de curso UVA de Javier (Org)"),
        (r"10309", "ID de curso UVA de Javier (SPF)"),
        (r"14079", "ID de curso UVA de Javier (Informática)"),
        # Contraseñas o credenciales en texto plano quemadas
        (r"adAS_password[\"']?\s*:\s*[\"'][^\"']+[\"']", "Contraseña quemada en formulario"),
        (r"TELEGRAM_BOT_TOKEN", "Variable de bot de Telegram"),
    ]

    def test_no_sensitive_patterns_in_code_or_documentation(self):
        """Escanea todos los archivos del repositorio (excluyendo .git) contra patrones prohibidos."""
        scanned_files = 0
        for root, dirs, files in os.walk(REPO_ROOT):
            # Omitir .git y __pycache__
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache")]
            for filename in files:
                filepath = Path(root) / filename
                # Excluir la propia prueba para no disparar falsos positivos con los patrones
                if filepath.name == "test_sanitizacion.py":
                    continue
                # Excluir archivos binarios si los hubiera
                if filepath.suffix in (".pyc", ".png", ".jpg", ".zip"):
                    continue

                scanned_files += 1
                try:
                    content = filepath.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue

                for pattern, description in self.FORBIDDEN_PATTERNS:
                    # En PLAN_MUSE_COMPLETO.md se mencionan algunos nombres en la auditoría,
                    # pero no deben contener los tokens ni el chat id real.
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    self.assertFalse(
                        bool(matches),
                        f"Fuga detectada en {filepath.relative_to(REPO_ROOT)}: {description}",
                    )

        self.assertGreater(scanned_files, 5, "Deben haberse escaneado al menos 5 archivos en el repositorio")

    def test_config_example_is_clean(self):
        """Verifica que config.example.json no contenga URLs rellenas ni tokens."""
        config_example = REPO_ROOT / "config.example.json"
        self.assertTrue(config_example.exists(), "config.example.json debe existir")
        content = config_example.read_text(encoding="utf-8")
        self.assertNotIn("authtoken", content.lower())
        self.assertNotIn("https://", content.lower())

    def test_campus_tasks_redacts_urls_in_runtime_errors(self):
        """Comprueba que excepciones de campus_tasks nunca hagan eco de la URL con token."""
        from campus_tasks import validate_feed_url

        sensitive_url = "http://moodle.campus.es/feed.ics?authtoken=super-secret-token-12345"
        with self.assertRaises(ValueError) as ctx:
            validate_feed_url(sensitive_url)

        error_message = str(ctx.exception)
        self.assertNotIn("super-secret-token-12345", error_message)
        self.assertNotIn("authtoken", error_message)
        self.assertNotIn("http://moodle.campus.es", error_message)


if __name__ == "__main__":
    unittest.main()
