"""Diagnostico local seguro del proyecto Genera FE 2025."""

from __future__ import annotations

import configparser
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

EXPECTED_FILES = [
    "README.md",
    "requirements.txt",
    "requirements-pyafipws.txt",
    "sistema.ini.example",
    ".env.example",
    "main.py",
]

OPTIONAL_LOCAL_FILES = [
    "sistema.ini",
    ".env",
]

DEPENDENCIES = [
    "PyQt5",
    "peewee",
    "dotenv",
    "cryptography",
    "qrcode",
    "fpdf",
    "xlsxwriter",
    "pyafipws",
]

REQUIRED_SECTIONS = [
    "param",
    "WSFEv1",
    "WSAA",
    "FACTURA",
    "WSCDC",
]

REQUIRED_KEYS = {
    "param": [
        "iniciosistema",
        "basedatos",
        "usuario",
        "host",
        "base",
        "homo",
        "afip_timeout_segundos",
    ],
    "WSFEv1": [
        "url_prod",
        "url_homo",
        "cuit",
        "pto_vta",
    ],
    "WSAA": [
        "cert_homo",
        "cert_prod",
        "privatekey_homo",
        "privatekey_prod",
        "url_prod",
        "url_homo",
    ],
}


class Report:
    def __init__(self) -> None:
        self.warning_count = 0
        self.error_count = 0

    def ok(self, message: str) -> None:
        print(f"[OK] {message}")

    def warn(self, message: str) -> None:
        self.warning_count += 1
        print(f"[WARN] {message}")

    def error(self, message: str) -> None:
        self.error_count += 1
        print(f"[ERROR] {message}")

    def exit_code(self) -> int:
        return 1 if self.error_count else 0


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_config_path(raw_path: str) -> Path:
    candidate = Path(raw_path.strip())
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate


def is_sensitive_name(name: str) -> bool:
    lowered = name.lower()
    return any(term in lowered for term in ("password", "key", "token", "sign"))


def config_key_label(section: str, key: str) -> str:
    if is_sensitive_name(key):
        return f"clave sensible en [{section}]"
    return f"clave [{section}] {key}"


def check_python(report: Report) -> None:
    version = sys.version_info
    version_label = f"{version.major}.{version.minor}.{version.micro}"
    if version < (3, 8):
        report.warn(f"Python version {version_label}; se recomienda 3.8 o superior")
    else:
        report.ok(f"Python version {version_label}")


def check_files(report: Report) -> None:
    for relative_path in EXPECTED_FILES:
        if (ROOT / relative_path).exists():
            report.ok(f"{relative_path} existe")
        else:
            report.error(f"{relative_path} no existe")

    for relative_path in OPTIONAL_LOCAL_FILES:
        if (ROOT / relative_path).exists():
            report.ok(f"{relative_path} existe")
        else:
            report.warn(f"{relative_path} no existe")


def check_pyafipws_documentation(report: Report) -> None:
    readme_path = ROOT / "README.md"
    requirements_path = ROOT / "requirements-pyafipws.txt"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    requirements = (
        requirements_path.read_text(encoding="utf-8")
        if requirements_path.exists()
        else ""
    )

    if "github.com/reingart/pyafipws" in readme and "github.com/reingart/pyafipws" in requirements:
        report.ok("pyafipws estrategia documentada")
    else:
        report.error("pyafipws estrategia no documentada en README/requirements")


def check_dependencies(report: Report) -> None:
    available = []
    missing = []

    for module_name in DEPENDENCIES:
        if importlib.util.find_spec(module_name) is None:
            missing.append(module_name)
        else:
            available.append(module_name)

    if available:
        report.ok(f"imports principales disponibles: {', '.join(available)}")

    for module_name in missing:
        if module_name == "pyafipws":
            report.warn(
                "pyafipws no importable. Instalar segun README/requirements-pyafipws.txt o proveer carpeta local pyafipws/"
            )
        else:
            report.warn(f"{module_name} no importable")


def load_config(report: Report) -> configparser.ConfigParser | None:
    config_path = ROOT / "sistema.ini"
    if not config_path.exists():
        report.warn("sistema.ini no existe; se omite validacion de configuracion y certificados")
        return None

    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
    except configparser.Error as exc:
        report.error(f"sistema.ini invalido: {exc}")
        return None

    report.ok("sistema.ini se pudo leer con configparser")
    return parser


def check_config_shape(report: Report, parser: configparser.ConfigParser | None) -> None:
    if parser is None:
        return

    for section in REQUIRED_SECTIONS:
        if parser.has_section(section):
            report.ok(f"seccion [{section}] presente")
        else:
            report.error(f"falta seccion [{section}]")

    for section, keys in REQUIRED_KEYS.items():
        if not parser.has_section(section):
            continue

        for key in keys:
            label = config_key_label(section, key)
            if parser.has_option(section, key):
                report.ok(f"{label} presente")
            else:
                report.warn(f"falta {label}")


def check_certificates(report: Report, parser: configparser.ConfigParser | None) -> None:
    if parser is None:
        report.warn("certificados/ no se valida sin sistema.ini")
        return

    certificates_dir = ROOT / "certificados"
    if certificates_dir.exists():
        report.ok("certificados/ existe")
    else:
        report.warn("certificados/ no existe")

    if not parser.has_section("param") or not parser.has_section("WSAA"):
        return

    homo = parser.get("param", "homo", fallback="").strip().upper()
    if homo == "N":
        pairs = [("cert_prod", "certificado productivo"), ("privatekey_prod", "clave productiva")]
        missing_level = report.error
    else:
        pairs = [("cert_homo", "certificado de homologacion"), ("privatekey_homo", "clave de homologacion")]
        missing_level = report.warn

    for option_name, label in pairs:
        raw_path = parser.get("WSAA", option_name, fallback="").strip()
        if not raw_path:
            missing_level(f"ruta de {label} no configurada")
            continue

        resolved_path = resolve_config_path(raw_path)
        if resolved_path.exists():
            report.ok(f"{label} existe")
        else:
            missing_level(f"{label} no existe")


def run_checks() -> int:
    report = Report()

    check_python(report)
    check_files(report)
    check_pyafipws_documentation(report)
    check_dependencies(report)
    parser = load_config(report)
    check_config_shape(report, parser)
    check_certificates(report, parser)

    if report.error_count:
        print(f"Resultado: FALLO ({report.error_count} errores, {report.warning_count} advertencias)")
    elif report.warning_count:
        print(f"Resultado: OK con advertencias ({report.warning_count})")
    else:
        print("Resultado: OK")

    return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(run_checks())
