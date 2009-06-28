# Copyright 2009 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

# Note: app-arch/zoo doesn't work properly on x86_64. Try contrib/unzoo.c
# Note: app-arch/arj is GPLed while app-arch/unarj is freeware, older, and lacking features.

DESCRIPTION="The only extraction wrapper you should ever need"
HOMEPAGE="https://launchpad.net/unball"
SRC_URI="http://launchpad.net/unball/0.2-legacy/${PV}/+download/${P}.tbz2"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~alpha amd64 ~hppa ~mips ~ppc ~ppc64 ~sparc ~x86"
IUSE="usedeps"

RDEPEND="app-shells/bash
	usedeps? (
		app-arch/alien
		app-arch/arc
		app-arch/arj
		app-arch/bzip2
		app-arch/cabextract
		app-arch/cpio
		app-arch/gzip
		app-arch/lha
		app-arch/lzop
		app-arch/mscompress
		|| ( app-arch/rpm2cpio app-arch/rpm2targz )
		app-arch/rzip
		app-arch/stuffit
		app-arch/tar
		|| ( app-arch/unace app-arch/unace-bin )
		app-arch/unadf
		|| ( app-arch/undms app-arch/xdms )
		app-arch/unlzx
		|| ( app-arch/unrar app-arch/unrar-gpl app-arch/rar )
		app-arch/unshield
		app-arch/unzip
		app-arch/xar
		app-arch/zoo
		games-util/biounzip
		games-util/umodpack
		games-util/uz2unpack
		games-util/dzip
		net-news/uudeview
		|| ( net-news/yencode net-news/yydecode )
	)"

DEPEND="${RDEPEND}
        sys-apps/help2man"

src_install() {
	export NO_CHOWN=1
	DESTDIR="${D}" ./install.sh;

	which sfarkxtc > /dev/null || ewarn "Your system lacks sfarkxtc but unball requires it for unpacking SFArk-compressed SoundFonts."
}

src_test()    { ./run_test.py; }
