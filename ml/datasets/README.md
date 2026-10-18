# RealLens AI dataset documentation

## 1. Dataset in use

The project is structured to support a local deepfake benchmark with three independent folders:

- `datasets/image/real` and `datasets/image/fake`
- `datasets/video/real` and `datasets/video/fake`
- `datasets/audio/real` and `datasets/audio/fake`

This repository does not ship a restrictive licensed benchmark. The code expects the user to provide a labeled dataset locally or to download a public benchmark that meets their local licensing and compliance requirements.

## 2. Dataset license

This project does not automatically download or redistribute any restricted media dataset. Before using a public benchmark, confirm:

- the dataset license allows research or commercial work,
- the data source permits redistribution or local storage,
- the legal terms allow use in your deployment environment.

If a dataset requires manual registration, the user must download it explicitly and place it into the directories listed above.

## 3. How to download it

For each dataset that is permitted for your use case:

1. Register or accept the dataset license on the official source.
2. Download the archive or extracted files.
3. Copy the real samples into `datasets/.../real` and fake samples into `datasets/.../fake`.
4. Ensure the folder names are exactly `real` and `fake`.

Do not automatically fetch datasets that require payment, restricted licensing, or embargoed terms.

## 4. Where to place files

Place content like this:

```text
ai-service/
  datasets/
    image/
      real/
      fake/
    video/
      real/
      fake/
    audio/
      real/
      fake/
```

## 5. Real vs fake labeling

The dataset loader assigns:

- `REAL = 0`
- `FAKE = 1`

The label is determined only by the directory path. No silent relabeling is performed.

## 6. Dataset size

The dataset size is not fixed in code. The loader discovers all supported files recursively and will use whatever number of labeled samples the local dataset contains.

## 7. Train / validation / test split

The default split is:

- `TRAIN_RATIO = 0.70`
- `VAL_RATIO = 0.15`
- `TEST_RATIO = 0.15`

The project uses a reproducible random seed and a class-stratified split when a dataset is sufficiently balanced.

## 8. Leakage prevention

To avoid data leakage:

- keep all versions of the same media sample in the same split when metadata is known,
- avoid reusing the same source video for both train and validation/test,
- use only the training data for optimizer updates,
- tune thresholds on the validation split only,
- never tune hyperparameters using the final test split.

## 9. Required preprocessing

The data pipeline expects:

- images: JPEG, PNG, and WEBP under `datasets/image/*`
- videos: MP4/AVI/MOV/MKV/WEBM under `datasets/video/*`
- audio: WAV/MP3/M4A/FLAC/AAC under `datasets/audio/*`

The actual preprocessing is described in the model docs and pipeline modules; the code intentionally keeps the dataset storage and the processing logic separate.

## 10. Visual robustness evaluation

Create a CSV manifest containing the unchanged test rows, with `path,label` columns and an optional `split` column. When `split` is present, only rows whose value is `test` are evaluated. Relative media paths resolve from the manifest directory. Labels must be `REAL`/`FAKE` or `0`/`1`; the evaluator never edits the manifest or original media.

Run from the repository root after activating `ai-service`'s virtual environment
and configuring a trained image checkpoint:

```powershell
python -m ml.evaluation.robustness --manifest ai-service/datasets/robustness_test_manifest.csv --checkpoint ml/checkpoints/image/best_model.pth
```

The runner writes `reports/robustness_config.json`, `reports/robustness_results.csv`, `reports/robustness_report.json`, and (only when real metrics are computed) `reports/robustness_metrics.png` in the repository root. Images receive original, JPEG-compressed, resized, blurred, noise, brightness, and contrast variants. Videos also receive frame-rate reduction; video scores are the mean fake probability of sampled frames from the trained image detector, not a temporal-model evaluation. Missing manifests, checkpoints, dependencies, or valid predictions produce a `not_run` report and an empty result CSV rather than fabricated metrics.

## 11. Cross-dataset evaluation

The cross-dataset runner requires a frozen CSV manifest with `dataset,split,path,label` and recommends `identity_id,identity_namespace,manipulation_type,dataset_version,license,source_url,preprocessing`. Use `DATASET_A` rows with `split=train` only for identity/content leakage checks and `split=test` for in-dataset metrics; add `DATASET_B` and optionally `DATASET_C` test rows. Relative paths resolve from the manifest directory. The evaluator never creates a split or changes a label.

Identity IDs must refer to the same person consistently within a dataset. To compare identities across datasets, provide the same documented canonical `identity_namespace`; unrelated local subject IDs are not compared. The runner skips cohorts with detected train/test identity or exact-content overlap and labels missing/noncomparable identity metadata as unverified. Checkpoint training-dataset metadata is also reported as unverified if the checkpoint does not carry it.

Run from the repository root. Example:

```powershell
python -m ml.evaluation.cross_dataset --manifest ai-service/datasets/cross_dataset_manifest.csv --checkpoint ml/checkpoints/image/best_model.pth
```

Outputs are `reports/cross_dataset_report.json`, `reports/cross_dataset_comparison.csv`, and `reports/cross_dataset_comparison.md`. The table includes accuracy, precision, recall, F1, ROC-AUC, 10-bin ECE, Brier score, and mean/median/p95 inference time. Dataset source, version, license, manipulation types, identity coverage, preprocessing, model/checkpoint version, and hardware are recorded. ROC-AUC is null when a test cohort has one class; calibration and latency are computed only from actual predictions.

The repository contains no licensed benchmark media or dataset-specific license grants. Public download access alone does not establish reuse rights. For example, the [official FaceForensics++ repository](https://github.com/ondyari/FaceForensics) says its data is governed by separate Terms of Use and requires an access request; do not treat it as unrestricted. Verify each dataset's current terms before populating the manifest. No dataset is downloaded by this project.
