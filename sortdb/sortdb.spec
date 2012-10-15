%define debug_package %{nil}
Name:           sortdb
Version:        xn_1.0
Release:        1
Summary:        sortdb for simplehttp
Group:          Tool
License:        MIT
URL:            https://github.com/ning/simplehttp/tree/xn-1.0
Source:         ning-simplehttp-xn-1.0-0-gd32a797.tar.gz
Requires:       libevent
BuildRequires:  libevent-devel

%description
sortdb static csv database over http

%prep
%setup -qn ning-simplehttp-e688783

%build
cd simplehttp
make
cd ../sortdb
make

%install
mkdir -p $RPM_BUILD_ROOT/usr/local/bin
cp sortdb/sortdb $RPM_BUILD_ROOT/usr/local/bin

%clean
rm -rf $RPM_BUILD_ROOT

%files
/usr/local/bin/sortdb

#end
