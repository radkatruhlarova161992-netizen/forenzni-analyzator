# -*- coding: utf-8 -*-
"""Tenký vstupní bod Streamlit aplikace."""

import streamlit as st

from controllers.app_controller import run_app_controller
from core.config import APP_ICON, APP_LAYOUT, APP_TITLE
from ui.sidebar import initialize_session_state, render_app_navigation, render_header


st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout=APP_LAYOUT)


def main() -> None:
    render_header()
    initialize_session_state({})

    results = st.session_state.get("results", [])
    current_screen = render_app_navigation(results)

    run_app_controller(current_screen)


if __name__ == "__main__":
    main()
