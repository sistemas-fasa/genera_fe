from types import SimpleNamespace


def test_no_encola_notificacion_para_notificacion_de_fallo(monkeypatch):
    from controladores import EnvioEmailsPendientes as envio

    encolados = []

    monkeypatch.setattr(
        envio.ParamSist,
        "ObtenerParametro",
        lambda nombre, default=None: "admin@example.com",
    )
    monkeypatch.setattr(
        envio,
        "encolar_email",
        lambda **kwargs: encolados.append(kwargs),
    )

    email = SimpleNamespace(
        id=83604,
        destinatario="oscar@example.com",
        asunto="⚠️ Fallo de envío de email ID 83600",
        creado_en=None,
        intentos=3,
    )

    envio._notificar_fallo_final(email, "EOF occurred in violation of protocol")

    assert encolados == []
