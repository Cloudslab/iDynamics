# Third-Party Notices

This repository is licensed under the MIT License. Third-party software,
benchmark applications, tools, and public data remain under their own licenses
or terms.

## Benchmark Applications

Third-party application source code is not vendored in this repository. Fetch
scripts clone pinned upstream commits into `external/benchmarks/`, which is
ignored by Git.

| Adapter | Upstream source | Pinned commit | License recorded for upstream |
| --- | --- | --- | --- |
| DeathStarBench Social Network | `https://github.com/delimitrou/DeathStarBench.git` | `6ecb09706140f8730b5385c08f1386c654c3c526` | Apache-2.0 |
| DeathStarBench Hotel Reservation | `https://github.com/delimitrou/DeathStarBench.git` | `6ecb09706140f8730b5385c08f1386c654c3c526` | Apache-2.0 |
| Online Boutique / Google Microservices Demo | `https://github.com/GoogleCloudPlatform/microservices-demo.git` | `5096a85b2f3bf41bef53363cfe5478d5b86ac701` | Apache-2.0 |
| TrainTicket | `https://github.com/FudanSELab/train-ticket.git` | `313886e99befb94be6cd45f085c98e0019f59829` | Apache-2.0 |
| Sock Shop | `https://github.com/microservices-demo/microservices-demo.git` | `9dff06fae4981921caec6a62393a6ebfce4b3e3f` | Apache-2.0 |
| CPU-only MoE Serving Microbenchmark | Repository-local implementation | Not applicable | MIT, as part of this repository |

Consult each fetched upstream checkout for complete license text, notices, and
transitive dependency terms before redistributing those applications or their
container images.

## Python And Command-Line Dependencies

The package declares optional Python extras in `setup.cfg`; those dependencies
are not vendored. Declared packages include `matplotlib`, `networkx`, `numpy`,
`pandas`, `prometheus-api-client`, `seaborn`, `kubernetes`, `paramiko`, `build`,
`codespell`, `pre-commit`, `pytest`, `ruff`, `shellcheck-py`, and `wheel`.
The build backend also uses `setuptools` and `wheel`.

Live benchmark helpers may require external command-line tools such as
`kubectl`, `helm`, `curl`, `git`, and Linux traffic-control tooling. These
tools are not distributed with this repository.

## Public Trace Data

The RIPE Atlas calibration artifacts use public ping RTT measurement data for
measurement `1001`, target `k.root-servers.net`, and sample window
`2026-06-02` to `2026-06-03`, as recorded in the reproducibility manifests.
The derived public artifacts are limited to latency-scale calibration and CDF
visualization. They do not claim bandwidth calibration or packet/path replay.

Attribute RIPE Atlas data to RIPE Atlas / RIPE NCC when reusing the calibration
artifacts, and review the RIPE Atlas terms and privacy documentation for any
new data collection.

## Copied And Generated Assets

The diagram PNG files in `reproducibility/diagrams/` and the top-level
framework image are repository figure assets. Their source mapping is recorded
in `reproducibility/diagrams/source-attribution.yaml`.

Expected SVG, CSV, Markdown, and TeX outputs under `reproducibility/items/*`
are generated from committed data and scripts in the corresponding artifact
folders. Their evidence boundaries are defined by each `manifest.yaml`.
