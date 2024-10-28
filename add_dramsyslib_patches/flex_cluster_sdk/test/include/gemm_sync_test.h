#include "flex_runtime.h"
#include "kernels/gemm/gemm_systolic_wise.h"
#include "examples/example_one_cluster_gemm.h"
#include <math.h>

typedef enum {SYNC, XY} sync_e;

void gemm_sync(uint32_t M_size, uint32_t N_size, uint32_t K_size, uint32_t elem_size,
              uint32_t tile_dimension_M, uint32_t tile_dimension_N, uint32_t tile_dimension_K,
              sync_e sync_type){

    flex_global_barrier_xy();
    uint32_t CID = flex_get_cluster_id();
    GemmSystolicInfo info = gemm_systolic_wise_analysis(M_size, N_size, K_size, elem_size,tile_dimension_M,tile_dimension_N,tile_dimension_K);

    //Initialize RedMule Paramters
    if (flex_is_first_core()){
        flex_redmule_set_M(0, info.tile_dimension_M);
        flex_redmule_set_N(0, info.tile_dimension_N);
        flex_redmule_set_K(0, info.tile_dimension_K);
        flex_redmule_set_X(0, info.X_offset_1);
        flex_redmule_set_W(0, info.W_offset_1);
        flex_redmule_set_Y(0, info.Y_offset_1);
        flex_redmule_set_Z(0, info.X_offset_2);
        if (CID == 0) flex_log(info.total_iter);
    }

    flex_global_barrier_xy();

    for (int i = 0; i < info.total_iter; ++i){
        if (CID == 0) flex_timer_start();
        if (flex_is_dm_core()) gemm_systolic_wise_dma_access(info, i);
        if (flex_is_first_core()) gemm_systolic_wise_redmule(info, i);

        if (sync_type == SYNC) flex_global_barrier();
        else if (sync_type == XY) flex_global_barrier_xy();
        if (CID == 0) flex_timer_end();
    }
}

void gemm_sync_test(){
    uint32_t num_reps = 1;
    uint32_t M_size = 1024;
    uint32_t N_size = 512;
    uint32_t K_size = 128;
    uint32_t elem_size = 2;
    uint32_t tile_dimension_M = 32;
    uint32_t tile_dimension_N = 32;
    uint32_t tile_dimension_K = 32;

    /**************************************/
    /*  Program Execution Region -- Start */
    /**************************************/

    for (int i = 0; i < num_reps; i++){
      gemm_sync(M_size, N_size, K_size, elem_size, tile_dimension_M, tile_dimension_N, tile_dimension_K, SYNC);
    }

    /**************************************/
    /*  Program Execution Region -- Stop  */
    /**************************************/
}