# P1 data pipeline status

P1 was completed on 2026-08-11 with tracked source, profile, split, and hash
manifests. Raw CSV/tar files and generated Parquet files remain local and are
ignored by Git.

External datasets:

- BurstGPT v2.0: all three official `without_fails` files, 10,144,565 requests;
- Alibaba PAI GPU v2020: official job/task archives, 714,903 successful GPU jobs
  in the normalized batch schema;
- NLR/NREL EULP: baseline ResStock detached-residential and ComStock small-office
  profiles for ASHRAE 3A, 3C, and 5A, plus three configured mixed profiles.

The EULP profiles are modeled building-stock aggregates calibrated and validated
against measured data; they are not direct feeder measurements. Each source is
normalized to a configurable community peak while preserving its temporal shape.
The initial 3A/3C/5A matrix is a paper default, not a hard-coded limit. Running
`aidrbench data list-community-profiles` shows the available catalog, and configs
may select any downloaded profiles or add newly cataloged locations.

Generated scenario data:

- deterministic synthetic community data remains available for smoke tests only;
- the current DR manifest has 184 synthetic events over 90 days for
  `eulp_mixed_3a`; the same command can regenerate an identical factor schedule
  against any selected profile;
- Alibaba deadlines are scenario-generated slack factors and are always marked
  synthetic.

Validation checks content hashes, required schema, row counts, monotonic time,
and dataset-specific semantic invariants. `data/manifests/split_v1.yaml` records
chronological 60/20/20 partitions; `community_profile_split_v1.yaml` separately
holds the initial climate-level OOD partition.
