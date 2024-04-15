CMAKE_FLAGS ?= -j 6
CMAKE ?= cmake

TARGETS ?= rv32;rv64

export PATH:=$(CURDIR)/gapy/bin:$(PATH)

all: checkout build

checkout:
	git submodule update --recursive --init

.PHONY: build

build:
	# Change directory to curdir to avoid issue with symbolic links
	cd $(CURDIR) && $(CMAKE) -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo \
		-DCMAKE_INSTALL_PREFIX=install \
		-DGVSOC_MODULES="$(CURDIR)/core/models;$(CURDIR)/pulp;$(MODULES)" \
		-DGVSOC_TARGETS="${TARGETS}" \
		-DCMAKE_SKIP_INSTALL_RPATH=false

	cd $(CURDIR) && $(CMAKE) --build build $(CMAKE_FLAGS)
	cd $(CURDIR) && $(CMAKE) --install build


clean:
	rm -rf build install



######################################################################
## 				Make Targets for DRAMSys Integration 				##
######################################################################

SYSTEMC_VERSION := 2.3.3
SYSTEMC_GIT_URL := https://github.com/accellera-official/systemc.git
SYSTEMC_INSTALL_DIR := $(PWD)/third_party/systemc_install

redmule_perparation:
	if cd pulp && git apply --check ../add_dramsyslib_patches/gvsoc_pulp.patch; then \
		git apply ../add_dramsyslib_patches/gvsoc_pulp.patch;\
	fi
	cp -rfv add_dramsyslib_patches/redmule pulp/pulp/


build-systemc: third_party/systemc_install/lib64/libsystemc.so

third_party/systemc_install/lib64/libsystemc.so:
	mkdir -p $(SYSTEMC_INSTALL_DIR)
	cd third_party && \
	git clone $(SYSTEMC_GIT_URL) && \
	cd systemc && git fetch --tags && git checkout $(SYSTEMC_VERSION) && \
	mkdir build && cd build && \
	$(CMAKE) -DCMAKE_CXX_STANDARD=17 -DCMAKE_INSTALL_PREFIX=$(SYSTEMC_INSTALL_DIR) -DCMAKE_INSTALL_LIBDIR=lib64 .. && \
	make && make install

build-dramsys: build-systemc third_party/DRAMSys/libDRAMSys_Simulator.so

third_party/DRAMSys/libDRAMSys_Simulator.so:
	mkdir -p third_party/DRAMSys
	cp add_dramsyslib_patches/libDRAMSys_Simulator.so third_party/DRAMSys/
	echo "Check Library Functionality"
	cd add_dramsyslib_patches/build_dynlib_from_github_dramsys5/dynamic_load/ && \
	gcc main.c -ldl
	@if add_dramsyslib_patches/build_dynlib_from_github_dramsys5/dynamic_load/a.out ; then \
        echo "Test libaray succeeded"; \
		rm add_dramsyslib_patches/build_dynlib_from_github_dramsys5/dynamic_load/a.out; \
		rm DRAMSysRecordable* ; \
    else \
		rm add_dramsyslib_patches/build_dynlib_from_github_dramsys5/dynamic_load/a.out; \
		rm third_party/DRAMSys/libDRAMSys_Simulator.so; \
		echo "Test libaray failed, We need to rebuild the library, tasks around 40 min"; \
		echo -n "Do you want to proceed? (y/n) "; \
		read -t 30 -r user_input; \
		if [ "$$user_input" = "n" ]; then echo "oops, I see, your time is precious, see you next time"; exit 1; fi; \
		echo "Go Go Go!" ; \
		cd add_dramsyslib_patches/build_dynlib_from_github_dramsys5 && make all; \
		cp DRAMSys/build/lib/libDRAMSys_Simulator.so ../../third_party/DRAMSys/ ; \
		make clean; \
    fi

build-configs: core/models/memory/dramsys_configs

core/models/memory/dramsys_configs:
	cp -rf add_dramsyslib_patches/dramsys_configs core/models/memory/

dramsys_preparation: build-systemc build-dramsys build-configs

occamy_pdk_preparation: third_party/occamy

third_party/occamy:
	cd third_party; git clone git@github.com:pulp-platform/occamy.git; \
	cd occamy; git reset --hard ed0b98162fae196faff96a972f861a0aa4593227; \
	git submodule update --init --recursive; bender vendor init; \
	cd target/sim; make DEBUG=ON sw

snitch_pdk_preparation: third_party/snitch_cluster

third_party/snitch_cluster:
	cd third_party; git clone third_party/snitch_cluster; \
	cd snitch_cluster; git submodule update --init --recursive; source iis-setup.sh; \
	cp -rf ../../add_dramsyslib_patches/snitch_app/ target/snitch_cluster/sw/apps/redmule; \
	cd target/snitch_cluster; sed -i '42aAPPS += sw/apps/redmule' sw.mk; make DEBUG=ON sw;

clean_dramsys_preparation:
	rm -rf third_party
