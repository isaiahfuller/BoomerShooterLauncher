"""Selection and compatibility rules independent of settings and widgets."""

from dataclasses import dataclass

from .catalog import runners as runner_catalog
from .records import Game, InstalledVersion, Modpack, Runner


def prefer_named(records, preferred):
    """Move a remembered record first only while it remains available."""
    return tuple(record for record in records if record.name == preferred) + tuple(
        record for record in records if record.name != preferred
    )


@dataclass(frozen=True)
class Library:
    games: tuple[Game, ...]
    runners: tuple[Runner, ...]
    modpacks: tuple[Modpack, ...]

    def compatible_runners(self, family, preferred=None) -> tuple[Runner, ...]:
        # Custom ports historically remain available for every game family.
        compatible = tuple(
            runner for runner in self.runners
            if runner.name not in runner_catalog
            or family in runner_catalog[runner.name]["games"]
        )
        return prefer_named(compatible, preferred)

    def installed_versions(self, name, *, modpack=False,
                           preferred=None) -> tuple[InstalledVersion, ...]:
        if modpack:
            pack = next((pack for pack in self.modpacks if pack.name == name), None)
            games = tuple(game for game in self.games if pack and game.family == pack.base)
        else:
            games = tuple(game for game in self.games if game.name == name)
        return prefer_named(tuple(version for game in games for version in game.versions),
                            preferred)
