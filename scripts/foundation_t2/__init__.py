"""Foundation T2 retention deposit + round-trip harness.

Governed by `docs/design/foundation_t2_execution_readiness_contract.md`. This
package prepares a metadata-only deposit manifest from committed PR-B.1
evidence, and drives deposit -> observe -> restore -> compare through an
abstract Destination interface. CI / tests use a local-mock destination only;
no real cloud, credentials, env-var values, or network are accessed here.

Real cloud deposit is performed only by an operator with credentials already
available securely, and only if the destination alias and file set are
unambiguous and evidence can be scrubbed. If not, the harness stops before
deposit and reports honestly — it never fakes success. It approves no
byte-admissibility, constructs no epoch, authorises no ML Step 4, and changes
no production.
"""
