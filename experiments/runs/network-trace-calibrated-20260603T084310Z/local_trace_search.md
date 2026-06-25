# Local Trace Search

Commands run from `/home/ubuntu/iDynamics` before downloading the external sample:

```sh
find . -maxdepth 5 -type f \( -iname '*ripe*' -o -iname '*caida*' -o -iname '*alibaba*' -o -iname '*trace*' -o -iname '*burst*' -o -iname '*calibrat*' \) | sort | head -300
rg --files | rg -i '(ripe|caida|alibaba|trace|burst|network|calibrat|ledger|paper_claims|main_TSC|experiment|runs)'
```

Finding: the repository contained existing iDynamics synthetic/replay traces, including `raw/burst_correlated_trace.csv` in prior run ledgers and trace-provider source/tests, but no downloaded RIPE, CAIDA, or Alibaba trace material was found locally.
