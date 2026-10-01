"""Parse the bundled UZDoom IWADINFO identification rules."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re


@dataclass(frozen=True)
class IWadDefinition:
    name: str
    game: str
    filename: str | None
    must_contain: tuple[str, ...]
    fields: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class IWadCatalog:
    definitions: tuple[IWadDefinition, ...]
    names: tuple[str, ...]
    order: tuple[str, ...]


_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|[{}=,]|[^\s{}=,]+')


def parse_iwadinfo(source: str) -> IWadCatalog:
    tokens = [token for token in _TOKEN.findall(source) if not token.startswith('//')]
    definitions = []
    sections = {'names': (), 'order': ()}
    pos = 0

    def value(token):
        return bytes(token[1:-1], 'utf-8').decode('unicode_escape') if token.startswith('"') else token

    while pos < len(tokens):
        section = tokens[pos].lower()
        pos += 1
        if section not in ('iwad', 'names', 'order') or pos >= len(tokens) or tokens[pos] != '{':
            raise ValueError(f'Invalid IWADINFO section: {section}')
        pos += 1
        if section == 'iwad':
            fields = {}
            while pos < len(tokens) and tokens[pos] != '}':
                key = tokens[pos].lower()
                pos += 1
                if pos >= len(tokens) or tokens[pos] != '=':
                    raise ValueError(f'Expected assignment for {key}')
                pos += 1
                values = []
                while pos < len(tokens) and tokens[pos] not in ('}', '='):
                    if tokens[pos] == ',':
                        pos += 1
                        continue
                    if pos + 1 < len(tokens) and tokens[pos + 1] == '=':
                        break
                    values.append(value(tokens[pos]))
                    pos += 1
                fields[key] = tuple(values)
            if 'name' not in fields or 'mustcontain' not in fields:
                raise ValueError('IWad requires Name and MustContain')
            definitions.append(IWadDefinition(fields['name'][0],
                fields.get('game', ('',))[0], fields.get('iwadname', (None,))[0],
                tuple(item.upper() for item in fields['mustcontain']), fields))
        else:
            values = []
            while pos < len(tokens) and tokens[pos] != '}':
                if tokens[pos] != ',':
                    values.append(value(tokens[pos]))
                pos += 1
            sections[section] = tuple(values)
        if pos >= len(tokens):
            raise ValueError('Unclosed IWADINFO section')
        pos += 1
    return IWadCatalog(tuple(definitions), sections['names'], sections['order'])


@lru_cache(maxsize=1)
def bundled_catalog() -> IWadCatalog:
    return parse_iwadinfo(Path(__file__).with_name('assets').joinpath('iwadinfo.txt').read_text())
