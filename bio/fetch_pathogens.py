"""Optional online taxonomy/marker fetch. Requires BIO_EMAIL and Biopython."""
import os,json
from pathlib import Path
from Bio import Entrez, SeqIO
OUT=Path(__file__).resolve().parents[1]/'data'/'pathogen_cache.json'
TAXA={'Listeria monocytogenes':'1639','Salmonella enterica':'28901','Escherichia coli O157:H7':'83334'}
def main(fetch_sequences=False):
    Entrez.email=os.environ['BIO_EMAIL']; result={}
    for name,taxid in TAXA.items():
        with Entrez.efetch(db='taxonomy',id=taxid,retmode='xml') as h: info=Entrez.read(h)[0]
        item={'taxid':taxid,'scientific_name':info.get('ScientificName'),'lineage':info.get('Lineage'),'markers':[]}
        if fetch_sequences:
            for marker in {'Listeria monocytogenes':['hly'],'Salmonella enterica':['invA'],'Escherichia coli O157:H7':['stx']}[name]:
                with Entrez.esearch(db='nucleotide',term=f'{name}[Organism] AND {marker}[Gene]',retmax=1) as h: ids=Entrez.read(h)['IdList']
                if ids:
                    with Entrez.efetch(db='nucleotide',id=ids[0],rettype='fasta',retmode='text') as h: seq=SeqIO.read(h,'fasta')
                    s=str(seq.seq).upper(); item['markers'].append({'gene':marker,'accession':seq.id,'length':len(s),'gc_percent':round(100*(s.count('G')+s.count('C'))/max(1,len(s)),2)})
        result[name]=item
    OUT.write_text(json.dumps(result,indent=2)); print(OUT)
if __name__=='__main__': main('--sequences' in os.sys.argv)
