#ifndef FLEXCLUSTERARCH_H
#define FLEXCLUSTERARCH_H

#define ARCH_NUM_CLUSTER_X 4
#define ARCH_NUM_CLUSTER_Y 4
#define ARCH_NUM_CORE_PER_CLUSTER 3
#define ARCH_CLUSTER_TCDM_BANK_WIDTH 8
#define ARCH_CLUSTER_TCDM_BANK_NB 64
#define ARCH_CLUSTER_TCDM_BASE 0x00000000
#define ARCH_CLUSTER_TCDM_SIZE 0x00400000
#define ARCH_CLUSTER_TCDM_REMOTE 0x30000000
#define ARCH_CLUSTER_STACK_BASE 0x10000000
#define ARCH_CLUSTER_STACK_SIZE 0x00020000
#define ARCH_CLUSTER_REG_BASE 0x20000000
#define ARCH_CLUSTER_REG_SIZE 0x00000200
#define ARCH_NUM_REDMULE_PER_CLUSTER 1
#define ARCH_REDMULE_CE_HEIGHT 128
#define ARCH_REDMULE_CE_WIDTH 32
#define ARCH_REDMULE_CE_PIPE 3
#define ARCH_REDMULE_ELEM_SIZE 2
#define ARCH_REDMULE_QUEUE_DEPTH 1
#define ARCH_REDMULE_REG_BASE 0x20010000
#define ARCH_REDMULE_REG_SIZE 0x00000200
#define ARCH_MTXTRAN_REG_BASE 0x20020000
#define ARCH_MTXTRAN_REG_SIZE 0x00000200
#define ARCH_IDMA_OUTSTAND_TXN 16
#define ARCH_IDMA_OUTSTAND_BURST 256
#define ARCH_HBM_START_BASE 0xc0000000
#define ARCH_HBM_NODE_INTERLEAVE 0x00100000
#define ARCH_NUM_HBM_CH_PER_NODE 1
#define ARCH_HBM_PLACEMENT [4,0,0,4]
#define ARCH_NOC_OUTSTANDING 64
#define ARCH_NOC_LINK_WIDTH 512
#define ARCH_INSTRUCTION_MEM_BASE 0x80000000
#define ARCH_INSTRUCTION_MEM_SIZE 0x00010000
#define ARCH_SOC_REGISTER_BASE 0x90000000
#define ARCH_SOC_REGISTER_SIZE 0x00010000
#define ARCH_SOC_REGISTER_EOC 0x90000000
#define ARCH_SOC_REGISTER_WAKEUP 0x90000004
#define ARCH_SYNC_BASE 0x40000000
#define ARCH_SYNC_INTERLEAVE 0x00000080
#define ARCH_SYNC_SPECIAL_MEM 0x00000040

#endif // FLEXCLUSTERARCH_H
