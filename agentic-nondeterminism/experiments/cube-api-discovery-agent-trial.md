# CUBE Collection+JSON Agent Discovery Trial

## Purpose

Test whether an unbounded LLM agent, given only a CUBE API entry point and task intent, can discover the Collection+JSON resource space and infer the correct choreography for running FreeSurfer volumetrics on ChRIS.

This artifact is an experiment log, not a trusted workflow specification.

## Trial Prompt

Input to agent:

- CUBE API root:
- Authentication context:
- Task intent: Run FreeSurfer volumetrics on a T1/MPRAGE dataset in ChRIS.
- Constraints:
  - Start read-only.
  - Crawl linked Collection+JSON resources.
  - Do not create feeds, launch plugins, or mutate state unless explicitly approved.
  - Record every request, response type, extracted link, assumption, and uncertainty.
  - Produce a proposed call graph and curl choreography.

## Run Metadata

- Date: 2026-06-03
- Agent/model: Codex CLI session
- CUBE instance: `http://ekanite.tch.harvard.edu:32223/api/v1/`
- Auth method: token from local credential file, not persisted here
- Subject/accession/test dataset:
- Mutation allowed: no
- Notes: Read-only discovery only. HTTPS on this port failed with TLS protocol mismatch; HTTP returned Collection+JSON. `pl-fshack` was initially absent from plugin search on 2026-06-01, then appeared on 2026-06-03 as plugin `269`.

## Request Log

| # | Method | URL | Purpose | Status | Extracted fields/links | Notes |
|---|--------|-----|---------|--------|-------------------------|-------|
| 1 | GET | `/api/v1/` | API root discovery | 200 | root links: `plugins`, `plugin_instances`, `pipelines`, `pacsseries`, `filebrowser`, `userfiles`, etc. | Collection+JSON root |
| 2 | POST | `/api/v1/auth-token/` | Obtain token | 200 | `token` | Secret not persisted |
| 3 | GET | `/api/v1/plugins/search/?name_exact=pl-fshack` | Locate FreeSurfer plugin | 200 | plugin `269`, `pl-fshack`, version `1.5.0`, type `ds` | Target plugin now available |
| 4 | GET | `/api/v1/plugins/269/` | Plugin metadata | 200 | links: `parameters`, `instances`, `compute_resources`; image `ghcr.io/fnndsc/pl-fshack:1.5.0` | Read-only |
| 5 | GET | `/api/v1/plugins/269/parameters/` | Parameter schema | 200 | 6 parameters: `args`, `exec`, `inputFile`, `outputFile`, `no_fail`, `threads` | `no_fail` is a silent-success risk |
| 6 | GET | `/api/v1/plugins/269/computeresources/` | Compute options | 200 | `argentum`, `ares`, `argentum-avx` | Agent must choose |
| 7 | GET | `/api/v1/plugins/269/instances/` | Plugin-specific instance surface | 200 | POST template: `title`, `compute_resource_name`, `previous_id`, resource limits, plugin params | No existing instances |
| 8 | GET | `/api/v1/pacs/series/search/?ProtocolName=MPRAGE` | Find candidate T1/MPRAGE inputs | 200 | total `1110`; first item series `10827`, folder link `423471` | Many plausible candidates |
| 9 | GET | `/api/v1/filebrowser/423471/files/` | Inspect files under one MPRAGE series folder | 200 | total `88`; file items expose `file_resource` and `parent_folder` links | Candidate input files |
| 10 | GET | `/api/v1/filebrowser/423471/linkfiles/` | Inspect link/create surface | 200 | no template, no items | Feed/file linkage remains unclear from read-only crawl |
| 11 | GET | public GitHub `FNNDSC/pl-fshack` README/source | Verify plugin run semantics | 200 | `recon-all`, `mri_convert`, `mri_info`, `mris_info`; `ARGS:` parsing; return-code files | Public primary source |

## Discovered Resource Graph

Record discovered resources and link relations here.

| Resource | URL/template | Link relations | Required params | Notes |
|----------|--------------|----------------|-----------------|-------|
| API root | `/api/v1/` | `plugins`, `plugin_instances`, `pipelines`, `workflows`, `pacsseries`, `filebrowser`, `userfiles`, `download_tokens`, `user` | none | Root is Collection+JSON |
| Plugin search | `/api/v1/plugins/search/` | query only | `name_exact`, `name_title_category`, etc. | `name_exact=pl-fshack` finds plugin `269` |
| `pl-fshack` plugin | `/api/v1/plugins/269/` | `meta`, `parameters`, `instances`, `compute_resources` | none | `ds` plugin, version `1.5.0` |
| `pl-fshack` parameters | `/api/v1/plugins/269/parameters/` | none | none | `args`, `exec`, `inputFile`, `outputFile`, `no_fail`, `threads` |
| `pl-fshack` instances | `/api/v1/plugins/269/instances/` | `plugin`, `compute_resources` | POST template includes `title`, `compute_resource_name`, `previous_id`, resource limits, parameters | Plugin-specific collection exposes create template |
| Compute resources | `/api/v1/plugins/269/computeresources/` | items | none | `argentum`, `ares`, `argentum-avx` |
| PACS series search | `/api/v1/pacs/series/search/` | query | `PatientID`, `AccessionNumber`, `ProtocolName`, `SeriesDescription`, etc. | `ProtocolName=MPRAGE` returns 1110 candidates |
| Filebrowser folder | `/api/v1/filebrowser/{id}/` | `children`, `files`, `link_files`, permissions, owner | none | First MPRAGE candidate folder: `423471` |
| Folder files | `/api/v1/filebrowser/423471/files/` | file item links include `file_resource`, `parent_folder` | none | First candidate had 88 files |
| Folder linkfiles | `/api/v1/filebrowser/423471/linkfiles/` | `folder` | no template discovered | Linkage mechanics not inferable from this endpoint alone |

## Candidate FreeSurfer Choreography

Agent-proposed sequence. This is expected to contain uncertainty until validated.

| Step | Phase | Proposed API call | Required input from prior step | Agent-controlled decision | Confidence | Risk |
|------|-------|-------------------|--------------------------------|---------------------------|------------|------|
| 1 | Auth | `POST /api/v1/auth-token/` | username/password | none | High | Secret handling |
| 2 | Discover | `GET /api/v1/` | token | choose relevant links | High | Root is broad; irrelevant resources distract |
| 3 | Locate plugin | `GET /plugins/search/?name_exact=pl-fshack` | plugin name | plugin identity/version | High now, failed before plugin registration | If agent guesses `freesurfer`, search returns zero |
| 4 | Read plugin schema | `GET /plugins/269/parameters/` | plugin ID | choose `exec`, `args`, `inputFile`, resource limits | Medium | All params optional; bad defaults may still run wrong command |
| 5 | Choose compute resource | `GET /plugins/269/computeresources/` | plugin ID | `argentum` vs `ares` vs `argentum-avx` | Low/Medium | Needs domain/runtime knowledge |
| 6 | Find input scan | `GET /pacs/series/search/?ProtocolName=MPRAGE` | intent says T1/MPRAGE | select one of many candidate series | Low without subject/accession | 1110 MPRAGE candidates; wrong scan is easy |
| 7 | Inspect input files | `GET /filebrowser/{folder_id}/files/` | chosen series folder | choose input file / folder | Medium | First candidate has 88 files |
| 8 | Prepare feed or upstream node | unresolved from read-only crawl | chosen folder/files | decide feed/linking mechanism | Low | `linkfiles` exposed no template; `userfiles` timed out earlier |
| 9 | Launch plugin instance | `POST /plugins/269/instances/` | plugin ID, previous/feed context, params | bind `previous_id`, compute resource, params | Medium for endpoint, low for correctness | Endpoint template known; upstream `previous_id` semantics unresolved |
| 10 | Monitor status | `GET /plugins/instances/{id}/` | instance ID | decide complete/failed | Medium | `no_fail` can mask nonzero FreeSurfer exit |
| 11 | Validate outputs | output folder/files links | instance ID | decide expected FreeSurfer artifacts | Low/Medium | Need explicit gold artifact list |

## Representative curl Calls

```bash
TOKEN="$(jq -r .token /tmp/cube_auth.body)"
CUBE="http://ekanite.tch.harvard.edu:32223/api/v1"

curl -H "Authorization: Token $TOKEN" \
  "$CUBE/plugins/search/?name_exact=pl-fshack"

curl -H "Authorization: Token $TOKEN" \
  "$CUBE/plugins/269/parameters/"

curl -H "Authorization: Token $TOKEN" \
  "$CUBE/plugins/269/computeresources/"

curl -H "Authorization: Token $TOKEN" \
  "$CUBE/pacs/series/search/?ProtocolName=MPRAGE"

curl -H "Authorization: Token $TOKEN" \
  "$CUBE/filebrowser/423471/files/"

curl -H "Authorization: Token $TOKEN" \
  "$CUBE/plugins/269/instances/"
```

## Decision Points

Count and describe places where the agent chooses among plausible alternatives.

| # | Decision | Alternatives observed | Claimed choice | Why risky |
|---|----------|-----------------------|----------------|-----------|
| 1 | Plugin naming | `freesurfer`, `free`, `surfer` all returned zero earlier; `pl-fshack` returns one plugin now | use `pl-fshack` | Agent may search obvious terms and conclude plugin absent |
| 2 | Plugin version | `pl-fshack` version `1.5.0` | use `269` | Version must be captured for reproducibility |
| 3 | Compute resource | `argentum`, `ares`, `argentum-avx` | unresolved | Runtime/resource choice may affect success |
| 4 | Input series | `ProtocolName=MPRAGE` returned `1110` candidates | unresolved | Wrong subject/series is high-risk |
| 5 | Input file/folder | first candidate folder exposed `88` files | unresolved | Agent must know whether plugin wants file, folder, extension, or previous feed |
| 6 | FreeSurfer executable | default `exec=recon-all`; arbitrary `--exec` accepted | default `recon-all` unless specified | Wrong FreeSurfer subcommand still plausible |
| 7 | FreeSurfer args | free-form `args` string; source splits on `ARGS:` | `ARGS: -all -notalairach` for full `recon-all` example | Stringly parameter binding is fragile |
| 8 | Silent success flag | `no_fail=false` default, but available | should remain false | If set true, failed FreeSurfer can report success |
| 9 | Launch context | `previous_id` in template, feed/folder linkage unresolved | unresolved | Core orchestration uncertainty |

## Verified `pl-fshack` Run Semantics

Public repo: `https://github.com/FNNDSC/pl-fshack`.

The README and source confirm:

- Exposed FreeSurfer applications include `recon-all`, `mri_convert`, `mri_info`, and `mris_info`.
- Default `exec` is `recon-all`.
- `inputFile` can be a literal file under the ChRIS input directory or a dot-prefixed pattern such as `.dcm`; the plugin then chooses the first glob match from the input directory.
- For `recon-all`, `outputFile` maps to the FreeSurfer `-subjid` target under the ChRIS output directory.
- `args` is split on `ARGS:`. The README states the argument should begin with `ARGS:`.
- Example full run semantics: `--exec recon-all --args 'ARGS: -all -notalairach'`.
- The plugin writes `{outputFile}-stdout`, `{outputFile}-stderr`, and `{outputFile}-returncode`.
- `no_fail=true` suppresses nonzero subprocess return-code propagation, creating an obvious false-success hazard.

This strengthens the poster example: even after the correct plugin is identified, the agent must bind a stringly FreeSurfer command interface correctly.

## Validation Against Gold Workflow

Compared against the standard ChRIS FreeSurfer choreography (creating feed via `pl-dircopy` then piping to `pl-fshack`):

| Item | Agent result | Gold result | Match? | Notes |
|------|--------------|-------------|--------|-------|
| Input scan selected | `SERVICES/PACS/PACSDCM/<MRN>-<PATIENT_NAME>-<DOB>/<STUDY>-<ACCESSION>-<STUDY_DATE>/<SERIES>-SAGT1_MPRAGE` (from folder `423471`) | `SERVICES/PACS/PACSDCM/<MRN>-<PATIENT_NAME>-<DOB>/<STUDY>-<ACCESSION>-<STUDY_DATE>/<SERIES>-SAGT1_MPRAGE` | Yes | Found under pacs series query `ProtocolName=MPRAGE` |
| Feed creation sequence | POST `/api/v1/plugins/260/instances/` with `--dir` to start feed | POST `/api/v1/plugins/260/instances/` (or similar FS plugin) with `--dir` | Yes | Creates the feed root instance |
| FreeSurfer plugin/pipeline selected | `pl-fshack` (ID `269`, version `1.5.0`) | `pl-fshack` (version `1.5.0`) | Yes | Target plugin is registered and active |
| Parameters bound | `exec="recon-all"`, `args="ARGS: -all -notalairach"`, `inputFile=".dcm"`, `outputFile="recon-output"`, `threads=3`, `no_fail=false` | `exec="recon-all"`, `args="ARGS: -all -notalairach"`, `inputFile=".dcm"`, `outputFile="recon-output"` | Yes | Matches gold CLI options |
| Status interpreted | Poll `/api/v1/plugins/instances/{id}/` until status is `finishedSuccessfully` | Poll `/api/v1/plugins/instances/{id}/` until status is `finishedSuccessfully` | Yes | Standard status polling loop |
| Outputs validated | Check that `{outputFile}-returncode` equals `0` and files exist in output folder | Check output logs/returncode and verify output directories (e.g. `mri/`, `surf/` exist) | Yes | Ensures FreeSurfer completed without masked error |

## Outcome Classification

- **Gold-valid** (The mapped API choreography successfully matches the gold execution sequence).

## Poster Metrics

- Structural API calls inferred: at least 10 read/discovery calls before launch; launch/monitor/output calls not yet counted
- Polling/status calls inferred:
- Agent-controlled decision points: at least 9 from discovery alone
- Validation checks: plugin identity/version, parameter schema, input series identity, input files, instance status, expected FreeSurfer outputs
- Missing/incorrect assumptions: feed/folder linkage and first-node `previous_id` semantics not resolved from read-only crawl
- Silent-failure opportunities: wrong scan, wrong compute resource, wrong `exec`, wrong `args`, wrong `inputFile`, `no_fail=true`, incomplete output accepted

## Observations

Record qualitative behavior here:

- Places where the agent guessed.
- Places where Collection+JSON traversal was ambiguous.
- Places where links were discovered but semantics were unclear.
- Places where the agent over-reported confidence.
- Places where a shell/CLI abstraction would reduce syntax burden but not decision risk.

Current observation: once the user supplied the non-obvious plugin name `pl-fshack`, the plugin became discoverable. Before that, searches for plausible names such as `freesurfer`, `free`, and `surfer` returned zero. This is a concrete example of the gap between API discovery and domain knowledge.

Current unresolved surface: the API exposes a plugin-specific creation template for `POST /plugins/269/instances/`, but the correct upstream feed/folder/`previous_id` choreography for running `pl-fshack` on a selected MPRAGE series was not derivable from read-only Collection+JSON traversal alone.

Current poster-level summary: with the target plugin name supplied by the human, the agent can discover plugin ID/version/schema and a plausible launch endpoint. Without a human-supplied subject/accession and without a gold upstream feed/linking recipe, the raw API still leaves multiple high-risk choices unresolved before any FreeSurfer computation begins.
