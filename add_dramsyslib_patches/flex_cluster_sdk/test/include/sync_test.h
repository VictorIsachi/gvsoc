#include "flex_runtime.h"
#include "kernels/gemm/gemm_systolic_wise.h"
#include "examples/example_one_cluster_gemm.h"
#include <math.h>

void sync_test(){
    uint32_t num_reps = 10;
    /**************************************/
    /*  Program Execution Region -- Start */
    /**************************************/

    for (int i = 0; i < num_reps; i++){
      flex_barrier_xy_init();
      flex_timer_start();
      flex_global_barrier_xy();
      flex_timer_end();
    }
    
    for (int i = 0; i < num_reps; i++){
      flex_barrier_init();
      flex_timer_start();
      flex_global_barrier();
      flex_timer_end();
    }

    /**************************************/
    /*  Program Execution Region -- Stop  */
    /**************************************/
}