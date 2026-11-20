import numpy as np, pandas as pd, json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, IsolationForest
from sklearn.metrics import roc_auc_score, f1_score, mean_absolute_error
from services.db import conn
ROOT=Path(__file__).resolve().parents[1]; CACHE=ROOT/"ml"/"metrics.json"
FEATURES=['product_banana','ph','aw','max_temp','hours_above_8','duration_h','quantity']
def synthetic_data(n=3000,seed=36):
    rng=np.random.default_rng(seed); banana=rng.integers(0,2,n); ph=np.where(banana,rng.normal(5,.35,n),rng.normal(3.8,.25,n)); aw=np.clip(rng.normal(.975,.012,n),.92,1); mx=np.clip(rng.normal(7,4,n),1,22); dur=rng.uniform(2,120,n); above=np.maximum(0,mx-8)*rng.uniform(0,.7,n)*dur/3; qty=rng.uniform(1,100,n)
    # Demonstration kinetic rule only: thermal rate doubles per 10 C above 5 C; accumulated time above 8 C adds dose.
    dose=dur*2**((mx-5)/10)+above*3+np.maximum(0,aw-.96)*100+np.maximum(0,ph-4.2)*10; prob=1/(1+np.exp(-(dose-110)/35)); y=(rng.random(n)<prob).astype(int); shelf=np.clip(8-dose/70+rng.normal(0,.5,n),.25,10)
    return pd.DataFrame({'product_banana':banana,'ph':ph,'aw':aw,'max_temp':mx,'hours_above_8':above,'duration_h':dur,'quantity':qty}),y,shelf
def train():
    X,y,s=synthetic_data(); xa,xb,ya,yb,sa,sb=train_test_split(X,y,s,test_size=.2,random_state=36,stratify=y); clf=RandomForestClassifier(n_estimators=120,min_samples_leaf=3,class_weight='balanced',random_state=36,n_jobs=-1).fit(xa,ya); reg=GradientBoostingRegressor(n_estimators=100,max_depth=2,random_state=36).fit(xa,sa)
    return clf,reg,{'auc':roc_auc_score(yb,clf.predict_proba(xb)[:,1]),'f1':f1_score(yb,clf.predict(xb)),'mae':mean_absolute_error(sb,reg.predict(xb))}
def ensure_models():
    X,y,s=synthetic_data()
    with conn() as c:
        if c.execute('SELECT COUNT(*) FROM synthetic_examples').fetchone()[0]==0:
            c.executemany('INSERT INTO synthetic_examples(features,label,shelf_days,is_synthetic) VALUES(?,?,?,1)',[(json.dumps(row),int(label),float(days)) for row,label,days in zip(X.to_dict('records'),y,s)])
    if CACHE.exists(): return json.loads(CACHE.read_text())
    _,_,m=train(); CACHE.parent.mkdir(exist_ok=True); CACHE.write_text(json.dumps(m)); return m
def assess(batch,logs):
    clf,reg,_=train(); ts=[x['temp'] for x in logs] or [4]; row=pd.DataFrame([{'product_banana':int(batch['product']=='Banana'),'ph':batch['ph'],'aw':batch['aw'],'max_temp':max(ts),'hours_above_8':2*sum(t>8 for t in ts),'duration_h':max(1,len(logs)*2),'quantity':batch['quantity']}])[FEATURES]
    p=float(clf.predict_proba(row)[0,1]); band='Low' if p<.33 else 'Medium' if p<.67 else 'High'
    try:
        import shap
        sv=shap.TreeExplainer(clf)(row).values
        impacts=sv[0,:,1] if sv.ndim==3 else sv[0]
        names={'max_temp':'Warmest logged temperature','hours_above_8':'Time above 8 °C','duration_h':'Elapsed storage time','ph':'Product pH','aw':'Water activity','product_banana':'Product type','quantity':'Batch quantity'}
        drivers=[names[FEATURES[i]] for i in np.argsort(np.abs(impacts))[::-1][:3]]
    except Exception:
        drivers=['Temperature exposure','Elapsed storage time','Product pH']
    return {'probability':p,'band':band,'shelf_days':max(.1,float(reg.predict(row)[0])),'drivers':drivers,'driver_method':'SHAP TreeExplainer' if 'shap' in locals() else 'Top model drivers (SHAP unavailable)'}
def anomaly(logs):
    if len(logs)<3: return False,'Need at least 3 readings for a meaningful anomaly check.'
    t=np.array([x['temp'] for x in logs]); f=np.array([[max(t),sum(max(0,x-8) for x in t),np.max(np.abs(np.diff(t)))]]); ref=np.array([[4,0,.3],[5,0,.5],[6,0,1],[7,0,1.5],[9,1,2],[11,4,3],[4,0,.2],[6,0,.8]])
    unusual=IsolationForest(contamination=.2,random_state=36).fit(ref).predict(f)[0]<0; why=[]
    if max(t)>8: why.append(f"peak was {max(t):g} °C (>8 °C)")
    if f[0,1]>0: why.append('exposure accumulated above 8 °C')
    return unusual,'; '.join(why) if unusual else 'Profile is within the small demo reference range.'
