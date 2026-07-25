"""Application-level settings."""

from dataclasses import dataclass
from pathlib import Path

from client.version import APP_NAME, APP_VERSION, COMPANY_NAME, ORGANIZATION_NAME, PRODUCT_NAME


@dataclass(slots=True)
class AppSettings:
    app_name: str = APP_NAME
    product_name: str = PRODUCT_NAME
    app_version: str = APP_VERSION
    company_name: str = COMPANY_NAME
    organization_name: str = ORGANIZATION_NAME
    data_dir: Path = Path("client_data")
    database_name: str = "client.db"
    storage_meta_name: str = "storage_meta.json"
    runtime_state_name: str = "runtime_state.json"
    config_name: str = "config.json"
    tasks_name: str = "tasks.json"
    history_name: str = "history.json"
    window_width: int = 1280
    window_height: int = 820

    @property
    def resources_dir(self) -> Path:
        return Path(__file__).resolve().parent / "resources"

    @property
    def icon_svg_path(self) -> Path:
        return self.resources_dir / "app_icon.svg"

    @property
    def icon_ico_path(self) -> Path:
        return self.resources_dir / "app_icon.ico"

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_name

    @property
    def storage_meta_path(self) -> Path:
        return self.data_dir / self.storage_meta_name

    @property
    def runtime_state_path(self) -> Path:
        return self.data_dir / self.runtime_state_name

    @property
    def config_path(self) -> Path:
        return self.data_dir / self.config_name

    @property
    def tasks_path(self) -> Path:
        return self.data_dir / self.tasks_name

    @property
    def history_path(self) -> Path:
        return self.data_dir / self.history_name

    @classmethod
    def load(cls) -> "AppSettings":
        settings = cls()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        return settings
