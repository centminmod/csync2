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

BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  bison
BuildRequires:  flex
BuildRequires:  gnutls-devel
BuildRequires:  librsync-devel
BuildRequires:  hostname
# openssl required at build time due to rpmlint checks which run postinstall script which uses openssl
BuildRequires:  openssl
BuildRequires:  pkgconfig
BuildRequires:  sqlite-devel
Requires:       sqlite-libs
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
Requires:       openssl
Requires:       sqlite
Requires:       sqlite-libs
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
%if 0%{?suse_version} >= 1210 || 0%{?rhel} >= 7
BuildRequires:  systemd-rpm-macros
%endif

%pre
systemctl preset csync2.socket >/dev/null 2>&1 || :

%post
if ! grep -q "^csync2" %{_sysconfdir}/services ; then
     echo "csync2          30865/tcp" >>%{_sysconfdir}/services
fi
systemctl daemon-reload >/dev/null 2>&1 || :

%files
%doc %{_docdir}/csync2/AUTHORS.adoc

%doc %{_docdir}/csync2/COPYING

%doc %{_docdir}/csync2/ChangeLog

%doc %{_docdir}/csync2/README.adoc

%doc %{_docdir}/csync2/AUTHORS

%doc %{_docdir}/csync2/README
%{_unitdir}/csync2.socket
%doc %{_docdir}/csync2/*
%defattr(-,root,root)
%{_sbindir}/csync2
%{_sbindir}/csync2-compare
%{_var}/lib/csync2
%doc %{_mandir}/man1/csync2.1.gz
%doc %{_docdir}/csync2/csync2.adoc
%doc %{_docdir}/csync2/csync2-quickstart.adoc
%doc %{_docdir}/csync2/ChangeLog
%doc %{_docdir}/csync2/README
%doc %{_docdir}/csync2/AUTHORS
%config(noreplace) %{_sysconfdir}/csync2/csync2.cfg

%changelog
* Fri Sep 18 2020 Lars Ellenberg <lars.ellenberg@linbit.com> - 2.1-1
- New upstream release

* Tue Jan 27 2015 Lars Ellenberg <lars.ellenberg@linbit.com> - 2.0-1
- New upstream release