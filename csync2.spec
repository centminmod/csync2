#
# spec file for package csync2
#
# Copyright 2004-2020 LINBIT, Vienna, Austria
#
# SPDX-License-Identifier: GPL-2.0-or-later

Summary:        Cluster synchronization tool
License:        GPL-2.0-or-later
Group:          Productivity/Clustering/HA

Name:           csync2
Version: 2.1
Release: 1%{?dist}
URL:            https://github.com/centminmod/csync2#readme
Source0: %{name}-%{version}.tar.gz

%define librsync_version 2.3.4
%define librsync_url https://github.com/librsync/librsync/releases/download/v%{librsync_version}/librsync-%{librsync_version}.tar.gz

BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  bison
BuildRequires:  curl
BuildRequires:  flex
BuildRequires:  gnutls-devel
BuildRequires:  librsync-devel
BuildRequires:  hostname
# openssl required at build time due to rpmlint checks which run postinstall script which uses openssl
BuildRequires:  openssl
BuildRequires:  pkgconfig
BuildRequires:  cmake
BuildRequires:  sqlite-devel
Requires:       sqlite-libs
Requires:       openssl
Requires:       sqlite
Requires:       sqlite-libs
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
%if 0%{?suse_version} >= 1210 || 0%{?rhel} >= 7
BuildRequires:  systemd-rpm-macros
%endif

BuildRoot:      %{_tmppath}/%{name}-%{version}-build

%description
Csync2 is a cluster synchronization tool. It can be used to keep files on
multiple hosts in a cluster in sync. Csync2 can handle complex setups with
much more than just 2 hosts, handle file deletions and can detect conflicts.
It is expedient for HA-clusters, HPC-clusters, COWs and server farms.

%prep
%setup -n csync2-master
curl -L %{librsync_url} -o librsync-%{librsync_version}.tar.gz
%{?suse_update_config:%{suse_update_config}}

%build
# Function to display config.log
display_config_log() {
    echo "Contents of config.log:"
    cat config.log
}

# Set up environment variables
export CC=gcc
export CPPFLAGS="-I/usr/include -I%{_builddir}/%{name}-master/librsync-install/include"
export CFLAGS="-O2 -g -pipe -Wall -fexceptions -fstack-protector-strong -fasynchronous-unwind-tables"
export LDFLAGS="-L%{_builddir}/%{name}-master -L%{_builddir}/%{name}-master/librsync-install/lib64 -L%{_builddir}/%{name}-master/librsync-install/lib"
export LIBS="-lprivatersync"
export PKG_CONFIG_PATH="%{_builddir}/%{name}-master/librsync-install/lib/pkgconfig:$PKG_CONFIG_PATH"

# Debug: Print all environment variables
env

# Test if the compiler works
echo "Testing basic compiler functionality:"
echo "int main() { return 0; }" > test.c
$CC $CFLAGS test.c -o test
if [ $? -ne 0 ]; then
    echo "Error: Unable to compile a simple C program. Check your compiler installation."
    gcc -v
    display_config_log
    exit 1
fi

# Debug: Test each flag individually
echo "Testing individual CFLAGS:"
for flag in $CFLAGS; do
    echo "Testing flag: $flag"
    if ! $CC $flag test.c -o test; then
        echo "Problematic flag: $flag"
    fi
done

# Check librsync source file
librsync_source_file=$(pwd)/librsync-%{librsync_version}.tar.gz
if [ ! -f "$librsync_source_file" ]; then
    echo "Error: librsync source file not found: $librsync_source_file"
    ls -l
    exit 1
fi

# Check for required libraries and headers
for lib in libsqlite3 libmysqlclient libpq libgnutls; do
    if ! pkg-config --exists $lib; then
        echo "Error: $lib not found"
        #exit 1
    fi
done

for header in sqlite3.h mysql.h libpq-fe.h gnutls/gnutls.h; do
    if [ ! -f /usr/include/$header ]; then
        echo "Error: $header not found"
        #exit 1
    fi
done

if ! [ -f configure ]; then 
    ./autogen.sh || { echo "autogen.sh failed"; display_config_log; exit 1; }
fi

# Run configure with verbose output
%configure --enable-systemd --enable-mysql --enable-postgres --disable-sqlite --enable-sqlite3 \
  --sysconfdir=%{_sysconfdir}/csync2 --docdir=%{_docdir}/%{name} \
  --with-librsync-source=$librsync_source_file \
  --verbose || {
    echo "configure failed. Contents of config.log:";
    cat config.log;
    exit 1;
  }

# If the above fails, try without custom librsync
# Uncomment the following lines if needed:
# if [ $? -ne 0 ]; then
#     echo "Trying configure without custom librsync..."
#     %configure --enable-systemd --enable-mysql --enable-postgres --disable-sqlite --enable-sqlite3 \
#       --sysconfdir=%{_sysconfdir}/csync2 --docdir=%{_docdir}/%{name} \
#       --verbose || {
#         echo "configure failed again. Contents of config.log:";
#         cat config.log;
#         exit 1;
#       }
# fi

make %{?_smp_mflags} || { echo "make failed"; display_config_log; exit 1; }

%preun
systemctl --no-reload disable csync2.socket >/dev/null 2>&1 || :
systemctl stop csync2.socket >/dev/null 2>&1 || :
systemctl --no-reload disable csync2@.service >/dev/null 2>&1 || :
systemctl stop csync2@.service >/dev/null 2>&1 || :

%postun 
systemctl daemon-reload >/dev/null 2>&1 || :

%install
mkdir -p %{buildroot}%{_localstatedir}/lib/csync2
mkdir -p %{buildroot}%{_docdir}/csync2
mkdir -p %{buildroot}%{_sysconfdir}/csync2
install -D -m 644 csync2.cfg %{buildroot}%{_sysconfdir}/csync2/csync2.cfg
install -D -m 644 csync2.socket %{buildroot}%{_unitdir}/csync2.socket
install -D -m 644 csync2@.service %{buildroot}%{_unitdir}/csync2@.service
install -m 644 AUTHORS %{buildroot}%{_docdir}/csync2/AUTHORS
install -m 644 AUTHORS.adoc %{buildroot}%{_docdir}/csync2/AUTHORS.adoc
install -m 644 README %{buildroot}%{_docdir}/csync2/README
install -m 644 README.adoc %{buildroot}%{_docdir}/csync2/README.adoc

%make_install
mkdir -p %{buildroot}%{_localstatedir}/lib/csync2
install -m 644 doc/csync2.adoc %{buildroot}%{_docdir}/csync2/csync2.adoc
install -m 644 doc/csync2-quickstart.adoc %{buildroot}%{_docdir}/csync2/csync2-quickstart.adoc

%clean
[ "$RPM_BUILD_ROOT" != "/" ] && [ -d $RPM_BUILD_ROOT ] && rm -rf $RPM_BUILD_ROOT
make clean

#%pre
#systemctl preset csync2.socket >/dev/null 2>&1 || :

%post
systemctl daemon-reload >/dev/null 2>&1 || :
systemctl preset csync2.socket >/dev/null 2>&1 || :
systemctl preset csync2@.service >/dev/null 2>&1 || :
if ! grep -q "^csync2" %{_sysconfdir}/services ; then
    echo "csync2          30865/tcp" >>%{_sysconfdir}/services
fi

%files
%config(noreplace) %{_sysconfdir}/csync2/csync2.cfg
%defattr(-,root,root)
%doc %{_docdir}/csync2/*
%doc %{_docdir}/csync2/AUTHORS
%doc %{_docdir}/csync2/AUTHORS.adoc
%doc %{_docdir}/csync2/ChangeLog
%doc %{_docdir}/csync2/COPYING
%doc %{_docdir}/csync2/csync2-quickstart.adoc
%doc %{_docdir}/csync2/csync2.adoc
%doc %{_docdir}/csync2/README
%doc %{_docdir}/csync2/README.adoc
%doc %{_mandir}/man1/csync2.1.gz
%{_sbindir}/csync2
%{_sbindir}/csync2-compare
%{_unitdir}/csync2.socket
%{_unitdir}/csync2@.service
%{_var}/lib/csync2

%changelog
* Fri Sep 18 2020 Lars Ellenberg <lars.ellenberg@linbit.com> - 2.1-1
- New upstream release

* Tue Jan 27 2015 Lars Ellenberg <lars.ellenberg@linbit.com> - 2.0-1
- New upstream release