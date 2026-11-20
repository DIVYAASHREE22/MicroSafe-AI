import streamlit as st
from services.db import init_db, list_batches, seed_demo
from services.ui import dashboard, register_batch, storage_log, assess_batch, batch_trace, pathogen_page, visual_check
from services.ml_service import ensure_models

st.set_page_config(page_title="MicroSafe AI 360", page_icon="🥬", layout="wide")
st.markdown("""<style>
.stApp { background:#f4f7f4; color:#17352d; }
[data-testid="stSidebar"] { background-color:#0B3D2E; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] label p,
[data-testid="stSidebar"] label span,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] div[role="radiogroup"] * { color:#FFFFFF !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color:#CDE7E1 !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p { color:#7FC8BC !important; font-weight:600; }
.stButton>button { background:#0F8B8D; color:white; border:0; border-radius:8px; }
.notice { background:#e5f3ef; border-left:5px solid #0F8B8D; padding:12px; }
.warning { background:#fff0df; border-left:5px solid #E8833A; padding:12px; }
</style>""", unsafe_allow_html=True)
init_db()
with st.sidebar:
    st.title("🥬 MicroSafe AI 360"); st.caption("Tech4Bharat 2026 · Micro Food Processors")
    page=st.radio("Navigation",["Dashboard","Register Batch","Storage Log","Risk & Shelf Life","Anomaly Detection","Visual Defect Check","Pathogen Intelligence","Integrated Summary","BatchTrace","Evaluation"])
    st.markdown("---")
    if st.button("Load demo seed batches",use_container_width=True): seed_demo(); st.success("Demo batches ready."); st.rerun()
    st.caption("Decision support only. Only laboratory testing can confirm contamination.")
if page=="Dashboard": dashboard()
elif page=="Register Batch": register_batch()
elif page=="Storage Log": storage_log()
elif page=="Visual Defect Check": visual_check()
elif page=="Pathogen Intelligence": pathogen_page()
elif page=="BatchTrace": batch_trace()
elif page=="Evaluation":
    st.title("Model evaluation"); st.markdown('<div class="warning">Models trained on synthetic data: demonstration only.</div>',unsafe_allow_html=True)
    m=ensure_models(); a,b,c=st.columns(3); a.metric("Risk ROC AUC",f"{m['auc']:.3f}"); b.metric("High-risk F1",f"{m['f1']:.3f}"); c.metric("Shelf-life MAE",f"{m['mae']:.2f} days")
    st.caption("Held-out 20% split of reproducible rule-generated synthetic data. Metrics are not evidence of real-world performance.")
else:
    batches=list_batches()
    if not batches: st.info("Register a batch or load the demo seed to begin.")
    else:
        batch=st.selectbox("Batch",batches,format_func=lambda x:f"{x['batch_id']} · {x['product']}")
        assess_batch(batch,page)
