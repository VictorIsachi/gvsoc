source sourceme.sh
make dramsys_preparation
pip3 install -r core/requirements.txt --user
pip3 install -r gapy/requirements.txt --user
pip3 install dataclasses --user
make config
make TARGETS=pulp.chips.flex_cluster.flex_cluster all
make clean_sw && make sw