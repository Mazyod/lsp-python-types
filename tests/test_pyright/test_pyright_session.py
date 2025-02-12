from lsp_types.pyright.session import PyrightSession


async def test_pyright_session():
    code = """\
def greet(name: str) -> str:
    return 123
"""

    pyright_session = await PyrightSession.create(initial_code=code)
    diagnostics = await pyright_session.get_diagnostics()

    assert diagnostics["diagnostics"] != []

    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"
"""

    assert await pyright_session.update_code(code) == 2

    diagnostics = await pyright_session.get_diagnostics()
    assert diagnostics["diagnostics"] == []
