"""Diagnostico local seguro del proyecto Genera FE 2025."""

from __future__ import annotations

import argparse
import configparser
import importlib.util
import re
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

PRODUCTION_REQUIRED_FILES = [
    "sistema.ini",
    ".env",
]

EXECUTABLE_CANDIDATES = [
    "dist/main.exe",
    "dist/genera_fe.exe",
    "dist/GeneraFE.exe",
    "main.exe",
    "genera_fe.exe",
    "GeneraFE.exe",
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

PRODUCTION_REQUIRED_KEYS = {
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
        "cuit",
        "pto_vta",
    ],
    "WSAA": [
        "cert_prod",
        "privatekey_prod",
        "url_prod",
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

    def warn_or_error(self, condition: bool, message: str, production: bool = False) -> None:
        if condition:
            self.ok(message)
        elif production:
            self.error(message)
        else:
            self.warn(message)

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


def is_repo_checkout() -> bool:
    return (ROOT / ".git").exists()


def check_python(report: Report) -> None:
    version = sys.version_info
    version_label = f"{version.major}.{version.minor}.{version.micro}"
    if version < (3, 8):
        report.warn(f"Python version {version_label}; se recomienda 3.8 o superior")
    else:
        report.ok(f"Python version {version_label}")


def check_files(report: Report, production: bool = False) -> None:
    for relative_path in EXPECTED_FILES:
        if (ROOT / relative_path).exists():
            report.ok(f"{relative_path} existe")
        elif production:
            report.warn(f"{relative_path} no existe")
        else:
            report.error(f"{relative_path} no existe")

    if production:
        return

    for relative_path in OPTIONAL_LOCAL_FILES:
        if (ROOT / relative_path).exists():
            report.ok(f"{relative_path} existe")
        else:
            report.warn(f"{relative_path} no existe")


def check_production_files(report: Report, production: bool) -> None:
    if not production:
        return

    for relative_path in PRODUCTION_REQUIRED_FILES:
        report.warn_or_error(
            (ROOT / relative_path).exists(),
            f"{relative_path} existe",
            production=production,
        )


def find_executable(
    report: Report,
    parser: configparser.ConfigParser | None,
    production: bool,
) -> Path | None:
    configured_path = ""
    if parser is not None and parser.has_section("param"):
        configured_path = parser.get("param", "ejecutable", fallback="").strip()

    if configured_path:
        executable_path = resolve_config_path(configured_path)
        if executable_path.exists():
            report.ok(f"ejecutable configurado existe: {display_path(executable_path)}")
            return executable_path
        report.warn_or_error(
            False,
            f"ejecutable configurado no existe: {display_path(executable_path)}",
            production=production,
        )
        return None

    for relative_path in EXECUTABLE_CANDIDATES:
        candidate = ROOT / relative_path
        if candidate.exists():
            report.ok(f"ejecutable encontrado: {display_path(candidate)}")
            return candidate

    report.warn_or_error(
        False,
        "no se encontro ejecutable generado",
        production=production,
    )
    return None


def check_pyafipws_documentation(report: Report, production: bool = False) -> None:
    readme_path = ROOT / "README.md"
    requirements_path = ROOT / "requirements-pyafipws.txt"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    requirements = (
        requirements_path.read_text(encoding="utf-8")
        if requirements_path.exists()
        else ""
    )

    if not requirements_path.exists() and production and not is_repo_checkout():
        report.warn("pyafipws estrategia no se valida sin requirements-pyafipws.txt")
    elif "github.com/reingart/pyafipws" in readme and "github.com/reingart/pyafipws" in requirements:
        report.ok("pyafipws estrategia documentada")
    else:
        report.error("pyafipws estrategia no documentada en README/requirements")


def check_pyafipws_requirements(report: Report, production: bool) -> None:
    requirements_path = ROOT / "requirements-pyafipws.txt"
    if not requirements_path.exists():
        if production and not is_repo_checkout():
            report.warn("requirements-pyafipws.txt no existe; se omite validacion PyAfipWs de repo")
        else:
            report.warn_or_error(
                False,
                "requirements-pyafipws.txt existe",
                production=production,
            )
        return

    requirements = requirements_path.read_text(encoding="utf-8")
    if "<COMMIT_SHA_PROBADO>" in requirements:
        report.error("requirements-pyafipws.txt contiene placeholder de commit")
    else:
        report.ok("requirements-pyafipws.txt sin placeholder de commit")

    if "github.com/reingart/pyafipws" in requirements:
        report.ok("requirements-pyafipws.txt usa GitHub oficial")
    else:
        report.error("requirements-pyafipws.txt no usa GitHub oficial")

    requirement_tokens = re.split(r"[@\s#]+", requirements)
    if any(re.fullmatch(r"[0-9a-fA-F]{40}", token) for token in requirement_tokens):
        report.ok("requirements-pyafipws.txt fija commit SHA de 40 caracteres")
    else:
        report.error("requirements-pyafipws.txt no fija commit SHA de 40 caracteres")

    requirements_txt = ROOT / "requirements.txt"
    requirements_txt_body = (
        requirements_txt.read_text(encoding="utf-8")
        if requirements_txt.exists()
        else ""
    )
    if "PyAfipWs==2.7.1874" in requirements_txt_body:
        report.error("requirements.txt contiene PyAfipWs legacy de PyPI")
    else:
        report.ok("requirements.txt no contiene PyAfipWs legacy de PyPI")


def check_dependencies(
    report: Report,
    production: bool = False,
    executable_exists: bool = False,
) -> None:
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
        message = (
            "pyafipws no importable. Instalar segun README/requirements-pyafipws.txt o proveer carpeta local pyafipws/"
            if module_name == "pyafipws"
            else f"{module_name} no importable"
        )
        if production and not executable_exists:
            report.error(message)
        else:
            report.warn(message)


def load_config(report: Report, production: bool = False) -> configparser.ConfigParser | None:
    config_path = ROOT / "sistema.ini"
    if not config_path.exists():
        report.warn_or_error(
            False,
            "sistema.ini existe para validar configuracion y certificados",
            production=production,
        )
        return None

    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
    except configparser.Error as exc:
        report.error(f"sistema.ini invalido: {exc}")
        return None

    report.ok("sistema.ini se pudo leer con configparser")
    return parser


def example_wscdc_keys() -> list[str]:
    example_path = ROOT / "sistema.ini.example"
    if not example_path.exists():
        return []

    parser = configparser.ConfigParser()
    try:
        parser.read(example_path, encoding="utf-8")
    except configparser.Error:
        return []

    if not parser.has_section("WSCDC"):
        return []
    return list(parser.options("WSCDC"))


def check_production_config_values(report: Report, parser: configparser.ConfigParser) -> None:
    homo = parser.get("param", "homo", fallback="").strip().upper()
    if homo == "N":
        report.ok("homo=N para produccion")
    else:
        report.error("homo debe ser N en produccion")

    base = parser.get("param", "base", fallback="").strip().lower()
    if base == "mysql":
        report.ok("base=mysql para produccion")
    else:
        report.error("base debe ser mysql en produccion")

    timeout_raw = parser.get("param", "afip_timeout_segundos", fallback="").strip()
    try:
        timeout = int(timeout_raw)
    except ValueError:
        report.error("afip_timeout_segundos debe ser entero >= 1")
        return

    if timeout >= 1:
        report.ok("afip_timeout_segundos entero >= 1")
    else:
        report.error("afip_timeout_segundos debe ser entero >= 1")


def check_config_shape(
    report: Report,
    parser: configparser.ConfigParser | None,
    production: bool = False,
) -> None:
    if parser is None:
        return

    for section in REQUIRED_SECTIONS:
        if parser.has_section(section):
            report.ok(f"seccion [{section}] presente")
        else:
            report.error(f"falta seccion [{section}]")

    required_keys = PRODUCTION_REQUIRED_KEYS if production else REQUIRED_KEYS
    for section, keys in required_keys.items():
        if not parser.has_section(section):
            continue

        for key in keys:
            label = config_key_label(section, key)
            if parser.has_option(section, key):
                report.ok(f"{label} presente")
            elif production:
                report.error(f"falta {label}")
            else:
                report.warn(f"falta {label}")

    if not production:
        return

    if parser.has_section("WSCDC"):
        report.ok("seccion [WSCDC] presente para produccion")
        wscdc_keys = example_wscdc_keys()
        for key in wscdc_keys:
            label = config_key_label("WSCDC", key)
            report.warn_or_error(
                parser.has_option("WSCDC", key),
                f"{label} presente",
                production=production,
            )
    else:
        report.error("falta seccion [WSCDC]")

    if parser.has_section("param"):
        check_production_config_values(report, parser)


def check_certificates(
    report: Report,
    parser: configparser.ConfigParser | None,
    production: bool = False,
) -> None:
    if parser is None:
        report.warn_or_error(
            False,
            "certificados/ se valida con sistema.ini",
            production=production,
        )
        return

    certificates_dir = ROOT / "certificados"
    if certificates_dir.exists():
        report.ok("certificados/ existe")
    elif production:
        report.error("certificados/ no existe")
    else:
        report.warn("certificados/ no existe")

    if not parser.has_section("param") or not parser.has_section("WSAA"):
        return

    if production:
        pairs = [("cert_prod", "certificado productivo"), ("privatekey_prod", "clave productiva")]
        missing_level = report.error
    else:
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


def check_operational_paths(
    report: Report,
    parser: configparser.ConfigParser | None,
    production: bool,
) -> None:
    if parser is None or not parser.has_section("param"):
        return

    raw_start_path = parser.get("param", "iniciosistema", fallback="").strip()
    if not raw_start_path:
        return

    start_path = resolve_config_path(raw_start_path)
    if start_path.exists():
        report.ok("iniciosistema existe")
    else:
        report.warn_or_error(False, "iniciosistema no existe o no se puede resolver", production=production)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnostico seguro del proyecto Genera FE 2025."
    )
    parser.add_argument(
        "--production",
        "--prod",
        action="store_true",
        help="Ejecuta validaciones estrictas para produccion sin conectar servicios externos.",
    )
    return parser.parse_args(argv)


def run_checks(production: bool = False) -> int:
    report = Report()

    if production:
        print("Modo: PRODUCCION WINDOWS")

    check_python(report)
    check_files(report, production=production)
    check_production_files(report, production)
    parser = load_config(report, production=production)
    executable_path = find_executable(report, parser, production) if production else None
    check_pyafipws_documentation(report, production=production)
    check_pyafipws_requirements(report, production)
    check_dependencies(
        report,
        production=production,
        executable_exists=executable_path is not None,
    )
    check_config_shape(report, parser, production=production)
    check_certificates(report, parser, production=production)
    check_operational_paths(report, parser, production=production)

    if production and report.error_count:
        print(
            f"Resultado: FALLÓ PRODUCCION ({report.error_count} errores, {report.warning_count} advertencias)"
        )
    elif production:
        print("Resultado: OK PRODUCCION")
    elif report.error_count:
        print(f"Resultado: FALLO ({report.error_count} errores, {report.warning_count} advertencias)")
    elif report.warning_count:
        print(f"Resultado: OK con advertencias ({report.warning_count})")
    else:
        print("Resultado: OK")

    return report.exit_code()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(run_checks(production=args.production))
