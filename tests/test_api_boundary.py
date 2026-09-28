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
import re
from pathlib import Path
from types import ModuleType

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


@pytest.mark.parametrize(
    "module, name, generated", RE_EXPORTS, ids=[f"{m.__name__}.{n}" for m, n, _ in RE_EXPORTS]
)
def test_re_export_is_bound_from_the_generated_module(module, name, generated):
    """Identity alone does not prove aliasing for the enum values: they are small
    ints, so ``WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED = 0`` would satisfy ``is``
    through CPython's integer cache while silently decoupling the constant from
    the proto — it would then keep its old value across a renumbering instead of
    following it. Check the binding itself, which holds for classes and values
    alike and does not depend on interning."""
    tree = ast.parse(Path(module.__file__).read_text())
    aliases = _generated_aliases(tree)
    bound = {
        target.id: ast.unparse(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id in aliases
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert name in bound, (
        f"{Path(module.__file__).name} does not bind {name} from the generated bindings — "
        "re-export it as `<alias>.<name>` so it follows the proto instead of restating it."
    )

# Modules a consumer imports, __init__ included — the generated package under
# _gen/ is the thing being fenced off, and private modules are not reachable.
FACADES = sorted(
    p for p in _SRC.glob("*.py") if p.name == "__init__.py" or not p.name.startswith("_")
)
# An empty glob would parametrize every gate below into nothing and report green.
assert FACADES, f"no facade modules found under {_SRC}"


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


def _consumer_reachable(body):
    """Annotations a consumer must be able to spell: public functions, public
    members of public classes, and public annotated assignments — at any nesting
    depth. Private names are excluded: an unexported member built on the
    generated types is how a facade is supposed to work, and no consumer can
    name it.

    Definitions guarded by ``try:``/``if`` are reached too. ``authorization_revision``
    already defines its optional transports behind ``try: import`` blocks, so a
    check that only looked at the top level would go blind exactly where this
    package conditionally defines things."""
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Do not descend into the body: locals are not consumer-reachable.
            if _public(node.name):
                yield from _annotations(node)
        elif isinstance(node, ast.ClassDef):
            if _public(node.name):
                yield from _consumer_reachable(node.body)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if _public(node.target.id):
                yield node.annotation
        else:
            for branch in ("body", "orelse", "finalbody"):
                yield from _consumer_reachable(getattr(node, branch, []))
            for handler in getattr(node, "handlers", []):
                yield from _consumer_reachable(handler.body)


def _names(expr):
    """Names an annotation mentions, looking inside string annotations too — a
    quoted forward reference is still a name the consumer has to be able to
    resolve, so it has to be checked rather than skipped as an opaque constant."""
    found = set()
    for node in ast.walk(expr):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                found |= _names(ast.parse(node.value, mode="eval").body)
            except SyntaxError:
                pass  # a plain string default or doc value, not an annotation
    return found


@pytest.mark.parametrize("path", FACADES, ids=lambda p: p.name)
def test_public_signatures_do_not_name_the_generated_package(path):
    tree = ast.parse(path.read_text())
    aliases = _generated_aliases(tree)
    if not aliases:
        pytest.skip(f"{path.name} does not import the generated bindings")

    leaks = [
        f"{path.name}:{annotation.lineno}: {ast.unparse(annotation)}"
        for annotation in _consumer_reachable(tree.body)
        if _names(annotation) & aliases
    ]
    assert not leaks, (
        "these signatures name the generated package, so a consumer cannot call them "
        "without importing saas_sdk._gen — re-export the type at module level and use "
        "that name:\n  " + "\n  ".join(leaks)
    )


@pytest.mark.parametrize("path", FACADES, ids=lambda p: p.name)
def test_star_import_does_not_re_export_the_generated_package(path):
    """The static __all__ check reads intent; this reads what Python actually
    hands a consumer. A module that grows a public name bound to the generated
    bindings without listing it fails here even if __all__ looks clean."""
    namespace = {}
    exec(f"from saas_sdk.{path.stem} import *", namespace)  # noqa: S102 — that is the check
    # A re-exported *type* still reports __module__ under _gen — that is the
    # mechanism, not the leak. Handing over the generated *module* is the leak,
    # because it hands over everything in it.
    leaked = {
        name
        for name, value in namespace.items()
        if isinstance(value, ModuleType) and value.__name__.startswith("saas_sdk._gen")
    }
    assert not leaked, (
        f"`from saas_sdk.{path.stem} import *` re-exports {sorted(leaked)} from "
        "saas_sdk._gen — add the module's public surface to __all__, or re-export "
        "the individual types rather than the generated module."
    )


def test_documented_examples_do_not_reach_the_generated_package():
    """The README's examples are what a consumer copies, so a leak there
    propagates exactly like one in a signature — and no signature check can see
    it. Prose may name ``saas_sdk._gen`` (the Regenerating section does, and so
    does the rule itself); only the code a reader lifts is constrained."""
    readme = (_SRC.parent.parent / "README.md").read_text()
    blocks = re.findall(r"^```python\n(.*?)^```", readme, re.DOTALL | re.MULTILINE)
    assert blocks, "no python examples found in README.md"

    leaks = [
        f"{line.strip()}"
        for block in blocks
        for line in block.splitlines()
        if "saas_sdk._gen" in line or re.search(r"\.pb\.", line)
    ]
    assert not leaks, (
        "these README examples reach the generated package, teaching consumers the "
        "import this SDK is trying to keep private — use the re-exported name:\n  "
        + "\n  ".join(leaks)
    )


@pytest.mark.parametrize("path", FACADES, ids=lambda p: p.name)
def test_generated_package_is_not_exported(path):
    tree = ast.parse(path.read_text())
    aliases = _generated_aliases(tree)
    if not aliases:
        pytest.skip(f"{path.name} does not import the generated bindings")

    declared = [
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
    ]
    # No __all__ is not a pass: a star-import then re-exports every public
    # module-level name, and the alias bound to the generated package is one of
    # them. Checking only modules that happen to declare one lets the leak
    # through on exactly the module that has no guard.
    assert declared, (
        f"{path.name} imports the generated bindings but declares no __all__, so "
        f"`from {path.stem} import *` re-exports {sorted(aliases)} — the generated "
        "package itself. Declare the module's public surface."
    )

    value = declared[-1]
    assert isinstance(value, (ast.List, ast.Tuple)), (
        f"{path.name} builds __all__ from a non-literal, which this check cannot read — "
        "keep it a literal list so the exported surface stays greppable."
    )
    exported = {e.value for e in value.elts if isinstance(e, ast.Constant)}
    assert not exported & aliases, (
        f"{path.name} lists the generated bindings in __all__ "
        f"({sorted(exported & aliases)}) — that documents saas_sdk._gen as public "
        "surface. Re-export the individual types instead."
    )
