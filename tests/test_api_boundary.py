"""The generated bindings are an implementation detail: nothing a consumer can
reach may name ``saas_sdk._gen``.

A consumer that has to import the generated package to spell an argument or hold
a result pins this SDK's internal layout into its own source, so regenerating
against a newer contract — or swapping the committed tree for a served
dependency — becomes a breaking change for every consumer instead of a change
here. The facades re-export the types they take and return; these tests fail if
a signature stops using those names.
"""

import ast
from pathlib import Path

import pytest

from saas_sdk import authorization_revision, datasource, work_context
from saas_sdk._gen import datasource_pb2, work_contexts_pb2

_SRC = Path(__file__).parent.parent / "src" / "saas_sdk"

# Every name a facade re-exports, against the generated type it must *be*.
RE_EXPORTS = [
    (datasource, "Datasource", datasource_pb2.Datasource),
    (work_context, "IssuedWorkContext", work_contexts_pb2.IssuedWorkContext),
    (work_context, "WorkContextScope", work_contexts_pb2.WorkContextScope),
    (work_context, "WorkContextReplayPolicy", work_contexts_pb2.WorkContextReplayPolicy),
    (
        work_context,
        "WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED",
        work_contexts_pb2.WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED,
    ),
    (
        work_context,
        "WORK_CONTEXT_REPLAY_POLICY_IDEMPOTENT",
        work_contexts_pb2.WORK_CONTEXT_REPLAY_POLICY_IDEMPOTENT,
    ),
    (
        work_context,
        "WORK_CONTEXT_REPLAY_POLICY_SINGLE_USE",
        work_contexts_pb2.WORK_CONTEXT_REPLAY_POLICY_SINGLE_USE,
    ),
    (
        authorization_revision,
        "CheckAuthorizationRevisionRequest",
        work_contexts_pb2.CheckAuthorizationRevisionRequest,
    ),
]


@pytest.mark.parametrize(
    "module, name, generated", RE_EXPORTS, ids=[f"{m.__name__}.{n}" for m, n, _ in RE_EXPORTS]
)
def test_re_export_is_the_generated_type(module, name, generated):
    """Re-exporting must alias, not wrap: a consumer that builds a message from
    the facade name and one that already imports the generated package have to
    produce values the other side accepts."""
    assert getattr(module, name) is generated

# Modules a consumer imports, __init__ included — the generated package under
# _gen/ is the thing being fenced off, and private modules are not reachable.
FACADES = sorted(
    p for p in _SRC.glob("*.py") if p.name == "__init__.py" or not p.name.startswith("_")
)


def _generated_aliases(tree):
    """Local names bound to the generated package, e.g. ``pb`` from
    ``from saas_sdk._gen import datasource_pb2 as pb``."""
    aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "saas_sdk._gen" or (node.level and module == "_gen"):
                aliases.update(a.asname or a.name for a in node.names)
    return aliases


def _public(name):
    return not name.startswith("_")


def _annotations(node):
    """Every annotation on a function, with the line it sits on."""
    args = node.args
    for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]:
        if arg is not None and arg.annotation is not None:
            yield arg.annotation
    if node.returns is not None:
        yield node.returns


def _consumer_reachable(tree):
    """Annotations a consumer must be able to spell: public module-level
    functions, and public members of public classes. Private names are excluded
    — an unexported member built on the generated types is how a facade is
    supposed to work, and no consumer can name it."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _public(node.name):
            yield from _annotations(node)
        elif isinstance(node, ast.ClassDef) and _public(node.name):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and _public(
                    member.name
                ):
                    yield from _annotations(member)
                elif isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name):
                    if _public(member.target.id):
                        yield member.annotation


def _names(expr):
    return {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)}


@pytest.mark.parametrize("path", FACADES, ids=lambda p: p.name)
def test_public_signatures_do_not_name_the_generated_package(path):
    tree = ast.parse(path.read_text())
    aliases = _generated_aliases(tree)
    if not aliases:
        pytest.skip(f"{path.name} does not import the generated bindings")

    leaks = [
        f"{path.name}:{annotation.lineno}: {ast.unparse(annotation)}"
        for annotation in _consumer_reachable(tree)
        if _names(annotation) & aliases
    ]
    assert not leaks, (
        "these signatures name the generated package, so a consumer cannot call them "
        "without importing saas_sdk._gen — re-export the type at module level and use "
        "that name:\n  " + "\n  ".join(leaks)
    )


@pytest.mark.parametrize("path", FACADES, ids=lambda p: p.name)
def test_generated_package_is_not_exported(path):
    tree = ast.parse(path.read_text())
    aliases = _generated_aliases(tree)
    if not aliases:
        pytest.skip(f"{path.name} does not import the generated bindings")

    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            exported = {e.value for e in node.value.elts if isinstance(e, ast.Constant)}
            assert not exported & aliases, (
                f"{path.name} lists the generated bindings in __all__ "
                f"({sorted(exported & aliases)}) — that documents saas_sdk._gen as public "
                "surface. Re-export the individual types instead."
            )
