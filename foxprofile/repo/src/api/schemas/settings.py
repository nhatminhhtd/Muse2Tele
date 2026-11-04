from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    download_dir: str = Field(description="Folder downloads are saved to right now")
    default_download_dir: str
    custom: bool = Field(description="True when the folder was chosen in the panel")


class SettingsUpdate(BaseModel):
    download_dir: str | None = Field(
        default=None, description="Full folder path; empty restores the default"
    )
