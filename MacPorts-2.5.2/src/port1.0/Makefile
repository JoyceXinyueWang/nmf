srcdir = .


include ../../Mk/macports.autoconf.mk

INSTALLDIR=	${DESTDIR}${TCL_PACKAGE_PATH}/port1.0

SRCS_AUTOCONF= port_autoconf.tcl
SRCS=	port.tcl portchecksum.tcl portconfigure.tcl portextract.tcl	    \
	portfetch.tcl portmain.tcl portbuild.tcl portpatch.tcl portutil.tcl \
	portinstall.tcl portuninstall.tcl portdepends.tcl portdestroot.tcl \
	portlint.tcl portclean.tcl porttest.tcl portactivate.tcl \
	portdeactivate.tcl portstartupitem.tcl porttrace.tcl portlivecheck.tcl \
	portdistcheck.tcl portmirror.tcl portload.tcl portunload.tcl portreload.tcl \
	portdistfiles.tcl fetch_common.tcl portsandbox.tcl

include $(srcdir)/../../Mk/macports.subdir.mk

.PHONY: test

all:: pkgIndex.tcl

pkgIndex.tcl: $(SRCS) $(SRCS_AUTOCONF)
	$(SILENT) ../pkg_mkindex.sh . || ( rm -rf $@ && exit 1 )

clean::
	rm -f pkgIndex.tcl

distclean:: clean
	rm -f port_autoconf.tcl port_test_autoconf.tcl
	rm -f Makefile

install:: all
	$(INSTALL) -d -o "${DSTUSR}" -g "${DSTGRP}" -m "${DSTMODE}" "${INSTALLDIR}"
	$(SILENT)set -x; for file in ${SRCS}; do \
		$(INSTALL) -o "${DSTUSR}" -g "${DSTGRP}" -m 444 "$(srcdir)/$$file" "${INSTALLDIR}"; \
	done
	$(SILENT)set -x; for file in ${SRCS_AUTOCONF}; do \
		$(INSTALL) -o "${DSTUSR}" -g "${DSTGRP}" -m 444 "$$file" "${INSTALLDIR}"; \
	done
	$(INSTALL) -o "${DSTUSR}" -g "${DSTGRP}" -m 444 pkgIndex.tcl "${INSTALLDIR}"

test::
	$(TCLSH) $(srcdir)/../tests/test.tcl -nocolor
