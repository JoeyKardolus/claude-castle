# GPU fast transcription

Without this tier, Notulen transcribes recordings on the castle server's own CPU: it works, but a one-hour meeting takes hours to process. The GPU tier does the same meeting in minutes. It is part of the normal setup (onboard phase 9), and it can also be added or removed later by just asking Claude.

## The pieces

- **Worker image**: built from `infra/docker/notulen-worker/Dockerfile` by `build-worker.sh` in this directory. The image is too big to build or push reliably from a laptop, so the script boots a temporary Scaleway instance in your region, builds there, pushes to your Scaleway Container Registry (`rg.<region>.scw.cloud/castle/notulen-worker:v1`), and deletes the instance. A few cents per build.
- **Cluster**: a Scaleway Kapsule cluster named `castle` with one GPU pool (L4 card) that scales between 0 and 1 nodes. The control plane is free. A node exists, and bills, only while a transcription job runs; the autoscaler removes it about 10 minutes after it goes idle.
- **One Job per recording**: when you upload a recording, the dashboard creates a Kubernetes Job in the `castle` namespace that requests one GPU. The autoscaler boots a node (3 to 5 minutes the first time), the job transcribes and writes the minutes, and the node disappears again. If anything in that chain fails, the recording automatically falls back to CPU transcription; nothing is lost.
- **Database over the published port**: the worker writes its results straight into the castle server's postgres, which the stack publishes on port 5432. That port is protected by the long random database password; it is reachable from the internet because the short-lived GPU nodes have no fixed address to allow.
- **A key with one job**: the dashboard talks to the cluster with its own service account that may only create and list transcription Jobs in the `castle` namespace, nothing else. `make-dashboard-kubeconfig.sh` in this directory mints it. The admin kubeconfig from scw cannot be used inside the container: it authenticates through the scw command, which is not there.

## Costs

Roughly 80 cents per hour of GPU processing, which comes to cents per meeting. Everything else (control plane, registry within its free allowance, an idle cluster) is free or near it. There is also a safety ceiling of 50 jobs per day (`MAX_DAILY_JOBS`).

## Speaker labels, later

The default image transcribes everything but does not label who said what. To add speaker labels: make a free account at huggingface.co, create a read token, accept the model terms on both pyannote model pages (links in the Dockerfile header), then ask Claude to rebuild:

```
HF_TOKEN=<your token> infra/gpu/build-worker.sh v2
```

and bump `NOTULEN_WORKER_IMAGE` to the new tag in `/opt/castle/castle.env`, then `docker compose --env-file /opt/castle/castle.env up -d notulen`.

## Tearing it down

Asking Claude to remove the GPU tier does this: delete the cluster (`scw k8s cluster delete <cluster-id> region=<region> with-additional-resources=true`), delete the registry namespace (`scw registry namespace delete <namespace-id>`) if you want the image gone too, and remove `KUBECONFIG_DATA` from `/opt/castle/castle.env` before restarting notulen. The dashboard then quietly goes back to CPU transcription.
