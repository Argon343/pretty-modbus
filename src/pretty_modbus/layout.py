# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import dataclasses

from pretty_modbus.exceptions import (
    NoSuchSlaveLayoutError,
    MissingSubLayoutError,
    VariableNotFoundError,
)


@dataclasses.dataclass
class SlaveContextLayout:
    holding_registers: Optional[registers.RegisterLayout] = None
    input_registers: Optional[registers.RegisterLayout] = None
    coils: Optional[coils.CoilLayout] = None
    discrete_inputs: Optional[coils.CoilLayout] = None


_TYPES = [
    "input_registers",
    "holding_registers",
    "coils",
    "discrete_inputs",
]


class ServerContextLayout:
    def __init__(self, slaves: dict[Key, SlaveContextLayout]) -> None:
        self._slaves = slaves

    def find(self, var: str) -> tuple[Key, str]:
        """Find the type and the containing unit of ``var``.

        Args:
            var: The variable to find

        Returns:
            Tuple ``(type, unit)``

        Raises:
            VariableNotFoundError:
                If there is no layout that contains the variable
        """
        for unit, _ in self._slaves.items():
            for type_ in _TYPES:
                layout = self._get(unit, type_)
                if layout is None:
                    continue
                if var in layout:
                    return unit, type_
        raise VariableNotFoundError(var)

    def where(self, var: str, unit: Optional[Key] = None) -> str:
        """Return where a variable is stored.

        Returns:
            ``"input_registers"``, ``"holding_registers"``, ``"coils"`` or
            ``"discrete_inputs"`` or ``None``, depending on where and if
            the variable is stored

        Raises:
            VariableNotFoundError:
                If there is no layout that contains the variable
        """
        for type_ in _TYPES:
            layout = self._get(unit, type_)
            if layout is None:
                continue
            if var in layout:
                return type_
        raise VariableNotFoundError(var)

    def _get(
        self, unit: Key, type: str
    ) -> Union[registers.RegisterLayout, coils.CoilLayout]:
        slave = self._slaves.get(unit)
        if slave is None:
            raise NoSuchSlaveLayoutError(unit)
        layout = getattr(slave, type, None)
        return layout

    def _get_fallible(
        self, unit: Key, type: str
    ) -> registeres.RegisterLayout | coils.CoilLayout:
        layout = self._get(unit, type)
        if layout is None:
            raise MissingSubLayoutError(unit, type)
        return layout

    def get_holding_register_layout(self, unit: Key) -> registers.RegisterLayout:
        return self._get_fallible(unit, "holding_registers")

    def get_input_register_layout(self, unit: Key) -> registers.RegisterLayout:
        return self._get_fallible(unit, "input_registers")

    def get_coil_layout(self, unit: Key) -> coils.CoilLayout:
        return self._get_fallible(unit, "coils")

    def get_discrete_input_layout(self, unit: Key) -> coils.CoilLayout:
        return self._get_fallible(unit, "discrete_inputs")
