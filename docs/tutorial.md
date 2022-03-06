<!--
SPDX-FileCopyrightText: 2022 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH

SPDX-License-Identifier: GPL-3.0-or-later
-->

## Tutorial

**pretty-modbus** allows you to use the [pymodbus], but write and read to the
server's store using a _memory layout_ as abstraction.

### Register Layouts

_Register layouts_ (used for holding registers and input registers) are composed
to _variables_. Variables are created using the classes `Number`, `Str` and
`Struct` (which consist of `Field` objects). Numbers are initialized with a name
and their type:

```python
Number("x", "i16")  # A signed 16-byte integer
Number("y", "u32")  # An unsigned 32-byte integer
Number("z", "f64")  # A 64-byte float
```

Allowed values for the type are `"i16"`, `"i32"`, `"i64"`, `"u16"`, `"u32"`,
`"u64"`, `"f16"`, `"f32"` and `"f64"`.

Strings are initialized with a name and the reserved length in bytes:

```python
Str("u", 3)  # Can hold "foo", but not "spam"
Str("v", 13)  # Good for "Hello, world!"
```

Strings with odd length reserve `length + 1` bytes (i.e. we round to the nearest
register).

Structs represent a sub-layout, which may define multiple variables within a
single byte. For example:

```python
Struct(
    "my_struct",
    [
        Field("ready", "u1"),  # 1-bit unsigned int
        Field("type", "u7"),  # 7-bit unsigned int
        Field("value", "u8"),  # 8-bit unsigned int
    ],
    endianness=Endian.little,
)
```

We use the [bitstruct] package to implement structs. The type of each field is
specified using the
[syntax defined by bitstructs](https://github.com/eerimoq/bitstruct).

The variables are composed into a register layout as follows:

```python
register_layout = RegisterLayout(
    variables=[
        Number("x", "i16")  # A signed 16-byte integer
        Number("y", "u32")  # An unsigned 32-byte integer
        Number("z", "f64")  # A 64-byte float
        Str("u", 3)  # Can hold "foo", but not "spam"
        Str("v", 13)  # Good for "Hello, world!"
        Struct(
            "my_struct",
            [
                Field("ready", "u1"),  # 1-bit unsigned int
                Field("type", "u7"),  # 7-bit unsigned int
                Field("value", "u8"),  # 8-bit unsigned int
            ],
            endianness=Endian.little,
        )
    ],
    byteorder=Endian.little,
    wordorder=Endian.big
)
```

The `byteorder` and `wordorder` parameters are optional (default values are
`Endian.little` and `Endian.big`) and apply to the `Number` objects in the
layout, but not the `Struct` or `Str` objects.

Variables can be initialized with an additional parameter `address`, which
determines its position in the register layout. If left blank (default), the
address is zero (for the first variable in the layout) or is derived from the
position of the previous variable:

```python
register_layout = RegisterLayout(
    variables=[
        Number("x", "i16")  # A signed 16-byte integer @ address 0
        Number("y", "u32")  # An unsigned 32-byte integer @ address 2
        Number("z", "f64", address=8)  # A 64-byte float @ address 8
        Str("u", 3)  # Can hold "foo", but not "spam" @ address 16
        Str("v", 13)  # Good for "Hello, world!" @ address 20
        Struct(
            "my_struct",
            [
                Field("ready", "u1"),  # 1-bit unsigned int
                Field("type", "u7"),  # 7-bit unsigned int
                Field("value", "u8"),  # 8-bit unsigned int
            ],
            endianness=Endian.little,
        )  # @ address 34
    ],
    byteorder=Endian.little,
    wordorder=Endian.big
)
```

### Coil Layouts

_Coil layouts_, which are used as memory layouts for coils and discrete inputs,
consist of `Variable` objects from the `coils` module. Each variable consists of
a name, a size (number of coils) and an optional address (sample idea as for
register layouts):

```python
Variable("x")  # Variable of size 1
Variable("y", size=3)  # Variable of size 3
```

Coil layouts are created as follows (with address derived as described above in
the case of registers):

```python
coil_layout = CoilLayout(
    [
        Variable("x", address=1),  # Variable of size 1 @ address 1
        Variable("y", size=3")  # Variable of size 3 @ address 2
    ]
)
```

### Slave and Server Context Layouts

Register and coil layouts are composed into a _slave context layout_ (i.e. the
layout of one store or unit), using the class `SlaveContextLayout` from
`layout`:

```python
slave_layout = SlaveContextLayout(
    holding_registers=register_layout, coils=coil_layout
)
```

The `__init__` takes for parameters, `holding_registers`, `input_registers`,
`coils` and `discrete_inputs`, any of which may be left at default (leaving the
layout undefined).

Slave layouts are composed into a `ServerContextLayout`, describing the layout
of the entire memory available in the Modbus network. This is done by mapping
each unit id the respective slave context layout:

```python
server_layout = ServerContextLayout(
    {
        0: slave_layout,  # Slave layout of unit 0
        # ...
    }
)
```

To use any of these layouts, we need to associate them with a client or server.
We will start with the client/server pairs based on [pymodbus]'s `async_io`
module.

### `asyncio` Client and Server

You will find a wrapper `Protocol` for the `ModbusClientProtocol` class of
[pymodbus]:

```python
_, client = pymodbus.client.asynchronous.tcp.AsyncModbusTCPClient(
    pymodbus.client.asynchronous.schedulers.ASYNC_IO,
    port=5020,
    loop=event_loop,
)
protocol = Protocol(client.protocol, server_layout)
```

The `Protocol` class offers `read_*` and `write_*` coroutines, where `*` is
`holding_register(s)`, `coil(s)`, `input_register(s)` or `discrete_input(s)`
(obviously `write_*` only for the former two). These follow the following API:

```python
def read_*s(
    self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFALT_SLAVE
) -> dict[str, ValueType]:
    pass

def read_*(
    self, var: str, unit: KeyType = DEFAULT_SLAVE
) -> ValueType:
    pass

def write_*s(
    self, values: dict[str, ValueType], unit: KeyType = DEFAULT_SLAVE
) -> None:
    pass

def write_*(
    self, var: str, value: ValueType, unit: KeyType = DEFAULT_SLAVE
) -> None:
    pass
```

The `variables` parameter can contain any name from the variables in the
respective layout. The `values` parameter is a dictionary that maps variable
names to values to write. The default `unit` is zero. The `KeyType` is basically
any `Hashable`, and `ValueType` needs to be appropriate for the type of variable
you're writing.

You can use the `Client` class to store the event loop in case you need to
protect it from garbage collection.

The `Server` class wraps the [pymodbus] server object and offers `start` and
`stop` functions.

**Note.** The `async_io` client blocks the event loop, so you can't use the
server and client in the same thread. We use the `threaded` module for this use
case.

### Threaded Client

The `Client` class from `threaded` uses the same interface as
`async_io.Protocol` for reading and writing, but is otherwise structured
differently. Instances are created by passing a [pymodbus] factory, a
`ServerContextLayout` and a set of `*args` and `**kwargs` to pass to the
factory. The [pymodbus] client must be from `pymodbus.client.sync`, and it is
run in a seperate thread that the `Client` instance manages. The thread can be
started and stopped using `start()` and `stop()`, which are _non-blocking_:

```python
client = Client(
    factory=ModbusSerialClient,
    layout=layout,
    port="/dev/cu.usbserial-A900NBT9",
    baudrate=115200,
    method="rtu",
)
print("Starting client...")
client.start()
time.sleep(1.0)  # Or do some productive stuff...
print("Stopping client...")
client.stop(timeout=0.1)
```

The `stop()` method terminates and then joins the thread that runs the
[pymodbus] client (currently, the library doens't seem to leave us any other
choice in the matter) and raises a `TimeoutError` if that takes longer than the
specified amount in seconds.

### Threaded Server

The `Server` class functions similarly in that it also takes a `factory`
argument and `*args` and `**kwargs` for that factory. It is run in a separate
process.

```python
layout = ServerContextLayout({UNIT: slave_layout})
modbus_slave_context = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [17] * 100),
    co=ModbusSequentialDataBlock(0, [17] * 100),
    hr=ModbusSequentialDataBlock(0, [17] * 100),
    ir=ModbusSequentialDataBlock(0, [17] * 100),
    zero_mode=True,
)
modbus_server_context = ModbusServerContext(
    slaves={UNIT: modbus_slave_context}, single=False
)
server = Server(
    factory=StartSerialServer,
    daemons=[daemon],
    layout=layout,
    context=modbus_server_context,
    port="/dev/cu.usbserial-A900NBT9",
    baudrate=115200,
    framer=ModbusRtuFramer,
)
print("Starting server...")
server.start()
time.sleep(1.0)
print("Stopping server...")
server.stop()
```

Note that the use of a child process means that if a datastore is passed as
argument or keyworded argument, that datastore is pickled into a new process
before being used. The datastore from the parent process remains unused. This
poses a problem if you wish to modify the datastore directly (without the use of
a client). This problem is mitigated using `Daemon` objects.

### Daemons for Threaded Server

You may find yourself wanting to modify the datastore of a local Modbus server
directly. **pretty-modbus** offers an interface `ServerContext` that allows you
to change the memory of the datastore using a server layout.

The `ServerContext` object is a straightforward composition of
`ServerContextLayout` and a `pymodbus.datastore.context.ModbusServerContext`.
The `get_*` and `set_*` methods follow the same interface as the `read`/`write`
methods of `async_io.Protocol` and `threaded.Client`. They are also available as
coroutines `get_*_coro` and `set_*_coro`.

As mentioned in the previous section, when using `threaded`, the datastore is
stored in the server process, making it difficult to manipulate it. This is what
the `threaded.Daemon` class is for.

Each daemon is initialized with a `job` and a `period`. The `job` parameter must
be a callable with the following interface:

```python
def abstract_job(context: ServerContext) -> Any:
    pass
```

When a daemon is passed to a `threaded.Server` using the `daemons` parameter of
`Server.__init__`, then it executes the `job` every `period` seconds once the
server is started. The `context` parameter of the daemon is the server's
datastore in composition with the `layout` passed to the `Server` on
initialization.

**Note.** Whenever you are using a local datastore, be sure to initialize it
with the `zero_mode=True` option. Otherwise, **pretty-modbus** layouts will be
thrown off.

<!-- Links -->

[pymodbus]: https://github.com/riptideio/pymodbus
[example]: example/
[bitstruct]: https://github.com/eerimoq/bitstruct
