#include "flex_runtime.h"
#include "kernels/gemm/gemm_systolic_wise.h"
#include "examples/example_one_cluster_gemm.h"
#include "sync_test.h"
#include "gemm_sync_test.h"
#include <math.h>

int main()
{
    uint32_t eoc_val = 0;
    flex_barrier_xy_init();
    flex_global_barrier_xy();
    flex_timer_start();
    /**************************************/
    /*  Program Execution Region -- Start */
    /**************************************/

    // Default tests
    example_one_cluster_gemm();
    // gemm_systolic_wise(1024, 512, 256, 2, 32, 32, 32);

    // Sync test
    // sync_test();

    // GEMM Sync test
    // gemm_sync_test();

    /**************************************/
    /*  Program Execution Region -- Stop  */
    /**************************************/
    flex_global_barrier_xy();
    flex_timer_end();
    flex_eoc(eoc_val);
	return 0;
}