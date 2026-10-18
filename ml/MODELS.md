# Model documentation and licensing notes

The following notes describe the public model families used by RealLens AI. The code is designed to load official checkpoints when they are available locally, but the repository does not include restricted or proprietary weights.

## AIDE (image)

- Official repository: AIDE (official public repo for AI-generated image detection)
- Checkpoint source: Download the public pretrained checkpoint from the official project release or model card when permitted by the project license.
- License: Check the official repository license before commercial use or redistribution.
- Permitted use: Research and non-commercial use only if the upstream license requires it.
- Citation: Use the citation specified by the official AIDE repository or model card.
- Required dependencies: PyTorch, OpenCV, Pillow, NumPy, and any requirements declared by the official repo.
- Expected input: RGB image, typically resized to 224x224 with the same preprocessing used by the model.
- Output format: Real/fake probability or logits, typically converted to a fake probability in [0, 1].

## SBI (video)

- Official repository: Self-Blended Images (SBI) public implementation from the original research authors.
- Checkpoint source: Use the public checkpoint released by the official repository when allowed by the licensing terms.
- License: Confirm the upstream model license before any redistribution or commercial deployment.
- Permitted use: Research or deployment only under the repository license terms.
- Citation: Use the publication and code citation from the official SBI repository.
- Required dependencies: PyTorch, OpenCV, NumPy, PIL, and the official repo's environment file.
- Expected input: Face crops or frame crops extracted from video frames, processed consistently with the upstream model.
- Output format: Frame-level fake probability, aggregated into a single video score using a documented strategy such as mean or median.

## AASIST (audio)

- Official repository: AASIST public anti-spoofing model repository.
- Checkpoint source: Download the public pretrained checkpoint only from the official repository or model release that matches the license terms.
- License: Verify the relevant official license before commercial use.
- Permitted use: Research and permitted deployment only under the official licensing terms.
- Citation: Use the official AASIST paper and repository citation.
- Required dependencies: PyTorch, Librosa, NumPy, soundfile, and the repo's exact checkpoint format requirements.
- Expected input: Mono waveform resampled to the sampling rate required by the chosen checkpoint.
- Output format: Real/fake probability in [0, 1], interpreted as model confidence rather than forensic certainty.

## Important safety note

The code in this repository does not claim that any model is guaranteed to detect all AI-generated content. The system reports model confidence only, and a separate forensic decision may require expert review, additional evidence, and a vetted benchmark dataset.
