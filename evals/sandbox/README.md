# Prepared Hugging Face sandbox

Build `Dockerfile` as a private HF Docker Space image or publish it to a registry
that HF Sandboxes can access. Set `EVAL_SANDBOX_IMAGE` to its image reference and
`HF_NAMESPACE` to the owning account. Each agent and fresh grader still gets a
separate dedicated sandbox. The HF adapter checks system tools before accepting
the image; it does not install packages with an explicit image. The default image retains setup. Verify the
EvalPlus VCS commit, numpy and psutil versions against the benchmark manifest
using the standalone verifier installed_runtime() before using a newly built
image. Repeat that verification whenever evaluator pins change. The actual fresh
grader also checks its installed runtime and installs dependencies if stale.

The initial image was built from private Space
`shaquan1228/genius-eval-runtime-20261016`, source commit
`021d54580bdfa788c26176743220d32f85a60fc7`, available as
`hf.co/spaces/shaquan1228/genius-eval-runtime-20261016`. This is a frozen unique
Space source reference, not a registry digest pin: rebuilding the Space could
change the image. Parent run receipts should record the source commit and image.
No credentials belong in the image context; HF token forwarding is disabled.

`EVAL_RUN_ID` correlates flushed `vm_provisioning`, `vm_ready` and `vm_cleanup`
events and the `genius-run` child Job label. `vm_cleanup` is emitted after the SDK kill call returns; the SDK can report a failed cancellation only as a warning. Reconcile actual HF Job state after a hosted run as well.
