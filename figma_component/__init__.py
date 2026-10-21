from pathlib import Path

import streamlit.components.v1 as components


build_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if not (build_dir / "index.html").is_file():
    raise FileNotFoundError(
        "The compiled frontend is missing. Run 'npm run build' in frontend/ "
        "and commit frontend/dist/ before deploying to Streamlit Cloud."
    )

_component_func = components.declare_component(
    "figma_component",
    path=str(build_dir),
)


def render(title=None, view=None, role=None, key=None, **kwargs):
    return _component_func(title=title, view=view, role=role, key=key, **kwargs)
