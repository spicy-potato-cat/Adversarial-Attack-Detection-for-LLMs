# DS-NUMERICAL-DISPOSITION-001

Status: PASS.

Disposition: NON_REPRODUCIBLE_EXECUTION_CONTEXT_NUMERICAL_ANOMALY. Causal origin UNRESOLVED; proven cause NONE. The OMP/MKL difference is a documented lead only.

The preserved historical raw/calibrated mismatches were 1.9159158060055859e-07 / 4.5186498820459775e-07. That execution produced zero accepted terminals or scientific outcomes and no D_M-B/D_G/ensemble feedback. Its exact query count remains unknown, bounded 1-61. No historical score is declared wrong or rewritten.

Current evidence: 243-record equivalence passes; 100 same-process and ten fresh-process repetitions are identical and exactly match the affected R1 seed; nine diagnostic R1 baselines reproduce, including long/multi-window/truncated inputs. These nine include the affected first seed. Native and operational mismatches are zero.

The new one-call durable preflight passed: raw delta 0.0, calibrated delta 0.0; both decisions match. Known diagnostic calls total 364: one prior repair, 362 numerical-diagnosis calls, one disposition gate. The historical failed attempt remains separately unknown.

Scientific treatment: exclude the failed execution from scientific results, preserve it as audit evidence, and use the currently verified frozen runtime for a new authoritative run. No tolerance, threshold, detector, generator algorithm, membership, query budget, transfer formula or bootstrap change is authorized by this disposition.

Restart is permissible because zero terminals/results were accepted, no transfer feedback was used, and the frozen search/population remain hash-bound. This is a disposition of an execution anomaly, without a claim of established mechanism.

```json
{
  "bindings": {
    "seed_manifest_sha256": "469ca9b92dee172e9124fe0d61c5fd6d6e7a22f05ab32f6d180763c95f658492",
    "generator_contract_sha256": "d6be1be6695ccb93893fd0b5e2868f1951202f119d1f8edcb03da083de8f42b4",
    "clarification_sha256": "be39feef8c3aff989b9d3b6c84ae26a7d96ba6ee29d6d2d297ed6d2cfd57e3fe",
    "query_journal_schema_sha256": "fc1cd4e65aad551e3165ae0410bf441e9459eba814b76fc95f7bcca778d5fe89",
    "runtime_binding_sha256": "d58c472c3187e8fa6c20efa5a2e9281e1036377076c39da2562c53eb6e13bbc5",
    "model_sha256": "c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157",
    "calibrator_sha256": "964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23",
    "feature_schema_sha256": "93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983",
    "threshold_id": "ds_v2_op3_cal_v1",
    "threshold": 0.5585373573968287,
    "replay_tolerance": 1e-12,
    "max_queries_per_seed": 61,
    "frozen_code_sha256": {
      "r2_ds_generator.py": "a198c1c7439c9fe0ccf5070821e6109409c7a9ce90f083dd9e36a5b5bc00dd8b",
      "r2_ds_design.py": "16adb08e79eaf220cdcadc28e24a2e07a055c30263d14dc71e34c5f38d4ea9cc",
      "r2_ds_generate_run.py": "ba296373087bedcf56631aab757d0b2e44e78c0eda73baa83743c7dc069e5fa2",
      "r2_ds_query_journal.py": "611b16ba48b1cf56bcc09c2f8980bc3df028038ad9f1ca72a3fb316faf123cd9"
    }
  },
  "gate": {
    "sample_id": "R1-DS-TXT-005-0010925a66bfbcf27df3b1a726edbea30b29fe5eeddbccce5c62c10525777785",
    "status": "OK",
    "raw_score": 0.9254972378912807,
    "calibrated_score": 0.844565288092724,
    "frozen_raw": 0.9254972378912807,
    "frozen_calibrated": 0.844565288092724,
    "raw_delta": 0.0,
    "calibrated_delta": 0.0,
    "native_match": true,
    "operational_match": true,
    "diagnostic_queries": 1,
    "environment": {
      "python": "3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]",
      "packages": {
        "torch": "2.6.0",
        "transformers": "4.49.0",
        "numpy": "2.1.3",
        "scipy": "1.17.1",
        "scikit-learn": "1.6.1"
      },
      "platform": "Windows-10-10.0.26200-SP0",
      "machine": "AMD64",
      "processor": "Intel64 Family 6 Model 154 Stepping 3, GenuineIntel",
      "numpy_backend": "Build Dependencies:\n  blas:\n    detection method: pkgconfig\n    found: true\n    include directory: C:/Users/runneradmin/AppData/Local/Temp/cibw-run-j8vn_sl2/cp311-win_amd64/build/venv/Lib/site-packages/scipy_openblas64/include\n    lib directory: C:/Users/runneradmin/AppData/Local/Temp/cibw-run-j8vn_sl2/cp311-win_amd64/build/venv/Lib/site-packages/scipy_openblas64/lib\n    name: scipy-openblas\n    openblas configuration: OpenBLAS 0.3.27  USE64BITINT DYNAMIC_ARCH NO_AFFINITY\n      Haswell MAX_THREADS=24\n    pc file directory: D:/a/numpy/numpy/.openblas\n    version: 0.3.27\n  lapack:\n    detection method: pkgconfig\n    found: true\n    include directory: C:/Users/runneradmin/AppData/Local/Temp/cibw-run-j8vn_sl2/cp311-win_amd64/build/venv/Lib/site-packages/scipy_openblas64/include\n    lib directory: C:/Users/runneradmin/AppData/Local/Temp/cibw-run-j8vn_sl2/cp311-win_amd64/build/venv/Lib/site-packages/scipy_openblas64/lib\n    name: scipy-openblas\n    openblas configuration: OpenBLAS 0.3.27  USE64BITINT DYNAMIC_ARCH NO_AFFINITY\n      Haswell MAX_THREADS=24\n    pc file directory: D:/a/numpy/numpy/.openblas\n    version: 0.3.27\nCompilers:\n  c:\n    commands: cl\n    linker: link\n    name: msvc\n    version: 19.29.30156\n  c++:\n    commands: cl\n    linker: link\n    name: msvc\n    version: 19.29.30156\n  cython:\n    commands: cython\n    linker: cython\n    name: cython\n    version: 3.0.11\nMachine Information:\n  build:\n    cpu: x86_64\n    endian: little\n    family: x86_64\n    system: windows\n  host:\n    cpu: x86_64\n    endian: little\n    family: x86_64\n    system: windows\nPython Information:\n  path: C:\\Users\\runneradmin\\AppData\\Local\\Temp\\build-env-0xvfl3v_\\Scripts\\python.exe\n  version: '3.11'\nSIMD Extensions:\n  baseline:\n  - SSE\n  - SSE2\n  - SSE3\n  found:\n  - SSSE3\n  - SSE41\n  - POPCNT\n  - SSE42\n  - AVX\n  - F16C\n  - FMA3\n  - AVX2\n  not found:\n  - AVX512F\n  - AVX512CD\n  - AVX512_SKX\n  - AVX512_CLX\n  - AVX512_CNL\n  - AVX512_ICL\n\n",
      "torch_backend": "PyTorch built with:\n  - C++ Version: 201703\n  - MSVC 192930157\n  - Intel(R) oneAPI Math Kernel Library Version 2025.0.1-Product Build 20241031 for Intel(R) 64 architecture applications\n  - Intel(R) MKL-DNN v3.5.3 (Git Hash 66f0cb9eb66affd2da3bf5f8d897376f04aae6af)\n  - OpenMP 2019\n  - LAPACK is enabled (usually provided by MKL)\n  - CPU capability usage: AVX2\n  - Build settings: BLAS_INFO=mkl, BUILD_TYPE=Release, COMMIT_SHA=2236df1770800ffea5697b11b0bb0d910b2e59e1, CXX_COMPILER=C:/actions-runner/_work/pytorch/pytorch/pytorch/.ci/pytorch/windows/tmp_bin/sccache-cl.exe, CXX_FLAGS=/DWIN32 /D_WINDOWS /GR /EHsc /Zc:__cplusplus /bigobj /FS /utf-8 -DUSE_PTHREADPOOL -DNDEBUG -DUSE_KINETO -DLIBKINETO_NOCUPTI -DLIBKINETO_NOROCTRACER -DLIBKINETO_NOXPUPTI=ON -DUSE_FBGEMM -DUSE_XNNPACK -DSYMBOLICATE_MOBILE_DEBUG_HANDLE /wd4624 /wd4068 /wd4067 /wd4267 /wd4661 /wd4717 /wd4244 /wd4804 /wd4273, LAPACK_INFO=mkl, PERF_WITH_AVX=1, PERF_WITH_AVX2=1, TORCH_VERSION=2.6.0, USE_CUDA=0, USE_CUDNN=OFF, USE_CUSPARSELT=OFF, USE_EXCEPTION_PTR=1, USE_GFLAGS=OFF, USE_GLOG=OFF, USE_GLOO=ON, USE_MKL=ON, USE_MKLDNN=ON, USE_MPI=OFF, USE_NCCL=OFF, USE_NNPACK=OFF, USE_OPENMP=ON, USE_ROCM=OFF, USE_ROCM_KERNEL_ASSERT=OFF, \n",
      "torch_threads": 8,
      "torch_interop_threads": 10,
      "deterministic_algorithms": true,
      "cudnn_deterministic": false,
      "cudnn_benchmark": false,
      "tf32_matmul": false,
      "tf32_cudnn": true,
      "cuda_version": null,
      "cudnn_version": null,
      "torch_initial_seed": 1701,
      "torch_rng_state_sha256": "812f3a64622ad1e81b43d21a18d0a7b0ea56aae4f9a15d54ac3c482d6da83b57",
      "numpy_rng_state_sha256": "479f7a31ca665712a23b5cfcdb6b8aa8172a8287397a36f475efb8467be5c781",
      "python_rng_state_sha256": "9451af12768b01f55c7c0ca92f6ae4d726ce5b2b826f6ee8fb39e75b468edd80",
      "numpy_seed": "UNKNOWN_NOT_SET_BY_DIAGNOSTIC",
      "python_seed": "UNKNOWN_NOT_SET_BY_DIAGNOSTIC",
      "grad_enabled_outside_inference": true,
      "variables": {
        "OMP_NUM_THREADS": null,
        "MKL_NUM_THREADS": null,
        "OPENBLAS_NUM_THREADS": null,
        "PYTHONHASHSEED": null
      }
    },
    "journal": {
      "path": "detection_service/outputs/ds-numerical-disposition-001/gate_queries_v1.jsonl",
      "sha256": "535c0768d817bda54ce82e0e041a15d85ee4c91ddbb16d6bc92560ebc2a4111e",
      "logical_path": "detection_service/outputs/ds-numerical-disposition-001/gate_queries_v1_logical.jsonl",
      "logical_sha256": "d1ac26c888c970e5b410990f7a0b327a92a8484266ff2c4054f5bcca261055a3"
    }
  }
}
```
