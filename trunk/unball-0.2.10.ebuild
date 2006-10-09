
DESCRIPTION="The only extraction wrapper you should ever need"
HOMEPAGE="http://www.ssokolow.com/MyPrograms/Gentoo"
SRC_URI=""

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~alpha ~amd64 ~hppa ~mips ~ppc ~ppc64 ~sparc x86"
IUSE="usedeps"

# Note: In some cases, app-arch/macutil will suffice in place of app-arch/stuffit, but not all.
# Note: app-arch/sharutils, app-arch/macutil, and media-video/mkvtoolnix could replace uudeview if there were
#	also an xxdecode command in the Portage tree.
# TODO: Add support for app-arch/unmakeself
# Tools not in the portage tree: paq6, sfarkxtc, and unace (2.x)

RDEPEND="app-shells/bash
	usedeps? (
		app-arch/alien
		app-arch/arc
		|| ( app-arch/unarj app-arch/arj )
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
		app-arch/unace
		app-arch/unadf
		|| ( app-arch/undms app-arch/xdms )
		app-arch/unlzx
		|| ( app-arch/unrar app-arch/unrar-gpl app-arch/rar )
		app-arch/unshield
		app-arch/unzip
		app-arch/xar
		app-arch/zoo
		net-news/uudeview
		|| ( net-news/yencode net-news/yydecode )
	)"

DEPEND="${RDEPEND}
        sys-apps/help2man"

src_install() { DESTDIR="${D}" ./install.sh; }
src_test()    { ./run_test.py; }
