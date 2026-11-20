# MicroSafe AI 360

Hackathon prototype for Tech4Bharat 2026, focused on fresh-cut apple and banana. It is a single Streamlit app backed by SQLite; no Docker or authentication is used.

## Setup

Use Python 3.11. From this folder:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

SQLite is initialized at `data/microsafe.db` on first launch. `data/` is created as needed.

## Demo

Click **Load demo seed batches** in the sidebar. The three labeled synthetic batches are a safe apple example, an apple with readings at 12 °C including an 18 °C spike (main demo), and a banana quality example. Open Dashboard, then Risk & Shelf Life, Anomaly Detection, Integrated Summary, and BatchTrace. The demo's risk and growth behavior is illustrative; do not use it for release decisions.

Register batches with pH and water activity. Storage CSV headers are `at,temp,humidity`. CSV readings are appended to the selected batch.

## Models

The deterministic generator in `services/ml_service.py` creates 3,000 synthetic records, stored in SQLite with `is_synthetic=1` the first time Evaluation is opened. The documented demo kinetic index applies a thermal multiplier of 2 for each 10 °C rise above 5 °C, accumulated exposure above 8 °C, and small pH/aw terms. It trains a random-forest classifier and gradient-boosting regressor with a stratified held-out 20% split. Evaluation reports ROC AUC, high-risk F1, and shelf-life MAE against synthetic labels only. Run `python -m ml.train` to calculate/cache metrics. Per-batch explanations use SHAP TreeExplainer when available and list the top three feature drivers in plain language.

Isolation Forest uses a tiny built-in demonstration reference profile, not facility-calibrated history.

## Visual model

The app always supports manual visual defect grading and clearly states that visual checks do not detect microbes. Optional fine-tuning uses ImageNet MobileNetV2 weights and a local copy of Kaggle Fruits Fresh and Rotten arranged as ImageFolder classes. Run `python -m ml.train_vision PATH_TO_DATASET`. The generated checkpoint is saved under `ml/vision_mobilenetv2.pt`; the current prototype does not load checkpoints for inference, so all grading remains manual.

## Pathogen intelligence

Growth-envelope fields in `data/growth_profiles.json` are `TO_VERIFY` pending source and strain/matrix verification; consequently the app returns an unassessed/borderline status instead of making up thresholds. No pathogen presence probability is produced. To optionally fetch taxonomy and one marker record per organism from NCBI, set `BIO_EMAIL` and run `python -m bio.fetch_pathogens`; the JSON cache is used for offline display. NCBI content is not fabricated or bundled.

## Limitations

- All generated training examples and seeded batches are synthetic and labeled as such. Metrics and model outputs are demonstrations, not validated shelf-life, spoilage, pathogen, or food-safety predictions.
- No model output confirms contamination. Only laboratory testing can confirm contamination.
- Growth thresholds need expert review and reliable organism-specific sources before rules can assess permissiveness.
- Vision inference is not active until a checkpoint loader and validated deployment checkpoint are supplied; manual grading is the fallback.
- The app is a local hackathon prototype, with no authentication, backup, access controls, calibration, or production audit guarantees.
- Simplifying choice: risk/shelf-life models are trained on demand; the demo seed is loaded only when the database has no batches; event history records registrations, readings, and assessments.
"# MicroSafe-AI" 
"# MicroSafe-AI" 
