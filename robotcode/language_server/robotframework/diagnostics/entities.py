from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Tuple

from ...common.lsp_types import Position, Range
from ..utils.ast_utils import Token, range_from_token

if TYPE_CHECKING:
    from .library_doc import KeywordDoc


@dataclass
class SourceEntity:
    line_no: int
    col_offset: int
    end_line_no: int
    end_col_offset: int
    source: Optional[str]

    @property
    def range(self) -> Range:
        return Range(
            start=Position(line=self.line_no - 1, character=self.col_offset),
            end=Position(line=self.end_line_no - 1, character=self.end_col_offset),
        )

    def __hash__(self) -> int:
        return hash((self.line_no, self.col_offset, self.end_line_no, self.end_col_offset, self.source))


@dataclass
class Import(SourceEntity):
    name: Optional[str]
    name_token: Optional[Token]

    @property
    def range(self) -> Range:
        return Range(
            start=Position(
                line=self.name_token.lineno - 1 if self.name_token is not None else self.line_no - 1,
                character=self.name_token.col_offset if self.name_token is not None else self.col_offset,
            ),
            end=Position(
                line=self.name_token.lineno - 1 if self.name_token is not None else self.end_line_no - 1,
                character=self.name_token.end_col_offset if self.name_token is not None else self.end_col_offset,
            ),
        )


@dataclass
class LibraryImport(Import):
    args: Tuple[str, ...] = ()
    alias: Optional[str] = None

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.args,
                self.alias,
            )
        )


@dataclass
class ResourceImport(Import):
    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
            )
        )


@dataclass
class VariablesImport(Import):
    args: Tuple[str, ...] = ()

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.args,
            )
        )


class InvalidVariableError(Exception):
    pass


class VariableMatcher:
    def __init__(self, name: str) -> None:
        from robot.variables.search import VariableSearcher

        from ..utils.match import normalize

        self.name = name

        searcher = VariableSearcher("$@&%", ignore_errors=True)
        match = searcher.search(name)

        if match.base is None:
            raise InvalidVariableError(f"Invalid variable '{name}'")

        self.base = match.base

        self.normalized_name = str(normalize(self.base))

    def __eq__(self, o: object) -> bool:
        from robot.utils.normalizing import normalize
        from robot.variables.search import VariableSearcher

        if isinstance(o, VariableMatcher):
            return o.normalized_name == self.normalized_name
        elif isinstance(o, str):
            searcher = VariableSearcher("$@&%", ignore_errors=True)
            match = searcher.search(o)
            base = match.base
            normalized = str(normalize(base))
            return self.normalized_name == normalized
        else:
            return False

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={repr(self.name)})"


class VariableDefinitionType(Enum):
    VARIABLE = "variable"
    LOCAL_VARIABLE = "local variable"
    ARGUMENT = "argument"
    COMMAND_LINE_VARIABLE = "command line variable"
    BUILTIN_VARIABLE = "builtin variable"
    IMPORTED_VARIABLE = "imported variable"
    ENVIRONMENT_VARIABLE = "environment variable"
    VARIABLE_NOT_FOUND = "variable not found"


@dataclass
class VariableDefinition(SourceEntity):
    name: str
    name_token: Optional[Token]
    type: VariableDefinitionType = VariableDefinitionType.VARIABLE

    has_value: bool = field(default=False, compare=False)
    resolvable: bool = field(default=False, compare=False)

    value: Any = field(default=None, compare=False)

    __matcher: Optional[VariableMatcher] = None

    @property
    def matcher(self) -> VariableMatcher:
        if self.__matcher is None:
            self.__matcher = VariableMatcher(self.name)
        return self.__matcher

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))

    @property
    def name_range(self) -> Range:
        if self.name_token is not None:
            return range_from_token(self.name_token)
        else:
            return self.range

    @property
    def range(self) -> Range:
        return Range(
            start=Position(
                line=self.line_no - 1,
                character=self.col_offset,
            ),
            end=Position(
                line=self.end_line_no - 1,
                character=self.end_col_offset,
            ),
        )


@dataclass
class LocalVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.LOCAL_VARIABLE

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class BuiltInVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.BUILTIN_VARIABLE
    resolvable: bool = True

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class CommandLineVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.COMMAND_LINE_VARIABLE
    resolvable: bool = True

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class ArgumentDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ARGUMENT
    keyword_doc: Optional["KeywordDoc"] = None

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class ImportedVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.IMPORTED_VARIABLE

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class EnvironmentVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ENVIRONMENT_VARIABLE
    resolvable: bool = True

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class VariableNotFoundDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.VARIABLE_NOT_FOUND
    resolvable: bool = False

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))
