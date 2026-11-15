# c164: the job queue of the director's machine

While most worker nodes are down, the director's machine draws for everyone.
`queue/<id>.job` is a request, `receipts/<id>.txt` its receipt. Nobody edits this branch by hand:
`c164-realms/tools/a0job.sh` (on the assembly) sends a job and waits for the receipt,
`c164-realms/tools/a0worker.sh` runs them. Nothing here is ever merged anywhere.
