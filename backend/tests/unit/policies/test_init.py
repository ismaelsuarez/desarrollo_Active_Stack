def test_policies_init_exports():
    from app.domain.policies import autorizar, Accion, Decision, ContextoAcceso, Intervalo
    import app.domain.policies as policies

    assert autorizar is not None
    assert Accion is not None
    assert Decision is not None
    assert ContextoAcceso is not None
    assert Intervalo is not None
    assert set(policies.__all__) == {"autorizar", "Accion", "Decision", "ContextoAcceso", "Intervalo"}
