from pathlib import Path

import streamlit.components.v1 as components


_RELEASE = True
build_dir = (Path(__file__).resolve().parent.parent / "frontend" / "dist").resolve()

print(f"Loading component from: {build_dir}")

_component_func = components.declare_component(
    "figma_component",
    path=str(build_dir),
)


def render(title=None, view=None, role=None, key=None, **kwargs):
    return _component_func(title=title, view=view, role=role, key=key, **kwargs)
