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
export CC=gcc
export CPPFLAGS="-I/usr/include -I%{_builddir}/%{name}-master/librsync-install/include"
export RPM_OPT_FLAGS="$RPM_OPT_FLAGS -Wno-format-truncation -Wno-misleading-indentation"
export CFLAGS="$RPM_OPT_FLAGS -flto"
%if 0%{?rhel}
export CFLAGS="$CFLAGS -I/usr/kerberos/include"
%endif
export LDFLAGS="$RPM_OPT_FLAGS -flto -L%{_builddir}/%{name}-master -L%{_builddir}/%{name}-master/librsync-install/lib64 -L%{_builddir}/%{name}-master/librsync-install/lib"
export LIBS="-lprivatersync"
export PKG_CONFIG_PATH="%{_builddir}/%{name}-master/librsync-install/lib/pkgconfig:$PKG_CONFIG_PATH"

if ! [ -f configure ]; then ./autogen.sh; fi
%configure --enable-systemd --enable-mysql --enable-postgres --disable-sqlite --enable-sqlite3 \
  --sysconfdir=%{_sysconfdir}/csync2 --docdir=%{_docdir}/%{name} \
  --with-librsync-source=$(pwd)/librsync-%{librsync_version}.tar.gz

make %{?_smp_mflags}

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