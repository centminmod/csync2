# csync2 - cluster synchronization tool, 2nd generation
# Copyright (C) 2004 - 2015 LINBIT Information Technologies GmbH
# http://www.linbit.com; see also AUTHORS
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#

sbin_PROGRAMS = csync2
sbin_SCRIPTS = csync2-compare
man_MANS = csync2.1

csync2_SOURCES = action.c cfgfile_parser.y cfgfile_scanner.l check.c	\
                 checktxt.c csync2.c daemon.c db.c error.c getrealfn.c	\
                 groups.c rsync.c update.c urlencode.c conn.c prefixsubst.c \
		 db_api.c db_sqlite.c db_sqlite2.c db_mysql.c db_postgres.c \
		 csync2.h db_api.h db_mysql.h db_postgres.h db_sqlite.h db_sqlite2.h dl.h \
		 csync2-compare \
		 csync2.1 \
		 csync2.spec

EXTRA_DIST = csync2.cfg csync2.xinetd

INSTALL_TARGETS = install-config-files

if USE_SYSTEMD
EXTRA_DIST += csync2.socket csync2@.service
INSTALL_TARGETS += install-systemd-files
endif

AM_YFLAGS = -d
BUILT_SOURCES = cfgfile_parser.h
LIBS += -ldl
CLEANFILES = cfgfile_parser.c cfgfile_parser.h cfgfile_scanner.c	\
             private_librsync private_libsqlite config.log

DISTCLEANFILES = config.status config.h .deps/*.Po stamp-h1 Makefile Makefile.in configure

docfiles = ChangeLog README.md AUTHORS.adoc doc/csync2.adoc COPYING

doc_DATA = $(docfiles)
dist_doc_DATA = $(docfiles)

dist-clean-local:
	rm -rf autom4te.cache

AM_CFLAGS=$(LIBGNUTLS_CFLAGS) -Wall
AM_LDFLAGS=$(LIBGNUTLS_LIBS)
LIBS += $(LIBGNUTLS_LIBS)

if PRIVATE_LIBRSYNC
  BUILT_SOURCES += private_librsync
  AM_CFLAGS += -I$(shell test -f librsync.dir && cat librsync.dir || echo ==librsync==)
  AM_LDFLAGS += -L$(shell test -f librsync.dir && cat librsync.dir || echo ==librsync==)
  LIBS += -lprivatersync
endif

AM_CPPFLAGS  = -D'DBDIR="$(localstatedir)/lib/csync2"'
AM_CPPFLAGS += -D'ETCDIR="$(sysconfdir)"'

install-config-files:
	$(mkinstalldirs) $(DESTDIR)$(sysconfdir)
	$(mkinstalldirs) $(DESTDIR)$(localstatedir)/lib/csync2
	test -e $(DESTDIR)$(sysconfdir)/csync2.cfg || \
		$(INSTALL_DATA) $(srcdir)/csync2.cfg $(DESTDIR)$(sysconfdir)/csync2.cfg

install-systemd-files:
	$(MKDIR_P) $(DESTDIR)$(SYSTEMD_UNITDIR)
	$(INSTALL_DATA) csync2.socket $(DESTDIR)$(SYSTEMD_UNITDIR)/csync2.socket
	$(INSTALL_DATA) csync2@.service $(DESTDIR)$(SYSTEMD_UNITDIR)/csync2@.service

install-data-local: $(INSTALL_TARGETS)

cert:
	$(mkinstalldirs) $(DESTDIR)$(sysconfdir)
	openssl genrsa -out $(DESTDIR)$(sysconfdir)/csync2_ssl_key.pem 1024
	yes '' | openssl req -new -key $(DESTDIR)$(sysconfdir)/csync2_ssl_key.pem \
		-out $(DESTDIR)$(sysconfdir)/csync2_ssl_cert.csr
	openssl x509 -req -days 600 -in $(DESTDIR)$(sysconfdir)/csync2_ssl_cert.csr \
		-signkey $(DESTDIR)$(sysconfdir)/csync2_ssl_key.pem \
		-out $(DESTDIR)$(sysconfdir)/csync2_ssl_cert.pem
	rm $(DESTDIR)$(sysconfdir)/csync2_ssl_cert.csr


## hack for building private librsync and private libsqlite ##

private_librsync:
	@if [ ! -f "$(librsync_source_file)" ]; then \
		echo "Error: librsync source file not found: $(librsync_source_file)"; \
		exit 1; \
	fi
	mkdir -p librsync_build
	tar xvzf $(librsync_source_file) -C librsync_build --strip-components=1
	cd librsync_build && \
		cmake . \
		-DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_C_FLAGS="$(CFLAGS) -flto" \
		-DCMAKE_EXE_LINKER_FLAGS="$(LDFLAGS) -flto" \
		-DCMAKE_INSTALL_PREFIX=$(abs_builddir)/librsync-install \
		-DBUILD_SHARED_LIBS=OFF \
		-DENABLE_COMPRESSION=ON \
		-DENABLE_TRACE=OFF
	make -C librsync_build
	make -C librsync_build install
	if [ -f "$(abs_builddir)/librsync-install/lib64/librsync.a" ]; then \
		cp $(abs_builddir)/librsync-install/lib64/librsync.a $(abs_builddir)/libprivatersync.a; \
	elif [ -f "$(abs_builddir)/librsync-install/lib/librsync.a" ]; then \
		cp $(abs_builddir)/librsync-install/lib/librsync.a $(abs_builddir)/libprivatersync.a; \
	else \
		echo "Error: librsync.a not found in expected locations"; \
		exit 1; \
	fi
	touch private_librsync

private_libsqlite:
	tar xvzf $(libsqlite_source_file) | cut -f1 -d/ | sed '1 p; d;' > libsqlite.dir
	test -s libsqlite.dir && cd $$( cat libsqlite.dir ) && ./configure --enable-static --disable-shared
	make -C $$( cat libsqlite.dir )
	cp $$( cat libsqlite.dir )/.libs/libsqlite.a $$( cat libsqlite.dir )/libprivatesqlite.a
	touch private_libsqlite

