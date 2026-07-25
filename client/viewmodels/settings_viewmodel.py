"""Settings view model placeholder."""

from dataclasses import dataclass, field

from client.core.models import AppConfig


@dataclass(slots=True)
class SettingsViewModel:
    config: AppConfig = field(default_factory=AppConfig)
