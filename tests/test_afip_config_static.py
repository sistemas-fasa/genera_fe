from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_sistema_ini_example_contains_afip_timeout_and_service_sections():
    sistema_ini = read_text("sistema.ini.example")

    assert "afip_timeout_segundos" in sistema_ini
    assert "[WSFEv1]" in sistema_ini
    assert "[WSAA]" in sistema_ini
    assert "[WSCDC]" in sistema_ini


def test_fe_and_fce_do_not_use_fixed_timeout_15():
    assert "TIMEOUT = 15" not in read_text("controladores/FE.py")
    assert "TIMEOUT = 15" not in read_text("controladores/FCE.py")


def test_main_does_not_hardcode_wsfev1_production_wsdl():
    main_py = read_text("controladores/Main.py")

    assert "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL" not in main_py


def test_fe_and_fce_use_configured_afip_timeout():
    fe_py = read_text("controladores/FE.py")
    fce_py = read_text("controladores/FCE.py")

    assert "LeerTimeoutAFIP" in fe_py or "LeerIni(clave=\"afip_timeout_segundos\"" in fe_py
    assert "LeerTimeoutAFIP" in fce_py or "LeerIni(clave=\"afip_timeout_segundos\"" in fce_py
