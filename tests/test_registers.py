# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pretty_modbus import registers
from pretty_modbus.exceptions import (
    InvalidAddressLayoutError,
    VariableNotFoundError,
    DuplicateVariableError,
    NoVariablesError,
    NegativeAddressError,
    UnknownTypeError,
    OutOfBoundsError,
)


class TestVariable:
    def test_init_failure(self):
        with pytest.raises(NegativeAddressError):
            registers.Number(name="", type="i64", address=-1)


class TestRegisterLayout:
    @pytest.fixture
    def layout(self):
        return registers.RegisterLayout(
            [
                registers.Str("str", length=5, address=2),
                registers.Number("i", "i32"),
                registers.Struct(
                    "struct",
                    [
                        registers.Field("CHANGED", "u1"),
                        registers.Field("ELEMENT_TYPE", "u7"),
                        registers.Field("ELEMENT_ID", "u5"),
                    ],
                    address=19,
                ),
                registers.Number("f", "f16"),
            ],
            byteorder="<",
            wordorder=">",
        )

    @pytest.fixture
    def data(self):
        return {
            "variables": [
                {"name": "str", "type": "str", "length": 5, "address": 2},
                {"name": "i", "type": "i32"},
                {
                    "name": "struct",
                    "type": "struct",
                    "fields": [
                        {"name": "CHANGED", "format": "u1"},
                        {"name": "ELEMENT_TYPE", "format": "u7"},
                        {"name": "ELEMENT_ID", "format": "u5"},
                    ],
                    "address": 19,
                },
                {"name": "f", "type": "f16"},
            ],
            "byteorder": "<",
            "wordorder": ">",
        }

    @pytest.mark.parametrize(
        "variables, exception",
        [
            (
                [registers.Number("foo", "i64", 2), registers.Number("bar", "i32", 5)],
                InvalidAddressLayoutError,
            ),
            (
                [registers.Number("foo", "i64", 2), registers.Str("foo", 5)],
                DuplicateVariableError,
            ),
            ([], NoVariablesError),
        ],
    )
    def test_init_failure(self, variables, exception):
        with pytest.raises(exception) as e:
            registers.RegisterLayout(variables)

    def test_build_payload_failure(self, layout):
        with pytest.raises(VariableNotFoundError):
            layout.build_payload({"str": "hello", "world": "!"})

    def test_load(self, layout, data):
        loaded = registers.RegisterLayout.load(**data)
        print(loaded._variables)
        print(layout._variables)
        assert loaded == layout


class TestPayloadBuilder:
    @pytest.mark.parametrize(
        "type, value, expected, byteorder, wordorder",
        [
            ("i16", 777, [b"\t\x03"], "<", ">"),
            ("i16", 777, [b"\x03\t"], ">", ">"),
            ("i16", -555, [b"\xd5\xfd"], "<", ">"),
            ("u16", 64981, [b"\xd5\xfd"], "<", ">"),
            ("i32", 67108864, [b"\x00\x04", b"\x00\x00"], "<", ">"),
            ("i32", 67108864, [b"\x00\x00", b"\x00\x04"], "<", "<"),
            ("i32", -555666777, [b"\xe1\xde", b"\xa72"], "<", ">"),
            ("u32", 3739300519, [b"\xe1\xde", b"\xa72"], "<", ">"),
            (
                "i64",
                288230389103853584,
                [b"\x00\x04", b"\x03\x00", b"\x02\x04", b"\x10\x00"],
                "<",
                ">",
            ),
            (
                "i64",
                288230389103853584,
                [b"\x04\x00", b"\x00\x03", b"\x04\x02", b"\x00\x10"],
                ">",
                ">",
            ),
            (
                "i64",
                288230389103853584,
                [b"\x10\x00", b"\x02\x04", b"\x03\x00", b"\x00\x04"],
                "<",
                "<",
            ),
            (
                "i64",
                288230389103853584,
                [b"\x00\x10", b"\x04\x02", b"\x00\x03", b"\x04\x00"],
                ">",
                "<",
            ),
            # ("i64", -123456789123456789, [b"I\xfe\xb4d/S\xeb\xa0", "<", ">"),
            # ("u64", 18323287284586094827, [b"I\xfe\xb4d/S\xeb\xa0", "<", ">"),
            ("i64", 1, [b"\x00\x00", b"\x00\x00", b"\x00\x00", b"\x01\x00"], "<", ">"),
            ("f64", 3.141, [b"\t@", b"\xc4 ", b"\xa5\x9b", b"T\xe3"], "<", ">"),
            ("f64", 3.141, [b"\xe3T", b"\x9b\xa5", b" \xc4", b"@\t"], ">", "<"),
        ],
    )
    def test_encode_number_single(self, type, value, expected, byteorder, wordorder):
        builder = registers._PayloadBuilder(byteorder=byteorder, wordorder=wordorder)
        var = registers.Number("", type)
        var.encode(builder, value)
        assert builder.build() == expected

    @pytest.mark.parametrize(
        "payload, expected, byteorder, wordorder",
        [
            (
                [("i16", 777), ("i32", 67108864), ("f64", 3.141)],
                [
                    b"\t\x03",
                    b"\x00\x04",
                    b"\x00\x00",
                    b"\t@",
                    b"\xc4 ",
                    b"\xa5\x9b",
                    b"T\xe3",
                ],
                "<",
                ">",
            ),
        ],
    )
    def test_encode_number_multiple(self, payload, expected, byteorder, wordorder):
        builder = registers._PayloadBuilder(byteorder, wordorder)
        for type_, value in payload:
            var = registers.Number("", type_)
            var.encode(builder, value)
        assert builder.build() == expected

    def test_encode_string(self):
        builder = registers._PayloadBuilder("<", ">")
        var = registers.Str("", 7)
        var.encode(builder, "Hullo")
        assert builder.build() == [b"Hu", b"ll", b"o ", b"  "]

    @pytest.mark.parametrize(
        "type, value, exception",
        [
            pytest.param("i8", 0, UnknownTypeError, id="8-bit types not supported"),
            pytest.param("i16", 32768, OutOfBoundsError),
            pytest.param("i16", -32769, OutOfBoundsError),
            pytest.param("i32", 2147483648, OutOfBoundsError),
            pytest.param("i32", -2147483649, OutOfBoundsError),
            pytest.param("i64", 9223372036854775808, OutOfBoundsError),
            pytest.param("i64", -9223372036854775809, OutOfBoundsError),
            pytest.param("u16", 65536, OutOfBoundsError),
            pytest.param("u16", -1, OutOfBoundsError),
            pytest.param("u32", 4294967296, OutOfBoundsError),
            pytest.param("u32", -1, OutOfBoundsError),
            pytest.param("u64", 18446744073709551616, OutOfBoundsError),
            pytest.param("u64", -1, OutOfBoundsError),
        ],
    )
    def test_encode_number_failure(self, type, value, exception):
        builder = registers._PayloadBuilder(byteorder="<", wordorder=">")
        with pytest.raises(exception):
            builder.add_number(type, value)


@pytest.mark.parametrize(
    "fields, values, byteorder, wordorder",
    [
        (
            [
                registers.Field("CHANGED", "u1"),
                registers.Field("ELEMENT_TYPE", "u7"),
                registers.Field("ELEMENT_ID", "u8"),
            ],
            {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "<",
            ">",
        ),
        pytest.param(
            [
                registers.Field("CHANGED", "u1"),
                registers.Field("ELEMENT_TYPE", "u7"),
                registers.Field("ELEMENT_ID", "u5"),
            ],
            {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "<",
            ">",
            id="With padding",
        ),
    ],
)
def test_encode_decode_struct(fields, values, byteorder, wordorder):
    s = registers.Struct("", fields)
    builder = registers._PayloadBuilder(byteorder, wordorder)
    s.encode(builder, values)
    payload = b"".join(builder.build())
    decoder = registers._PayloadDecoder(payload, byteorder, wordorder)
    assert s.decode(decoder) == values


class TestPayloadDecoder:
    @pytest.mark.parametrize(
        "type, expected, payload, byteorder, wordorder",
        [
            ("i16", 777, b"\t\x03", "<", ">"),
            ("i16", 777, b"\x03\t", ">", ">"),
            ("i16", -555, b"\xd5\xfd", "<", ">"),
            ("u16", 64981, b"\xd5\xfd", "<", ">"),
            ("i32", 67108864, b"\x00\x04\x00\x00", "<", ">"),
            ("i32", 67108864, b"\x00\x00\x00\x04", "<", "<"),
            ("i32", -555666777, b"\xe1\xde\xa72", "<", ">"),
            ("u32", 3739300519, b"\xe1\xde\xa72", "<", ">"),
            ("i64", 288230389103853584, b"\x00\x04\x03\x00\x02\x04\x10\x00", "<", ">"),
            ("i64", 288230389103853584, b"\x04\x00\x00\x03\x04\x02\x00\x10", ">", ">"),
            ("i64", 288230389103853584, b"\x10\x00\x02\x04\x03\x00\x00\x04", "<", "<"),
            ("i64", 288230389103853584, b"\x00\x10\x04\x02\x00\x03\x04\x00", ">", "<"),
            ("i64", -123456789123456789, b"I\xfe\xb4d/S\xeb\xa0", "<", ">"),
            ("u64", 18323287284586094827, b"I\xfe\xb4d/S\xeb\xa0", "<", ">"),
            ("i64", 1, b"\x00\x00\x00\x00\x00\x00\x01\x00", "<", ">"),
            ("f64", 3.141, b"\t@\xc4 \xa5\x9bT\xe3", "<", ">"),
            ("f64", 3.141, b"\xe3T\x9b\xa5 \xc4@\t", ">", "<"),
        ],
    )
    def test_decode_single(self, type, expected, payload, byteorder, wordorder):
        builder = registers._PayloadDecoder(payload, byteorder, wordorder)
        var = registers.Number("", type)
        assert var.decode(builder) == expected
