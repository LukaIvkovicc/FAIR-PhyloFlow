from __future__ import annotations

import subprocess

import streamlit as st

st.set_page_config(page_title="FAIR PhyloFlow", layout="wide")
st.title("FAIR PhyloFlow")
st.caption("Configuration-driven, decision-aware phylogenomics")

st.write(
    "This UI is intentionally minimal. The CLI output reports the project-specific location of each generated artifact."
)

config_path = st.text_input("Path to project.yaml", value="examples/demo_project/project.yaml")

col1, col2, col3, col4 = st.columns(4)


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + ("\n" + exc.stderr if exc.stderr else "")
        return 124, f"{output}\nCommand timed out after 600 seconds."
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, out


def _show_result(code: int, output: str) -> None:
    st.code(output)
    if code == 0:
        st.success("Command completed successfully.")
    else:
        st.error(f"Command failed with exit code {code}.")


with col1:
    if st.button("Check"):
        code, out = _run(["fair-phyloflow", "check", config_path])
        _show_result(code, out)

with col2:
    if st.button("Plan"):
        code, out = _run(["fair-phyloflow", "plan", config_path])
        _show_result(code, out)

with col3:
    if st.button("Run"):
        code, out = _run(["fair-phyloflow", "run", config_path, "--no-execute"])
        _show_result(code, out)

with col4:
    if st.button("Report"):
        code, out = _run(["fair-phyloflow", "report", config_path])
        _show_result(code, out)
