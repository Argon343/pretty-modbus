# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations


class ModbusBackendException(Exception):
    pass


class NoVariablesError(ModbusBackendException):
    pass


class NotConnectedError(ModbusBackendException):
    pass


class UnknownTypeError(ModbusBackendException):
    def __init__(self, type: str, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Unknown type: {type}"
        super().__init__(msg)
        self.type = type


class OutOfBoundsError(ModbusBackendException):
    def __init__(self, type: str, value, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Value {value} is out of bounds for type {type}"
        super().__init__(msg)
        self.type = type
        self.value = value


class NegativeAddressError(ModbusBackendException):
    def __init__(self, name: str, address: int, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Variable '{name}' has negative address {address}. Memory address must always be positive."
        super().__init__(msg)
        self.name = name
        self.address = address


class InvalidAddressLayoutError(ModbusBackendException):
    def __init__(
        self, current: Variable, previous: Variable, msg: Optional[str] = None
    ) -> None:
        if msg is None:
            msg = f"Invalid address for variable '{current.name}' specified: {current.address}. Previous variable store ends at {previous.end}. Variable stores must not overlap."
        super().__init__(msg)
        self.previous = previous
        self.current = current


class VariableNotFoundError(ModbusBackendException):
    def __init__(self, variables: Iterable[str], msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Variables not found: {variables}"
        super().__init__(msg)
        self.variables = variables


class DuplicateVariableError(ModbusBackendException):
    def __init__(self, duplicate: str, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"Duplicate variable name: {duplicate}"
        super().__init__(msg)
        self.duplicate = duplicate


class EncodingError(ModbusBackendException):
    pass


class MissingSubLayoutError(ModbusBackendException):
    def __init__(self, type: str, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"No memory layout defined for: {type}"
        super().__init__(msg)
        self.type = type


class NoSuchSlaveLayoutError(ModbusBackendException):
    def __init__(self, unit, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = f"No memory layout defined for slave '{unit}'"
        super().__init__(msg)
        self.unit = unit


# For wrapping: pymodbus.exceptions.NoSuchSlaveException
class NoSuchSlaveError(ModbusBackendException):
    pass


class ModbusResponseError(ModbusBackendException):
    def __init__(
        self, response: pymodbus.pdu.ExceptionResponse, msg: Optional[str] = None
    ) -> None:
        if msg is None:
            msg = str(response)
        super().__init__(msg)
        self.response = response
