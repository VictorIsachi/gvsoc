#
# Copyright (C) 2020 ETH Zurich and University of Bologna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import gvsoc.runner
import pulp.snitch.snitch_core as iss
import memory.memory as memory
import interco.router as router
import gvsoc.systree
from pulp.chips.flex_cluster.cluster_registers import ClusterRegisters
from pulp.chips.flex_cluster.light_redmule import LightRedmule
from pulp.chips.flex_cluster.light_mtxtran import LightMtxTran
from pulp.chips.flex_cluster.hwpe_interleaver import HWPEInterleaver
from pulp.snitch.snitch_cluster.dma_interleaver import DmaInterleaver
from pulp.chips.flex_cluster.flex_sync_mem import FlexSyncMem
from pulp.snitch.zero_mem import ZeroMem
from elftools.elf.elffile import *
from pulp.idma.snitch_dma import SnitchDma
from pulp.cluster.l1_interleaver import L1_interleaver
import gvsoc.runner
import math
from pulp.snitch.sequencer import Sequencer
import utils.loader.loader


GAPY_TARGET = True



class Area:

    def __init__(self, base, size):
        self.base = base
        self.size = size



class ClusterArch:
    def __init__(self,  nb_core_per_cluster, base, cluster_id, tcdm_size,
                        stack_base,         stack_size,
                        reg_base,           reg_size,
                        sync_base,          sync_size,          sync_special_mem,
                        insn_base,          insn_size,
                        nb_tcdm_banks,      tcdm_bank_width,
                        redmule_ce_height,  redmule_ce_width,   redmule_ce_pipe,
                        redmule_elem_size,  redmule_queue_depth,
                        redmule_reg_base,   redmule_reg_size,
                        mtxtran_reg_base,   mtxtran_reg_size,
                        idma_outstand_txn,  idma_outstand_burst,
                        num_cluster_x,      num_cluster_y,
                        data_bandwidth,     num_redmule,
                        auto_fetch=False,   boot_addr=0x8000_0650):

        self.nb_core                = nb_core_per_cluster
        self.base                   = base
        self.cluster_id             = cluster_id
        self.boot_addr              = boot_addr
        self.auto_fetch             = auto_fetch
        self.barrier_irq            = 19
        self.tcdm                   = ClusterArch.Tcdm(base, self.nb_core, tcdm_size, nb_tcdm_banks, tcdm_bank_width, sync_size, sync_special_mem)
        self.stack_area             = Area(stack_base, stack_size)
        self.sync_area              = Area(sync_base, sync_size)
        self.reg_area               = Area(reg_base, reg_size)
        self.insn_area              = Area(insn_base, insn_size)

        #RedMule
        self.num_redmule            = num_redmule
        self.redmule_ce_height      = redmule_ce_height
        self.redmule_ce_width       = redmule_ce_width
        self.redmule_ce_pipe        = redmule_ce_pipe
        self.redmule_elem_size      = redmule_elem_size
        self.redmule_queue_depth    = redmule_queue_depth
        self.redmule_area           = Area(redmule_reg_base, redmule_reg_size)

        #MtxTran
        self.mtxtran_area           = Area(mtxtran_reg_base, mtxtran_reg_size)

        #IDMA
        self.idma_outstand_txn      = idma_outstand_txn
        self.idma_outstand_burst    = idma_outstand_burst
        self.data_bandwidth         = data_bandwidth

        #Global Information
        self.num_cluster_x          = num_cluster_x
        self.num_cluster_y          = num_cluster_y

    class Tcdm:
        def __init__(self, base, nb_masters, tcdm_size, nb_tcdm_banks, tcdm_bank_width, sync_size, sync_special_mem):
            self.area = Area( base, tcdm_size)
            self.nb_tcdm_banks = nb_tcdm_banks
            self.bank_width = tcdm_bank_width
            self.bank_size = self.area.size / self.nb_tcdm_banks
            self.nb_masters = nb_masters
            self.sync_size = sync_size
            self.sync_special_mem = sync_special_mem


class ClusterTcdm(gvsoc.systree.Component):

    def __init__(self, parent, name, arch):
        super().__init__(parent, name)

        banks = []
        nb_banks = arch.nb_tcdm_banks
        for i in range(0, nb_banks):
            banks.append(memory.Memory(self, f'bank_{i}', size=arch.bank_size, atomics=True, width_log2=int(math.log2(arch.bank_width))))

        interleaver = L1_interleaver(self, 'interleaver', nb_slaves=nb_banks,
            nb_masters=arch.nb_masters, interleaving_bits=int(math.log2(arch.bank_width)))

        dma_interleaver = DmaInterleaver(self, 'dma_interleaver', arch.nb_masters,
            nb_banks, arch.bank_width)

        bus_interleaver = DmaInterleaver(self, 'bus_interleaver', arch.nb_masters,
            nb_banks, arch.bank_width)

        hwpe_interleaver = HWPEInterleaver(self, 'hwpe_interleaver', arch.nb_masters,
            nb_banks, arch.bank_width)

        tcdm_sync_mem = FlexSyncMem(self, 'sync_mem', size=arch.sync_size, special_mem_base=arch.sync_special_mem)

        for i in range(0, nb_banks):
            self.bind(interleaver, 'out_%d' % i, banks[i], 'input')
            self.bind(dma_interleaver, 'out_%d' % i, banks[i], 'input')
            self.bind(bus_interleaver, 'out_%d' % i, banks[i], 'input')
            self.bind(hwpe_interleaver, 'out_%d' % i, banks[i], 'input')

        for i in range(0, arch.nb_masters):
            self.bind(self, f'in_{i}', interleaver, f'in_{i}')
            self.bind(self, f'dma_input', dma_interleaver, f'input')
            self.bind(self, f'bus_input', bus_interleaver, f'input')
            self.bind(self, f'hwpe_input', hwpe_interleaver, f'input')

        self.bind(self, f'sync_input', tcdm_sync_mem, f'input')

    def i_INPUT(self, port: int) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, f'in_{port}', signature='io')

    def i_DMA_INPUT(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, f'dma_input', signature='io')

    def i_BUS_INPUT(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, f'bus_input', signature='io')

    def i_HWPE_INPUT(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, f'hwpe_input', signature='io')

    def i_SYNC_INPUT(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, f'sync_input', signature='io')



class ClusterUnit(gvsoc.systree.Component):

    def __init__(self, parent, name, arch, binary, entry=0, auto_fetch=True):
        super().__init__(parent, name)

        #
        # Components
        #

        #Loader
        loader = utils.loader.loader.ElfLoader(self, 'loader', binary=binary)

        #Instruction memory
        instr_mem = memory.Memory(self, 'instr_mem', size=arch.insn_area.size, atomics=True)

        #Instruction router
        instr_router = router.Router(self, 'instr_router', bandwidth=8)

        # Main router
        wide_axi_goto_tcdm = router.Router(self, 'wide_axi_goto_tcdm')
        wide_axi_from_idma = router.Router(self, 'wide_axi_from_idma')
        narrow_axi = router.Router(self, 'narrow_axi', bandwidth=8)

        # L1 Memory
        tcdm = ClusterTcdm(self, 'tcdm', arch.tcdm)

        # Cores
        cores = []
        fp_cores = []
        cores_ico = []
        xfrep = True
        if xfrep:
            fpu_sequencers = []
        for core_id in range(0, arch.nb_core):
            cores.append(iss.Snitch(self, f'pe{core_id}', isa='rv32imfdvca',
                fetch_enable=arch.auto_fetch, boot_addr=arch.boot_addr,
                core_id=core_id, htif=False))

            fp_cores.append(iss.Snitch_fp_ss(self, f'fp_ss{core_id}', isa='rv32imfdvca',
                fetch_enable=arch.auto_fetch, boot_addr=arch.boot_addr,
                core_id=core_id, htif=False))
            if xfrep:
                fpu_sequencers.append(Sequencer(self, f'fpu_sequencer{core_id}', latency=0))

            cores_ico.append(router.Router(self, f'pe{core_id}_ico', bandwidth=arch.tcdm.bank_width))

        # RedMule
        redmule_list = []
        for redmule_id in range(0, arch.num_redmule):
            redmule = LightRedmule(self, f'redmule_{redmule_id}',
                                        redmule_id          = redmule_id,
                                        tcdm_bank_width     = arch.tcdm.bank_width,
                                        tcdm_bank_number    = (arch.tcdm.nb_tcdm_banks / arch.num_redmule),
                                        elem_size           = arch.redmule_elem_size,
                                        ce_height           = arch.redmule_ce_height,
                                        ce_width            = arch.redmule_ce_width,
                                        ce_pipe             = arch.redmule_ce_pipe,
                                        queue_depth         = arch.redmule_queue_depth)
            redmule_list.append(redmule)
            pass

        # MtxTran
        mtxtran = LightMtxTran(self, f'mtxtran',
                                        tcdm_bank_width     = arch.tcdm.bank_width,
                                        tcdm_bank_number    = arch.tcdm.nb_tcdm_banks,
                                        elem_size           = arch.redmule_elem_size)

        # Cluster peripherals
        cluster_registers = ClusterRegisters(self, 'cluster_registers',
            num_cluster_x=arch.num_cluster_x, num_cluster_y=arch.num_cluster_y, nb_cores=arch.nb_core,
            boot_addr=entry, cluster_id=arch.cluster_id)

        # Cluster DMA
        idma = SnitchDma(self, 'idma', loc_base=arch.tcdm.area.base, loc_size=arch.tcdm.area.size,
            tcdm_width=(arch.tcdm.nb_tcdm_banks * arch.tcdm.bank_width), transfer_queue_size=arch.idma_outstand_txn, burst_queue_size=arch.idma_outstand_burst)

        idma2 = SnitchDma(self, 'idma2', loc_base=arch.tcdm.area.base, loc_size=arch.tcdm.area.size,
            tcdm_width=(arch.tcdm.nb_tcdm_banks * arch.tcdm.bank_width), transfer_queue_size=arch.idma_outstand_txn, burst_queue_size=arch.idma_outstand_burst)

        #stack memory
        stack_mem = memory.Memory(self, 'stack_mem', size=arch.stack_area.size)

        #synchronization router
        sync_router = router.Router(self, 'sync_router', bandwidth=4)

        #
        # Bindings
        #

        #Binary loader
        loader.o_OUT(instr_router.i_INPUT())
        loader.o_START(self.i_FETCHEN())

        #Instruction router
        instr_router.o_MAP(instr_mem.i_INPUT(), base=arch.insn_area.base, size=arch.insn_area.size, rm_base=True)

        # Narrow router for cores data accesses
        self.o_NARROW_INPUT(narrow_axi.i_INPUT())
        narrow_axi.o_MAP(self.i_NARROW_SOC())
        # TODO check on real HW where this should go. This probably go through wide axi to
        # have good bandwidth when transferring from one cluster to another
        narrow_axi.o_MAP(cores_ico[0].i_INPUT(), base=arch.tcdm.area.base, size=arch.tcdm.area.size, rm_base=False)

        #binding to stack memory
        narrow_axi.o_MAP(stack_mem.i_INPUT(), base=arch.stack_area.base, size=arch.stack_area.size, rm_base=True)

        #binding to cluster registers
        narrow_axi.o_MAP(cluster_registers.i_INPUT(), base=arch.reg_area.base, size=arch.reg_area.size, rm_base=True)

        #binding to redmule
        for redmule_id in range(0, arch.num_redmule):
            narrow_axi.o_MAP(redmule_list[redmule_id].i_INPUT(), base=arch.redmule_area.base+redmule_id*arch.redmule_area.size, size=arch.redmule_area.size, rm_base=True)
            pass

        #binding to mtxtran
        narrow_axi.o_MAP(mtxtran.i_INPUT(), base=arch.mtxtran_area.base, size=arch.mtxtran_area.size, rm_base=True)

        #binding back to instruction memory if access needs
        narrow_axi.o_MAP(instr_mem.i_INPUT(), base=arch.insn_area.base, size=arch.insn_area.size, rm_base=True)

        #binding to synchronization bus
        narrow_axi.o_MAP(sync_router.i_INPUT(), base=arch.sync_area.base, size=arch.sync_area.size, rm_base=False)
        sync_router.o_MAP(self.i_SYNC_OUTPUT())


        #RedMule to TCDM
        for redmule_id in range(0, arch.num_redmule):
            redmule_list[redmule_id].o_TCDM(tcdm.i_HWPE_INPUT())
            pass


        # Wire router for DMA and instruction caches
        self.o_WIDE_INPUT(wide_axi_goto_tcdm.i_INPUT())
        wide_axi_goto_tcdm.o_MAP(tcdm.i_BUS_INPUT())
        wide_axi_from_idma.o_MAP(self.i_WIDE_SOC())
        

        # iDMA connection
        cores[arch.nb_core-1].o_OFFLOAD(idma.i_OFFLOAD())
        idma.o_OFFLOAD_GRANT(cores[arch.nb_core-1].i_OFFLOAD_GRANT())

        cores[arch.nb_core-2].o_OFFLOAD(idma2.i_OFFLOAD())
        idma2.o_OFFLOAD_GRANT(cores[arch.nb_core-2].i_OFFLOAD_GRANT())

        # Cores
        for core_id in range(0, arch.nb_core):
            self.__o_FETCHEN( cores[core_id].i_FETCHEN() )

        for core_id in range(0, arch.nb_core):
            cores[core_id].o_BARRIER_REQ(cluster_registers.i_BARRIER_ACK(core_id))
        for core_id in range(0, arch.nb_core):
            cores[core_id].o_DATA(cores_ico[core_id].i_INPUT())
            cores_ico[core_id].o_MAP(tcdm.i_INPUT(core_id), base=arch.tcdm.area.base,
                size=arch.tcdm.area.size, rm_base=True)
            cores_ico[core_id].o_MAP(narrow_axi.i_INPUT())
            cores[core_id].o_FETCH(instr_router.i_INPUT())

        for core_id in range(0, arch.nb_core):
            fp_cores[core_id].o_DATA( cores_ico[core_id].i_INPUT() )
            self.__o_FETCHEN( fp_cores[core_id].i_FETCHEN() )

            # SSR in fp subsystem datem mover <-> memory port
            self.bind(fp_cores[core_id], 'ssr_dm0', cores_ico[core_id], 'input')
            self.bind(fp_cores[core_id], 'ssr_dm1', cores_ico[core_id], 'input')
            self.bind(fp_cores[core_id], 'ssr_dm2', cores_ico[core_id], 'input')

            # Use WireMaster & WireSlave
            # Add fpu sequence buffer in between int core and fp core to issue instructions
            if xfrep:
                self.bind(cores[core_id], 'acc_req', fpu_sequencers[core_id], 'input')
                self.bind(fpu_sequencers[core_id], 'output', fp_cores[core_id], 'acc_req')
                self.bind(cores[core_id], 'acc_req_ready', fpu_sequencers[core_id], 'acc_req_ready')
                self.bind(fpu_sequencers[core_id], 'acc_req_ready_o', fp_cores[core_id], 'acc_req_ready')
            else:
                # Comment out if we want to add sequencer
                self.bind(cores[core_id], 'acc_req', fp_cores[core_id], 'acc_req')
                self.bind(cores[core_id], 'acc_req_ready', fp_cores[core_id], 'acc_req_ready')

            self.bind(fp_cores[core_id], 'acc_rsp', cores[core_id], 'acc_rsp')

        for core_id in range(0, arch.nb_core):
            self.bind(cluster_registers, f'barrier_ack', cores[core_id], 'barrier_ack')
        for core_id in range(0, arch.nb_core):
            cluster_registers.o_EXTERNAL_IRQ(core_id, cores[core_id].i_IRQ(arch.barrier_irq))

        #Global Synchronization
        self.o_SYNC_INPUT(tcdm.i_SYNC_INPUT())
        self.bind(self, 'sync_irq', cluster_registers, 'global_barrier_req')

        # Cluster DMA
        idma.o_AXI(wide_axi_from_idma.i_INPUT())
        idma.o_TCDM(tcdm.i_DMA_INPUT())

        idma2.o_AXI(wide_axi_from_idma.i_INPUT())
        idma2.o_TCDM(tcdm.i_DMA_INPUT())

    def i_FETCHEN(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, 'fetchen', signature='wire<bool>')

    def __o_FETCHEN(self, itf: gvsoc.systree.SlaveItf):
        self.itf_bind('fetchen', itf, signature='wire<bool>', composite_bind=True)

    def i_WIDE_INPUT(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, 'wide_input', signature='io')

    def o_WIDE_INPUT(self, itf: gvsoc.systree.SlaveItf):
        self.itf_bind('wide_input', itf, signature='io', composite_bind=True)

    def i_WIDE_SOC(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, 'wide_soc', signature='io')

    def o_WIDE_SOC(self, itf: gvsoc.systree.SlaveItf):
        self.itf_bind('wide_soc', itf, signature='io')

    def i_NARROW_INPUT(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, 'narrow_input', signature='io')

    def o_NARROW_INPUT(self, itf: gvsoc.systree.SlaveItf):
        self.itf_bind('narrow_input', itf, signature='io', composite_bind=True)

    def i_NARROW_SOC(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, 'narrow_soc', signature='io')

    def o_NARROW_SOC(self, itf: gvsoc.systree.SlaveItf):
        self.itf_bind('narrow_soc', itf, signature='io')

    def i_SYNC_OUTPUT(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, 'sync_output', signature='io')

    def o_SYNC_OUTPUT(self, itf: gvsoc.systree.SlaveItf):
        self.itf_bind('sync_output', itf, signature='io')

    def i_SYNC_INPUT(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, f'sync_input', signature='io')

    def o_SYNC_INPUT(self, itf: gvsoc.systree.SlaveItf):
        self.itf_bind('sync_input', itf, signature='io', composite_bind=True)

    def i_SYNC_IRQ(self) -> gvsoc.systree.SlaveItf:
        return gvsoc.systree.SlaveItf(self, 'sync_irq', signature='wire<bool>')

    def o_SYNC_IRQ(self, itf: gvsoc.systree.SlaveItf):
        self.itf_bind('sync_irq', itf, signature='wire<bool>')
