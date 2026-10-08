# R3 ensemble experiment preparation v1

R3-ENSEMBLE-001 asks for all-three operational evasion, distinct from R2 single
target transfer. The design was committed at e37c91d before search implementation,
from accepted base 99b012e5b72fbae9273fa73ccc8d84d579a69c83. R2-D_S outcomes,
scientific logs and output directories were not inspected. No Track A coordination
or results request was used. Only accepted pre-R3 protocol evidence informed choices.

Minimize max(score_i/threshold_i - 1), using D_S calibrated probability and D_M-B
and D_G raw operational scores. No learned fusion, averaging or probability
reinterpretation occurs. All three must be strictly below threshold with OK status
and exact reversible terminal validity. Inclusive threshold ties remain attacks.

The R1-only source-round-robin, deterministic hash-ordered seed rule admits attack
parents detected by at least one detector and retains one parent per inherited
lineage, up to 800. Eligibility uses existing complete OK frozen R1 operational
predictions only. This preparation hashes those accepted artifacts without deriving
real seed membership, opening payloads, or executing new eligibility inference.
The selector is a pure metadata interface; authoritative integration must validate
the supplied R1 decision records before passing their operational decisions.

Search budget: 61 uncached candidate evaluations per parent, each querying the
three-detector stack, hence 183 individual calls. Global ceilings: 48,800 and
146,400 for at most 800 parents. Baseline + 16 saliency probes + up to 32 greedy
variants + 8 fixed paddings + 4 global transforms provide this bound. Cache hits
are counted as logical requests separately. Errors count attempted calls and abort
without retries or non-OK benign imputation. Occlusion probes never become terminal
candidates. Coverage is the intersection of the three analyzed character prefixes.

The fixed reversible operators and padding literals reuse hash-bound generic R2
edit/render/inverse functions. Search minimizes the ensemble margin with fixed
priority and candidate-byte hash ties. It does not observe any R2-D_S outcomes.
Uncertainty remains 1000 percentile-bootstrap replicates, seed 1701, 95% CI and
inherited lineage clusters, using the unchanged frozen implementation.

The code is deliberately preparation-only and rejects authoritative oracle objects.
R3_READY_FOR_AUTHORITATIVE_EXECUTION denotes design and synthetic infrastructure
readiness. It does not authorize execution or claim live adapters were exercised.
Before real execution, the lead must separately authorize it, freeze actual seed
membership, complete protocol preflight and resolve exact runtime portability.
No authoritative terminal manifest, predictions or results were created.

R2-D_S results: NOT_OBSERVED. R3 results: NOT_STARTED. Verifier results:
NOT_STARTED. Protected confirmation: NOT_STARTED. Cycle 2: DEFERRED.
