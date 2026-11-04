from typing import Literal

from pydantic import BaseModel, Field


class TabTarget(BaseModel):
    tab: int | str | None = Field(
        None,
        description="Act on this tab without switching to it: an index, or a URL "
        "(query, fragment and trailing slash ignored). Default: the active tab",
    )


class NavigateRequest(TabTarget):
    url: str
    wait_until: Literal["load", "domcontentloaded", "networkidle", "commit"] = "load"


class ClickRequest(TabTarget):
    selector: str = Field(
        description="Playwright selector: CSS, text=..., or role=button[name='...']"
    )
    timeout: int = Field(10_000, ge=100, le=120_000)


class TypeRequest(TabTarget):
    selector: str
    text: str = Field(max_length=20_000)
    submit: bool = Field(False, description="Press Enter after typing")
    clear: bool = Field(True, description="Replace the field's value instead of appending")
    timeout: int = Field(10_000, ge=100, le=120_000)


class PressRequest(TabTarget):
    key: str = Field(description="Key name such as Enter, Tab, Escape, Control+A")
    selector: str | None = None


class ClickAtRequest(TabTarget):
    x: float = Field(ge=0, description="Viewport X in CSS pixels, as on a screenshot")
    y: float = Field(ge=0, description="Viewport Y in CSS pixels, as on a screenshot")


class KeyboardTypeRequest(TabTarget):
    text: str = Field(max_length=20_000)


class WaitRequest(TabTarget):
    selector: str
    timeout: int = Field(15_000, ge=100, le=120_000)


class EvaluateRequest(TabTarget):
    script: str = Field(
        max_length=200_000,
        description="JavaScript expression or function body, e.g. document.title",
    )


class UploadRequest(TabTarget):
    files: list[str] = Field(
        min_length=1,
        max_length=50,
        description="Absolute paths inside a folder listed in FOXPROFILE_UPLOAD_DIRS",
    )
    trigger: str | None = Field(
        None, description="Playwright selector of the button that opens the file chooser"
    )
    input_selector: str | None = Field(
        None, description="Playwright selector of an <input type=file> (instead of trigger)"
    )
    timeout: int = Field(15_000, ge=100, le=120_000)


class TabNewRequest(BaseModel):
    url: str | None = None
