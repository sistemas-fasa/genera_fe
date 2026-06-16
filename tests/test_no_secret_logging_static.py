from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENVIO_EMAILS = ROOT / "controladores" / "EnvioEmailsPendientes.py"
FCE = ROOT / "controladores" / "FCE.py"
FE = ROOT / "controladores" / "FE.py"


def test_envio_emails_no_loguea_password_smtp():
    source = ENVIO_EMAILS.read_text(encoding="utf-8")

    assert "pass" + "_preview" not in source
    assert "len={len(smtp" + "_password)}" not in source
    assert "password" + " '" not in source


def test_fce_no_loguea_ticket_wsaa():
    source = FCE.read_text(encoding="utf-8")

    assert "Ticket de acceso " + "{}" + ".format(ta)" not in source


def test_no_quedan_logs_reactivables_de_tra_o_cms():
    source = FCE.read_text(encoding="utf-8") + FE.read_text(encoding="utf-8")

    logging_error = "logging" + ".error("

    assert logging_error + "\"" + "Tra " not in source
    assert logging_error + "\"" + "CMS " not in source
