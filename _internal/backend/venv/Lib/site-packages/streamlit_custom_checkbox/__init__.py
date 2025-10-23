import os
import streamlit.components.v1 as components

_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "streamlit_custom_checkbox",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    _component_func = components.declare_component("streamlit_custom_checkbox", path=build_dir)

def st_custom_checkbox(label: str, value: bool = False, disabled: bool = False, key=None):
    """Display a custom styled checkbox component.

    Parameters
    ----------
    label: str
        A short label explaining to the user what this checkbox is for.
    value: bool
        The initial value of the checkbox.
    disabled: bool
        Whether the checkbox is disabled.
    key: str or None
        An optional key that uniquely identifies this component.

    Returns
    -------
    bool
        The current value of the checkbox.
    """
    
    component_value = _component_func(
        label=label, 
        value=value, 
        disabled=disabled,
        key=key,
        default=value
    )
    return component_value if component_value is not None else value