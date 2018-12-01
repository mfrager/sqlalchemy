# sqlite/pysqlcipher3.py
# Copyright (C) 2005-2018 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: sqlite+pysqlcipher3
    :name: pysqlcipher3
    :dbapi: pysqlcipher3
    :connectstring: sqlite+pysqlcipher3://:passphrase/file_path[?kdf_iter=<iter>]
    :url: https://pypi.python.org/pypi/pysqlcipher3

    ``pysqlcipher3`` is a fork of the standard ``pysqlite`` driver to make
    use of the `SQLCipher <https://www.zetetic.net/sqlcipher>`_ backend.

    ``pysqlcipher33`` is a fork of ``pysqlcipher3`` for Python 3. This dialect
    will attempt to import it if ``pysqlcipher3`` is non-present.

    .. versionadded:: 1.1.4 - added fallback import for pysqlcipher33

    .. versionadded:: 0.9.9 - added pysqlcipher3 dialect

Driver
------

The driver here is the `pysqlcipher3 <https://pypi.python.org/pypi/pysqlcipher3>`_
driver, which makes use of the SQLCipher engine.  This system essentially
introduces new PRAGMA commands to SQLite which allows the setting of a
passphrase and other encryption parameters, allowing the database
file to be encrypted.

`pysqlcipher33` is a fork of `pysqlcipher3` with support for Python 3,
the driver is the same.

Connect Strings
---------------

The format of the connect string is in every way the same as that
of the :mod:`~sqlalchemy.dialects.sqlite.pysqlite` driver, except that the
"password" field is now accepted, which should contain a passphrase::

    e = create_engine('sqlite+pysqlcipher3://:testing@/foo.db')

For an absolute file path, two leading slashes should be used for the
database name::

    e = create_engine('sqlite+pysqlcipher3://:testing@//path/to/foo.db')

A selection of additional encryption-related pragmas supported by SQLCipher
as documented at https://www.zetetic.net/sqlcipher/sqlcipher-api/ can be passed
in the query string, and will result in that PRAGMA being called for each
new connection.  Currently, ``cipher``, ``kdf_iter``
``cipher_page_size`` and ``cipher_use_hmac`` are supported::

    e = create_engine('sqlite+pysqlcipher3://:testing@/foo.db?cipher=aes-256-cfb&kdf_iter=64000')


Pooling Behavior
----------------

The driver makes a change to the default pool behavior of pysqlite
as described in :ref:`pysqlite_threading_pooling`.   The pysqlcipher3 driver
has been observed to be significantly slower on connection than the
pysqlite driver, most likely due to the encryption overhead, so the
dialect here defaults to using the :class:`.SingletonThreadPool`
implementation,
instead of the :class:`.NullPool` pool used by pysqlite.  As always, the pool
implementation is entirely configurable using the
:paramref:`.create_engine.poolclass` parameter; the :class:`.StaticPool` may
be more feasible for single-threaded use, or :class:`.NullPool` may be used
to prevent unencrypted connections from being held open for long periods of
time, at the expense of slower startup time for new connections.


"""
from __future__ import absolute_import
from .pysqlite import SQLiteDialect_pysqlite
from ...engine import url as _url
from ... import pool


class SQLiteDialect_pysqlcipher3(SQLiteDialect_pysqlite):
    driver = 'pysqlcipher3'

    pragmas = ('kdf_iter', 'cipher', 'cipher_page_size', 'cipher_use_hmac')

    @classmethod
    def dbapi(cls):
        try:
            from pysqlcipher3 import dbapi2 as sqlcipher
        except ImportError as e:
            try:
                from pysqlcipher33 import dbapi2 as sqlcipher
            except ImportError:
                raise e
        return sqlcipher

    @classmethod
    def get_pool_class(cls, url):
        return pool.SingletonThreadPool

    def connect(self, *cargs, **cparams):
        passphrase = cparams.pop('passphrase', '')

        pragmas = dict(
            (key, cparams.pop(key, None)) for key in
            self.pragmas
        )

        conn = super(SQLiteDialect_pysqlcipher3, self).\
            connect(*cargs, **cparams)
        conn.execute('pragma key="%s"' % passphrase)
        for prag, value in pragmas.items():
            if value is not None:
                conn.execute('pragma %s="%s"' % (prag, value))

        return conn

    def create_connect_args(self, url):
        super_url = _url.URL(
            url.drivername, username=url.username,
            host=url.host, database=url.database, query=url.query)
        c_args, opts = super(SQLiteDialect_pysqlcipher3, self).\
            create_connect_args(super_url)
        opts['passphrase'] = url.password
        return c_args, opts

dialect = SQLiteDialect_pysqlcipher3
