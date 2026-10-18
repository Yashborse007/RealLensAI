# RealLens AI

## Project Title

**RealLens AI: Real-Time Deepfake Detection Portal**

RealLens AI is an AI-powered portal for analyzing images, videos and audio to
identify potential manipulation and provide confidence scores and supporting
evidence. It combines a React client, an Express API gateway, a FastAPI service,
and optional MongoDB persistence.

The project foundation provides service startup and health checks. A health
response confirms availability only; it does not analyze media or provide a
model prediction.

> **Important:** This is a research and development project. A model prediction
> is an automated estimate, not proof that media is authentic or manipulated.
> Use independent verification and human review for consequential decisions.

## Problem Statement

AI-generated and edited media can be difficult to distinguish from genuine
content by inspection alone. A useful review tool needs to accept common media
types and present results in a way that makes uncertainty, evidence, model
availability, and processing limitations visible. A single opaque label is not
enough for a user to understand what the software examined.

## Motivation

RealLens AI explores a multi-service approach to media analysis and
explainability. The project brings together media upload, detector execution,
available modality scores, evidence reporting, and a user-facing history and
PDF summary in one application. It is also a foundation for controlled model
evaluation and future research, rather than a claim of production-grade
forensic certification.

## Objectives

- Accept supported image, video, and audio files through an authenticated
  application workflow.
- Route each file to the applicable detection modules.
- Preserve modality-level outputs and indicate failed, unavailable, and
  non-applicable modules.
- Present the prediction, confidence estimate, quality information, evidence,
  and processing trace together.
- Persist analysis records where MongoDB is available and provide report
  summaries for completed analyses.
- Keep proposed research and deployment capabilities separate from what is
  implemented and validated today.

## Features

### Implemented functionality

- React dashboard and responsive navigation for analysis, history, reports,
  profile, and admin views.
- Authenticated image, video, and audio uploads through the Express gateway.
- Gateway routes that forward media to the FastAPI service.
- One AI-service orchestrator that detects media type, invokes applicable
  modules, tracks module outcomes, records unavailable modalities, fuses
  eligible scores, and returns a standardized result.
- Per-modality scores and fusion participation/contribution details retained
  for analysis results.
- Analysis detail view with quality information, evidence, processing status,
  modality output, and model-version information.
- Client-side PDF report generation from an analysis result.
- Optional MongoDB persistence, with in-memory stores used by parts of the
  gateway when the database is unavailable.
- Python evaluation utilities for image/video robustness and cross-dataset
  evaluation when suitable manifests and checkpoints are supplied.

### Not implied by the feature list

- A model is not guaranteed to be loaded just because the service is running.
  The AI health endpoint reports image, video, and audio model availability.
- A listed training/evaluation component does not mean a trained model or
  completed experiment is included.
- A successful application build or unit test is not a benchmark of detection
  accuracy, robustness, or deployment performance.

## System Architecture

### Implemented architecture

```text
Browser
  └── React + Vite client (localhost:5173)
        └── /api requests ──> Express API gateway (localhost:5000)
                                ├── JWT authentication and authorization
                                ├── MongoDB (optional persistence)
                                └── FastAPI AI service (localhost:8000)
                                      ├── analysis orchestrator
                                      ├── image / video / audio modules
                                      ├── frequency supporting analysis
                                      └── PyTorch model managers and preprocessing
```

The dashboard forwards files and analysis requests through the gateway. The
gateway sends the uploaded media to the appropriate AI-service endpoint. The
orchestrator returns a common response envelope and keeps detector-specific
legacy fields where available. PDF output is generated in the client from
analysis data; it is not a separately hosted report-rendering service.

### Proposed architecture

The following are design directions, not claims that the corresponding
production infrastructure exists:

- Deploy the client, API gateway, AI service, model artifacts, and database as
  independently managed services.
- Use durable object storage for uploaded media and versioned model artifacts.
- Add an explicit calibration stage based on a held-out calibration set.
- Operate isolated, reproducible training and evaluation pipelines with dataset
  governance and model registry/versioning.
- Add monitoring, operational alerting, retention policies, and deployment
  automation appropriate to the target environment.

The repository includes a Docker Compose stack for the client, API gateway,
AI service, and MongoDB. The intended startup command is:

```bash
docker compose up --build
```

This stack uses environment variables for runtime configuration and avoids
embedding secrets in Dockerfiles. The compose setup is intended for local
Docker-based startup and should be run on a machine with Docker Engine and the
Compose plugin installed.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Client | React 18, Vite, React Router, Tailwind CSS, Recharts, Lucide |
| API gateway | Node.js, Express, Mongoose, Multer, Axios |
| Authentication | JSON Web Tokens, bcryptjs |
| AI service | Python, FastAPI, Uvicorn, Pydantic Settings |
| Inference and media processing | PyTorch, Torchvision, OpenCV, Pillow, librosa, SoundFile, NumPy, scikit-learn |
| Data store | MongoDB (optional for local UI/gateway operation; required for durable database persistence) |
| PDF | jsPDF in the browser |
| Tests | Vitest and Testing Library (client), Node test runner (server), pytest-compatible AI-service tests |

Exact package constraints are in `client/package.json`, `server/package.json`,
and `ai-service/requirements.txt`.

## Project Structure

```text
RealLensAIProject/
├── client/
│   ├── src/
│   │   ├── components/       # Common UI and analysis components
│   │   ├── context/          # Authentication and toast contexts
│   │   ├── layouts/          # Public and authenticated layouts
│   │   ├── pages/            # Dashboard, upload, analysis, history, reports, admin
│   │   ├── services/         # Gateway API client
│   │   └── utils/            # Client-side report generation
│   ├── package.json
│   └── .env.example
├── server/
│   ├── config/               # Database and security configuration
│   ├── controllers/          # Auth, media, analysis, and admin handlers
│   ├── middleware/           # Authentication, upload, and rate limits
│   ├── models/               # Mongoose schemas
│   ├── routes/               # Express API routes
│   ├── utils/                # Cleanup and performance helpers
│   ├── services/store/       # In-memory fallback stores
│   ├── tests/                # Node test-runner tests
│   ├── app.js                # Express application
│   ├── server.js             # Gateway startup
│   ├── package.json
│   └── .env.example
├── ml/                       # Shared ML implementation package
│   ├── datasets/             # Dataset readers
│   ├── evaluation/           # Metrics and evaluation tools
│   ├── experiments/          # Reserved for experiment assets
│   ├── inference/            # Image, video, audio, and multimodal inference
│   ├── models/               # Detector architectures
│   ├── training/             # Training helpers
│   ├── checkpoints/          # Local model checkpoints (ignored)
│   └── config.py             # Shared paths and model settings
├── ai-service/
│   ├── api/                  # FastAPI endpoint modules
│   ├── explainability/       # Grad-CAM support
│   ├── models/               # Model availability/load managers
│   ├── preprocessing/
│   ├── services/             # Detector services and analysis orchestrator
│   ├── tests/                # AI-service tests; pytest also imports root ml/
│   ├── datasets/             # AI-service training/evaluation datasets
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── datasets/                 # Optional repository-level dataset placeholder
├── reports/                  # Evaluation-output location (generated files)
├── scripts/                  # Standalone API helper scripts
├── docker-compose.yml        # Compose template; see deployment caveat above
└── README.md
```

Model checkpoints and datasets are local inputs and are not implied to be
included in source control. The AI service's default training/evaluation data
directory is `ai-service/datasets/`.

## Installation

### Prerequisites

- Node.js and npm compatible with the package manifests (Node.js 18 or newer
  recommended).
- Python 3.10 or newer recommended.
- MongoDB Community Server or an accessible MongoDB deployment for durable
  persistence.
- FFmpeg on `PATH` if video files should have their audio stream extracted for
  audio analysis.
- A machine with enough CPU/GPU memory for the chosen model and media. CUDA is
  used by PyTorch when available; the code can also run on CPU.

Install each service's dependencies using its own package manager. Model
weights and datasets may require separate acquisition and must be obtained
under their respective licenses.

## Environment Variables

Copy each service's example file to `.env` in that service directory, then
adjust values for your local setup. Do not commit real credentials or `.env`
files.

### `server/.env`

| Variable | Default in example | Purpose |
| --- | --- | --- |
| `PORT` | `5000` | Express listening port |
| `NODE_ENV` | `development` | Runtime mode; production enables stricter secret checks |
| `MONGO_URI` | `mongodb://localhost:27017/reallens_ai` | MongoDB connection string |
| `JWT_SECRET` | Development placeholder | JWT signing secret; replace with a unique, high-entropy secret before production |
| `ALLOW_ADMIN_REGISTRATION` | `false` | Allows admin registration only when explicitly enabled; do not enable casually |
| `RATE_LIMIT_MAX` | `200` | General API rate limit per window |
| `AUTH_RATE_LIMIT_MAX` | `50` | Login/registration rate limit per window |
| `UPLOAD_RATE_LIMIT_MAX` | `60` | Upload/analysis rate limit per window |
| `MAX_FILE_SIZE_BYTES` | `104857600` | Gateway upload size limit (100 MiB) |
| `CLIENT_URL` | `http://localhost:5173` | Primary allowed browser origin |
| `CORS_ORIGINS` | Empty | Comma-separated additional exact browser origins; local development also accepts private-LAN origins on Vite/React ports `5173` and `3000` |
| `AI_SERVICE_URL` | `http://localhost:8000` | FastAPI service base URL |

The development JWT value in `.env.example` is not suitable for production.
The server checks for a secure non-default secret in production and refuses to
start if it is missing or insecure.

### `ai-service/.env`

| Variable | Default in example | Purpose |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | FastAPI bind host |
| `PORT` | `8000` | FastAPI port |
| `DEBUG` | `False` | Enables development reload when running `main.py` |
| `ENVIRONMENT` | `development` | Documented environment label |
| `MODEL_WEIGHTS_DIR` | `../ml/checkpoints` | Model weights directory, relative to `ai-service/` |
| `IMAGE_MODEL_PATH` | `../ml/checkpoints/image/best_model.pth` | Image checkpoint path |
| `VIDEO_MODEL_PATH` | `../ml/checkpoints/video/best_model.pth` | Video checkpoint path |
| `AUDIO_MODEL_PATH` | `../ml/checkpoints/audio/best_model.pth` | Audio checkpoint path |
| `MAX_FILE_SIZE_BYTES` | `104857600` | AI-service upload size limit loaded by its settings |

The AI-service code default is 200 MiB, while its example `.env` sets the
effective configured value to 100 MiB; the gateway also defaults to 100 MiB.
The gateway is normally the first limit encountered. Keep both configured
limits aligned if changing them.
The shared ML defaults point to checkpoints in `ml/checkpoints/`; the AI
service example uses paths relative to `ai-service/` (`../ml/checkpoints/...`).
Set the `*_MODEL_PATH` values to the actual checkpoint files you have.

### `client/.env`

| Variable | Default in example | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:5000/api` | Gateway API base URL used by the production client |

During Vite development, the client uses the same-origin `/api` proxy to
`http://localhost:5000` regardless of `VITE_API_BASE_URL`, avoiding browser
CORS issues from stale local API URLs.

## MongoDB Setup

1. Install and start MongoDB locally, or create a database in a managed
   MongoDB service.
2. Set `MONGO_URI` in `server/.env`, for example:

   ```dotenv
   MONGO_URI=mongodb://localhost:27017/reallens_ai
   ```

3. Start the server and check its logs for the database connection status.
4. The application uses Mongoose models for user and analysis records.

The database name is part of the connection URI. MongoDB can create the
database and collections when the application first writes data. Development
and automated tests can use in-memory fallbacks when MongoDB is unavailable;
those records are temporary and are lost when the server process restarts.
Production startup requires a reachable MongoDB database and must not rely on
in-memory users or analyses.

## Frontend Setup

From the repository root:

```bash
cd client
npm install
copy .env.example .env
npm run dev
```

On PowerShell, `copy` is an alias for `Copy-Item`. Alternatively create
`client/.env` manually. The Vite development server is available at
`http://localhost:5173`.

Production build and local preview:

```bash
npm run build
npm run preview
```

## Backend Setup

In another terminal:

```bash
cd server
npm install
copy .env.example .env
npm run dev
```

The Express API listens on `http://localhost:5000` by default. To start without
the development watcher, run `npm start`.

If startup reports that port 5000 is already in use, check whether the backend
is already running before starting another copy. In PowerShell, identify the
listener with
`Get-NetTCPConnection -LocalPort 5000 -State Listen | Select-Object LocalPort, OwningProcess`,
then inspect it with `Get-Process -Id <PID>`. Stop it only if you confirm it is
an old RealLens backend process. If you choose another backend port, update the
frontend Vite `/api` proxy target in `client/vite.config.js` to match.

## AI Service Setup

In a third terminal:

```bash
cd ai-service
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux or macOS
source .venv/bin/activate
```

Then install and start:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
python main.py
```

On Linux/macOS, use `cp .env.example .env` instead of `copy`. The service
listens on `http://localhost:8000`. Interactive OpenAPI documentation is at
`http://localhost:8000/docs`.

The health endpoint may report individual models unavailable until compatible
checkpoints are present. The application can expose partial/unavailable module
status; a running service alone does not establish that inference is ready.

## Dataset Setup

The image dataset reader expects recursively discoverable files in two class
directories:

```text
ai-service/datasets/image/
├── real/
│   └── <licensed-real-image-files>
└── fake/
    └── <licensed-synthetic-or-manipulated-image-files>
```

Supported image extensions are `.jpg`, `.jpeg`, `.png`, and `.webp`. Keep
dataset licenses, provenance, and train/validation/test splits documented.
Avoid identity, source-video, or near-duplicate leakage between splits. Do not
place private or unlicensed media in the repository.

The image training helper can create a tiny deterministic synthetic dataset
when the configured training directory is empty. That dataset exists for
pipeline/testing convenience only; it is **not** a benchmark dataset and its
results must not be presented as detector performance.

Audio and video datasets/checkpoints require their respective upstream or
custom training pipelines. The current training modules do not provide a
complete end-to-end audio/video dataset preparation flow.

## Model Training

### Image

The repository contains an image training helper in
`ml/training/train_image.py`. From the repository root, after activating the
AI-service virtual environment and preparing real, properly licensed data, run:

```bash
python -c "from ml.training.train_image import train_image_model; print(train_image_model('ai-service/datasets/image'))"
```

By default it writes `best_model.pth` and `last_model.pth` under
`ml/checkpoints/image/`. Run the command from the repository root with the
AI-service virtual environment activated. The default helper uses its own train/validation
split and settings from `ml/config.py`; review the implementation and adapt the
split strategy to your data before drawing conclusions. The synthetic fallback
described above must not be used for evaluation claims.

### Video and audio

The repository's `train_video_model` and `train_audio_model` functions are
placeholders. They return `NOT_IMPLEMENTED` and describe the expected external
SBI/AASIST training pipeline/checkpoint requirements. No complete video or
audio training command is currently provided by this repository.

## Model Evaluation

The project contains reusable binary classification metrics and scripts for
cross-dataset and robustness evaluation. They require an appropriate trained
checkpoint and a labeled manifest; the presence of the scripts is not evidence
that an experiment has been run.

### Robustness evaluation (image/video visual models)

The default manifest is `ai-service/datasets/robustness_test_manifest.csv`.
Rows require `path` and `label` columns; `label` accepts `REAL`/`FAKE` or `0`/`1`.
An optional `split` column restricts evaluation to rows marked `test`. The
checkpoint defaults to `ml/checkpoints/image/best_model.pth`.

```bash
python -m ml.evaluation.robustness --help
python -m ml.evaluation.robustness \
  --manifest ai-service/datasets/robustness_test_manifest.csv \
  --checkpoint ml/checkpoints/image/best_model.pth
```

The script reports metrics for original and transformed visual inputs and
writes result files under the repository-level `reports/` directory by
default. Video scoring in this evaluation uses a trained image detector over
sampled frames; it is not a measurement of a trained temporal detector.

### Cross-dataset evaluation

`ml/evaluation/cross_dataset.py` accepts a manifest with `dataset`,
`split`, `path`, and `label` columns. It recognizes `DATASET_A`, `DATASET_B`,
and `DATASET_C`; only `DATASET_A` may have training rows. Identity fields can
be used to check for leakage where the source datasets provide comparable
identity metadata.

```bash
python -m ml.evaluation.cross_dataset --help
python -m ml.evaluation.cross_dataset \
  --manifest ai-service/datasets/cross_dataset_manifest.csv \
  --checkpoint ml/checkpoints/image/best_model.pth
```

Inspect the generated JSON/CSV/Markdown report, blockers, identity status,
dataset provenance, and checkpoint metadata before interpreting results.
Metrics are valid only for the manifest, checkpoint, preprocessing, and
experiment actually run. No experimental detection metrics are asserted in
this README.

## Running the Project

Run MongoDB if using durable persistence, then start the AI service, backend,
and frontend in separate terminals using their setup instructions above.

Check service availability:

```text
Frontend:             http://localhost:5173
Express health:       http://localhost:5000/api/health
Express → AI health:  http://localhost:5000/api/health/ai
FastAPI health:       http://localhost:8000/health
FastAPI OpenAPI:      http://localhost:8000/docs
```

Sign in or register through the client before accessing protected media and
analysis endpoints. Confirm that AI model statuses are available before
expecting a particular modality to contribute to a result.

## API Documentation

### Express gateway

The client API is rooted at `/api`. Relevant implemented route groups include:

| Method | Path | Authentication | Description |
| --- | --- | --- | --- |
| `GET` | `/api/health` | No | Gateway health check |
| `GET` | `/api/health/ai` | No | Checks connectivity to the AI service |
| `POST` | `/api/auth/register` | No | Register a user; subject to auth rate limit |
| `POST` | `/api/auth/login` | No | Obtain a JWT; subject to auth rate limit |
| `GET` | `/api/auth/me` | Bearer JWT | Return the current user |
| `POST` | `/api/media/upload` | Bearer JWT | Upload one media file in multipart field `file` |
| `POST` | `/api/media/analyze` | Bearer JWT | Analyze an uploaded media record; JSON body includes `mediaId` |
| `GET` | `/api/media/analysis/:id` | Bearer JWT | Retrieve an analysis associated with media |
| `GET` | `/api/media/reports/:id` | Bearer JWT | Retrieve an authorized report resource |
| `GET` | `/api/analyses` | Bearer JWT | List analyses for the signed-in user |
| `POST` | `/api/analyses` | Bearer JWT | Create an analysis record |
| `GET` | `/api/analyses/:id` | Bearer JWT | Retrieve an analysis record |
| `DELETE` | `/api/analyses/:id` | Bearer JWT | Delete an analysis record |

Admin endpoints are mounted at `/api/admin` and require the admin role. Upload
formats and size are validated at the gateway. The default gateway upload size
limit is 100 MiB.

### FastAPI AI service

All inference routes accept multipart form data with the field name `file`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | AI service and model availability |
| `POST` | `/predict/image` | Image analysis |
| `POST` | `/predict/image/explain` | Image Grad-CAM explanation when supported |
| `POST` | `/predict/video` | Video analysis |
| `POST` | `/predict/audio` | Audio analysis |
| `POST` | `/predict/multimodal` | Fusion of supplied modality scores |
| `POST` | `/api/detect/image` | Compatibility route for image analysis |
| `POST` | `/api/detect/video` | Compatibility route for video analysis |
| `POST` | `/api/detect/audio` | Compatibility route for audio analysis |
| `POST` | `/api/detect/multimodal` | Compatibility fusion route |

FastAPI serves its OpenAPI schema and interactive docs at `/openapi.json` and
`/docs`, respectively.

## Authentication

The Express service implements registration, login, and a protected current-user
endpoint. Passwords are stored as bcrypt hashes; successful login returns a
JWT, which the client sends in the `Authorization: Bearer <token>` header.
Protected routes require authentication, and admin routes additionally require
an admin role.

Set a strong, unique `JWT_SECRET` outside source control. The sample secret is
for local development only. Do not use development/demo fallback accounts or
in-memory data as a production identity or persistence mechanism.
Registration accepts valid email addresses from any domain, including Gmail
and Gmail plus-addresses; email casing is normalized before persistence and
sign-in. Public registration always creates a standard user account. Admin
registration must be explicitly enabled with `ALLOW_ADMIN_REGISTRATION=true`.

## Media Analysis

The AI service orchestrator is implemented in
`ai-service/services/analysis_orchestrator.py`. Its processing flow includes
media validation and quality checks, applicable extraction/analysis modules,
fusion, classification, confidence estimation, evidence assembly, and
processing metadata. Exact module execution depends on media type and available
checkpoints.

The standardized response contains:

```json
{
  "analysis_id": "generated-id",
  "media_type": "image",
  "status": "COMPLETED",
  "prediction": {
    "label": "REAL",
    "confidence": 0.0
  },
  "confidence": 0.0,
  "quality": {},
  "modalities": {
    "spatial": {
      "available": true,
      "status": "SUCCEEDED",
      "score": 0.0,
      "score_type": "fake_probability",
      "included_in_fusion": true
    }
  },
  "evidence": [],
  "timestamps": {},
  "processing": {},
  "model_versions": {}
}
```

Values above describe the response shape only; `0.0` values are placeholders,
not example results. The live response may contain more modality metadata and
legacy detector fields.

`status` distinguishes `COMPLETED`, `PARTIAL`, and `FAILED`. `modalities`
retains available scores and explanatory status for applicable modules; a
module that does not apply to the media type is marked non-applicable.

The current fusion code combines eligible available fake-probability signals
using configured, normalized weights. Frequency analysis is supporting evidence
and is not treated as a fake probability. Heuristic audio results are not
included as trained audio-model fusion evidence; temporal outputs are included
only when an eligible temporal checkpoint is available. Inspect the response's
fusion metadata to see the actual participating modalities for that analysis.

## Explainability

The analysis detail page and PDF report can display modality scores, fusion
participation/contributions, quality notes, evidence, pipeline module statuses,
unavailable modalities, timestamps, and model versions when provided by the
service. Image Grad-CAM support is implemented as a separate AI endpoint.

The confidence value currently uses a **decision-margin estimate** around the
fusion decision boundary. `processing.fusion.confidence_calibration` explicitly
reports `statistically_calibrated: false`; no held-out statistical calibration
model is configured. It must not be described as a calibrated probability.
Evidence should be interpreted as model output, not conclusive proof.

## PDF Reports

The client generates a downloadable PDF analysis summary using jsPDF. The
report builder includes available prediction, confidence, modality, fusion,
evidence, quality, processing, and model metadata, while marking missing
details as unreported where appropriate.

Reports are generated in the browser from the analysis object. The application
does not currently provide a dedicated server-side PDF rendering pipeline or
claim a digital signature or independently verified chain-of-custody
certificate.

## Testing

### Client

```bash
cd client
npm test
npm run build
```

### Backend

```bash
cd server
npm test
```

### AI service

Install the service dependencies (including pytest) in the AI service virtual
environment, then run:

```bash
cd ai-service
python -m pip install -r requirements.txt
python -m pytest
```

Focused test files are under `ai-service/tests/`, `server/tests/`, and
`client/src/__tests__/`.

### Validation recorded for the current implementation

- The client production build completed successfully; Vite emitted a warning
  about a JavaScript bundle chunk exceeding 500 kB.
- The client test run completed with 4 tests passing across 3 test files.
- The Node backend test suite completed with 70 tests passing.
- The AI-service suite completed with 104 tests passing. The test task sets
  `DEBUG=false` to avoid an invalid inherited `DEBUG` environment value.
- Python emitted deprecation warnings from Pydantic configuration, UTC logging,
  and the installed Starlette/httpx test client. These warnings do not fail the
  suite and remain maintenance items.
- These checks validate software behavior only. They do not measure model
  accuracy, robustness, fairness, or performance on representative external
  data.

## Robustness Evaluation

The AI service includes a robustness evaluation script for visual inputs. It
can test supported transformations such as compression, resizing, blur, noise,
brightness/contrast changes, and video frame-rate reduction. It writes
per-sample and aggregate metrics only when a valid test manifest and checkpoint
are provided and the experiment completes.

Robustness claims require a documented dataset, checkpoint hash, evaluation
configuration, and generated report. The script's existence or a passing unit
test alone does not establish robustness.

## Performance Evaluation

The repository includes request/database performance instrumentation and
evaluation code that can record inference timing summaries during actual
evaluation runs. The resulting latency depends on hardware, checkpoints,
media size, preprocessing, and runtime configuration.

No latency, throughput, or resource-consumption benchmark is reported in this
README because no controlled performance experiment is being claimed. For
reproducible measurements, record the hardware, operating system, Python and
PyTorch versions, checkpoint identity, warm-up policy, media composition,
batching, and repeated-run summary.

## Limitations

- Detection output can be wrong and should not be used alone for high-impact
  decisions.
- Confidence is not statistically calibrated.
- Results depend on model checkpoint availability, training data, preprocessing,
  and supported media quality.
- Video and audio availability or fusion participation can vary by installed
  tools and checkpoints; an unavailable modality must not be interpreted as a
  negative finding.
- Frequency-domain output is supporting information rather than a probability
  of manipulation.
- Video and audio training implementations are placeholders in this repository.
- The image training helper's synthetic fallback is only suitable for exercising
  code paths, not for detector-quality evaluation.
- In-memory gateway fallbacks are temporary and not durable.
- The client has fallback/sample data in some service API paths; the UI marks
  sample content where detectable. Sample content is not a real user analysis.
- The Compose file references missing Dockerfiles and is not validated as a
  complete deployment.
- Dataset rights, consent, privacy, demographic coverage, and distribution shift
  remain the responsibility of the dataset owner and deployment operator.

## Future Scope

- Complete and independently validate model training for video and audio.
- Add versioned, documented datasets and leakage-resistant split generation.
- Train and evaluate confidence calibration on a held-out calibration set.
- Improve missing-modality policies and user-facing explanation quality.
- Add controlled experiments for cross-dataset generalization, subgroup
  performance, and robustness to real-world transformations.
- Add reproducible latency and resource benchmarks across CPU/GPU hardware.
- Add durable object storage, retention/deletion controls, and operational
  monitoring.
- Add tested container definitions and continuous integration/deployment.
- Conduct accessibility reviews and usability studies with non-technical users.

## Team

Add the project contributors, roles, and institutional affiliations here before
publication. No contributor names or affiliations are inferred by this README.
