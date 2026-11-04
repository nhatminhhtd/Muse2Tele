import threading
from collections.abc import Callable

import flet as ft

from ...core.strings import get_string
from ...utils.validation import validate_profile_name
from ..theme.colors import COLORS, FONT_BOLD
from ..theme.styles import ACCENT_STYLE, DLG_FIELD_KWARGS
from .profile import _field


def open_clone_dialog(
    page: ft.Page,
    source: str,
    on_clone: Callable[[str, bool, bool], str | None],
) -> None:
    """Ask for the clone's name and what to copy; on_clone runs off the UI thread
    (copying browser data takes a while) and returns an error message or None."""
    name_field = ft.TextField(value=f"{source}-copy", **DLG_FIELD_KWARGS)
    data_cb = ft.Checkbox(label=get_string("clone_include_data"), value=True)
    fp_cb = ft.Checkbox(label=get_string("clone_new_fingerprint"), value=True)
    status = ft.Text("", size=12, color=COLORS["error"], visible=False)

    def work(name: str, include_data: bool, new_fp: bool) -> None:
        error = on_clone(name, include_data, new_fp)
        if error is None:
            page.pop_dialog()
            return
        status.value, status.color = error, COLORS["error"]
        submit.disabled = False
        page.update()

    def on_submit(_: ft.ControlEvent) -> None:
        name = (name_field.value or "").strip()
        valid, msg = validate_profile_name(name)
        if not valid:
            status.value, status.color, status.visible = msg, COLORS["error"], True
            page.update()
            return
        status.value, status.color, status.visible = (
            get_string("cloning_profile"),
            COLORS["text_sub"],
            True,
        )
        submit.disabled = True
        page.update()
        threading.Thread(
            target=work, args=(name, bool(data_cb.value), bool(fp_cb.value)), daemon=True
        ).start()

    submit = ft.Button(
        get_string("clone"), icon=ft.Icons.CONTENT_COPY, style=ACCENT_STYLE, on_click=on_submit
    )
    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["card_bg"],
        shape=ft.RoundedRectangleBorder(radius=12),
        title=ft.Column(
            spacing=4,
            tight=True,
            controls=[
                ft.Text(get_string("clone_title"), size=19, font_family=FONT_BOLD),
                ft.Text(
                    get_string("clone_sub", name=source), size=13.5, color=COLORS["text_sub"]
                ),
            ],
        ),
        content=ft.Container(
            width=420,
            content=ft.Column(
                tight=True,
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    _field(get_string("profile_name"), name_field),
                    ft.Container(height=6),
                    data_cb,
                    fp_cb,
                    ft.Text(get_string("clone_hint"), size=12, color=COLORS["text_dim"]),
                    status,
                ],
            ),
        ),
        actions=[
            ft.TextButton(
                get_string("cancel"),
                style=ft.ButtonStyle(color=COLORS["text_sub"]),
                on_click=lambda _: page.pop_dialog(),
            ),
            submit,
        ],
    )
    page.show_dialog(dlg)
