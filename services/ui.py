import streamlit as st, pandas as pd, json
from datetime import datetime
from pathlib import Path
from services.db import add_batch,add_log,list_batches,get_logs,save_assessment,timeline,save_lab
from services.ml_service import assess,anomaly
ROOT=Path(__file__).resolve().parents[1]
DISCLAIMER='Decision support only. Only laboratory testing can confirm contamination.'
def batch_picker(label='Batch'):
    bs=list_batches()
    if not bs: return None
    return st.selectbox(label,bs,key=label,format_func=lambda b:f"{b['batch_id']} · {b['product']}")
def dashboard():
    st.title('MicroSafe AI 360'); bs=list_batches(); st.caption('Food safety decision support for micro food processors')
    st.markdown('<div class="warning">Models trained on synthetic data: demonstration only.</div>',unsafe_allow_html=True)
    cols=st.columns(3); cols[0].metric('Batches',len(bs)); logs=[(b,get_logs(b['batch_id'])) for b in bs]; alerts=sum(any(x['temp']>8 for x in ls) for b,ls in logs); cols[1].metric('Recent alerts',alerts); cols[2].metric('Logged batches',sum(bool(ls) for b,ls in logs))
    bands={'Low':0,'Medium':0,'High':0}
    if bs:
        from services.ml_service import assess
        for b,ls in logs: bands[assess(b,ls)['band']]+=1
    st.subheader('Batches by predicted risk band'); st.bar_chart(pd.DataFrame({'Batches':bands}))
    st.subheader('Recent alerts')
    for b,ls in logs:
        if any(x['temp']>8 for x in ls): st.warning(f"{b['batch_id']} · storage reading exceeded 8 °C")
    if not bs: st.info('Use “Load demo seed batches” in the sidebar to explore the main demo batch.')
def register_batch():
    st.title('Register Batch')
    with st.form('register'):
        a,b=st.columns(2); product=a.selectbox('Product',['Apple','Banana']); quantity=b.number_input('Quantity (kg)',min_value=.1,value=10.0); packed=st.datetime_input('Packed time',value=datetime.now()); ph=a.number_input('pH',min_value=0.,max_value=14.,value=3.8 if product=='Apple' else 5.0); aw=b.number_input('Water activity (aw)',min_value=0.,max_value=1.,value=.97,step=.001,format='%.3f'); packaging=st.selectbox('Packaging',['Sealed','Vented','Clamshell','Other']); ok=st.form_submit_button('Register batch')
    if ok: st.success(f"Registered {add_batch(product,quantity,packed,ph,aw,packaging)}")
def storage_log():
    st.title('Storage Log'); batch=batch_picker()
    if not batch:return
    with st.expander('Manual entry',expanded=True):
        with st.form('log'):
            at=st.datetime_input('Reading time',value=datetime.now()); temp=st.number_input('Temperature (°C)',value=4.0); hum=st.number_input('Humidity (%)',min_value=0.,max_value=100.,value=75.); ok=st.form_submit_button('Add reading')
        if ok: add_log(batch['batch_id'],at,temp,hum); st.success('Reading saved.')
    up=st.file_uploader('Or upload CSV (columns: at,temp,humidity)',type='csv')
    if up is not None and st.button('Import CSV'):
        df=pd.read_csv(up)
        for _,r in df.iterrows(): add_log(batch['batch_id'],r['at'],float(r['temp']),float(r.get('humidity',75)))
        st.success(f'Imported {len(df)} rows.')
    ls=get_logs(batch['batch_id'])
    if ls:
        df=pd.DataFrame(ls); df['at']=pd.to_datetime(df['at']); st.line_chart(df.set_index('at')['temp'],y_label='Temperature °C'); st.dataframe(df[['at','temp','humidity']],use_container_width=True)
        if (df.temp>8).any(): st.markdown('<div class="warning">Excursion: one or more readings exceeded 8 °C.</div>',unsafe_allow_html=True)
def assess_batch(batch,page):
    bid=batch['batch_id']; logs=get_logs(bid)
    if page=='Risk & Shelf Life':
        st.title('Spoilage risk + shelf life'); st.markdown('<div class="warning">Models trained on synthetic data: demonstration only.</div>',unsafe_allow_html=True); r=assess(batch,logs); st.metric('Predicted risk band',r['band']); st.metric('Risk score (synthetic model)',f"{r['probability']:.0%}"); st.metric('Estimated shelf life',f"{r['shelf_days']:.1f} days"); st.write('Top drivers: '+', '.join(r['drivers'])); st.caption('Predicted · synthetic-data demonstration model; not validated for food release decisions.'); save_assessment(bid,'ML assessment',r)
    elif page=='Anomaly Detection':
        st.title('Storage anomaly detection'); unusual,reason=anomaly(logs); (st.warning if unusual else st.success)(('Unusual storage profile: ' if unusual else 'No anomaly flag: ')+reason); st.caption('Predicted · Isolation Forest on temperature summary features.'); save_assessment(bid,'Anomaly assessment',{'flag':unusual,'reason':reason})
    else:
        st.title('Integrated batch summary'); r=assess(batch,logs); unusual,reason=anomaly(logs); growth=growth_status(batch,logs)
        defect=st.select_slider('Visual defect grade (0–4)',options=[0,1,2,3,4],value=0); lab=st.selectbox('Optional lab result to record',['Not entered','Negative','Positive','Pending']); organism=st.selectbox('Organism',['Listeria monocytogenes','Salmonella enterica','E. coli O157:H7'])
        if lab!='Not entered' and st.button('Save lab result'): save_lab(bid,organism,lab); st.success('Lab result recorded.')
        st.subheader(f"{bid} · {batch['product']}"); st.write(f"Risk: **{r['band']}** — Predicted | Shelf life: {r['shelf_days']:.1f} days — Predicted"); st.write(f"Storage anomaly: **{'Flagged' if unusual else 'Not flagged'}** — Predicted ({reason})"); st.write(f"Growth conditions: **{growth['status']}** — Database-informed ({growth['rule']})"); st.write(f"Visual grade: **{defect}/4** — Predicted, visual quality only"); st.write('Actions:')
        actions=['Chill to 5 °C or below and keep cold.','Sell within 48 hours while the model is unvalidated.']
        if defect>=3: actions.append('Discard batch with severe visible defects.')
        if unusual: actions.append('Review the cold chain and investigate the temperature excursion.')
        actions.append('Send a representative sample for laboratory testing if contamination is a concern.')
        for x in actions[:5]: st.write('• '+x)
        st.error(DISCLAIMER)
        save_assessment(bid,'Integrated summary',{'risk_band':r['band'],'anomaly':unusual,'defect_grade':defect,'growth':growth,'actions':actions[:5]})
def growth_status(batch,logs):
    profiles=json.loads((ROOT/'data'/'growth_profiles.json').read_text()); max_t=max([x['temp'] for x in logs] or [4]); vals=[batch['ph'],batch['aw']]
    if any(p['temperature_min_c']=='TO_VERIFY' for p in profiles): return {'status':'Borderline / unassessed','rule':'Growth thresholds are marked TO_VERIFY; no organism-specific conclusion is made.'}
    return {'status':'Restrictive','rule':'Placeholder rule'}
def pathogen_page():
    st.title('Pathogen Intelligence'); st.caption('Taxonomy/marker cache is optional and fetched only by running the helper script. Growth-profile values are deliberately TO_VERIFY pending source review.')
    pf=json.loads((ROOT/'data'/'growth_profiles.json').read_text()); st.dataframe(pd.DataFrame(pf),use_container_width=True)
    cache=ROOT/'data'/'pathogen_cache.json'
    if cache.exists(): st.json(json.loads(cache.read_text()))
    else: st.info('No cached NCBI records. App is operating offline. Set BIO_EMAIL and run: python -m bio.fetch_pathogens')
    st.warning('Rule-based status compares only verified envelopes. This page never estimates pathogen presence.')
def visual_check():
    st.title('Visual Defect Check'); st.caption('Visual quality only — this does not detect microbes.')
    image=st.file_uploader('Upload apple or banana photo',type=['png','jpg','jpeg'])
    if image: st.image(image,width=360)
    checkpoint=ROOT/'ml'/'vision_mobilenetv2.pt'
    if checkpoint.exists() and image:
        try:
            import torch
            from torch import nn
            from torchvision import models,transforms
            from PIL import Image
            saved=torch.load(checkpoint,map_location='cpu',weights_only=False); classes=saved['classes']; model=models.mobilenet_v2(weights=None); model.classifier[1]=nn.Linear(model.last_channel,len(classes)); model.load_state_dict(saved['state_dict']); model.eval()
            tf=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])]); x=tf(Image.open(image).convert('RGB')).unsqueeze(0)
            with torch.no_grad(): probs=torch.softmax(model(x)[0],dim=0).numpy()
            rotten=[i for i,c in enumerate(classes) if 'rotten' in c.lower()]; fresh=[i for i,c in enumerate(classes) if 'fresh' in c.lower()]
            if rotten and fresh:
                rp=float(probs[rotten].sum()); grade=round(rp*4); st.metric('Rotten probability (visual only)',f'{rp:.0%}'); st.write(f'Fresh probability (visual only): {float(probs[fresh].sum()):.0%}'); st.write(f'Visual defect grade: **{grade}/4** (Predicted)')
            else: st.warning('Checkpoint class labels must include “fresh” and “rotten”. Use manual grading below.')
        except Exception as e: st.warning(f'Vision model could not load ({e}). Use manual grading below.')
    elif not checkpoint.exists(): st.info('Fine-tuned MobileNetV2 weights are missing. Upload an image and use the manual grade fallback; the demo will continue safely.')
    grade=st.select_slider('Manual visual defect grade (0 = none, 4 = severe)',options=[0,1,2,3,4],value=0); st.write(f'Fallback grade: **{grade}/4** (manual, visual quality only; not microbial evidence)')
def batch_trace():
    st.title('BatchTrace'); batch=batch_picker('Trace batch')
    if not batch:return
    events=timeline(batch['batch_id']); st.subheader(f"History · {batch['batch_id']}")
    for e in events: st.write(f"**{e['created_at']} · {e['kind']}** — {e['detail']}")
    report=f"<html><head><meta charset='utf-8'><title>{batch['batch_id']} report</title></head><body><h1>MicroSafe AI 360 · {batch['batch_id']}</h1><p>{DISCLAIMER}</p><h2>Batch registration</h2><pre>{json.dumps(batch,indent=2)}</pre><h2>Timeline</h2><ul>"+''.join(f"<li>{e['created_at']} · {e['kind']} — {e['detail']}</li>" for e in events)+"</ul></body></html>"
    st.download_button('Download HTML report',report,file_name=f"{batch['batch_id']}-report.html",mime='text/html')
