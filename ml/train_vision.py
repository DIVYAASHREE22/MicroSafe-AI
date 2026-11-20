"""Optional MobileNetV2 fine-tuning on Kaggle Fruits Fresh and Rotten.

Expected ImageFolder layout: apple_fresh/, apple_rotten/, banana_fresh/,
banana_rotten/ (each containing images). Dataset is not redistributed.
"""
import argparse
from pathlib import Path
import torch
from torch import nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models

def main():
    p=argparse.ArgumentParser(); p.add_argument('dataset',type=Path); p.add_argument('--epochs',type=int,default=4); a=p.parse_args()
    tf=transforms.Compose([transforms.Resize((224,224)),transforms.RandomHorizontalFlip(),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    ds=datasets.ImageFolder(a.dataset,transform=tf); n=int(.8*len(ds)); train,val=random_split(ds,[n,len(ds)-n]); dl=DataLoader(train,batch_size=32,shuffle=True); device='cuda' if torch.cuda.is_available() else 'cpu'
    net=models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1); net.classifier[1]=nn.Linear(net.last_channel,len(ds.classes)); net.to(device); opt=torch.optim.Adam(net.parameters(),lr=1e-4); loss=nn.CrossEntropyLoss()
    for epoch in range(a.epochs):
        net.train(); total=0
        for x,y in dl: x,y=x.to(device),y.to(device); opt.zero_grad(); z=net(x); l=loss(z,y); l.backward(); opt.step(); total+=l.item()
        print(f'epoch {epoch+1}: loss={total/max(1,len(dl)):.4f}')
    out=Path(__file__).with_name('vision_mobilenetv2.pt'); torch.save({'state_dict':net.cpu().state_dict(),'classes':ds.classes},out); print(f'Saved {out}; class mapping: {ds.classes}')
if __name__=='__main__': main()
