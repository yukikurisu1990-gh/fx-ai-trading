"""Authority resolution for PR-B.1 (pair universe + M1 BA schema).

Both authorities are resolved by AST / source-text inspection only — the
production modules are read with ``Path.read_text`` and parsed with ``ast``,
never imported or executed. This honours the protocol AST/source-only mandate
(plan §6).
"""
