import os
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim import lr_scheduler
from torch.autograd import Variable
from util import *
import time
import copy

parser = argparse.ArgumentParser()

parser.add_argument('--hidden_dim', type = int, default = 10, help = 'num of hidden nodes')
parser.add_argument('--num_epoch', type = int, default = 20, help = 'num of epochs')
parser.add_argument('--learning_rate', type = float, default = 1e-2, help = 'learning rate')
parser.add_argument('--batch_size', type = int, default = 32, help = 'batch size')
parser.add_argument('--momentum', type = float, default = 0.9, help = 'momentum')

args = parser.parse_args()

class TextClassifier(nn.Module):
    def __init__(self,vocab_size,hidden_dim,num_class):
        super(TextClassifier,self).__init__()
        #self.embedding = nn.EmbeddingBag(vocab_size, hidden_dim, sparse=True)
        self.input_layer = nn.Linear(vocab_size,hidden_dim)
        self.hidden_layer = nn.Linear(hidden_dim, num_class)
        self.output_layer = nn.Softmax(dim=1)
        
    def forward(self,text):
        embedded = self.input_layer(text)
        output = self.hidden_layer(embedded)
        return self.output_layer(output)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
HIDDEN_DIM = args.hidden_dim
NUM_CLASS = len(set(dataDict['test_Y']))
NUM_EPOCH = args.num_epoch
LEARN_RATE = args.learning_rate
BATCH_SIZE = args.batch_size

model = TextClassifier(VOCAB_SIZE,HIDDEN_DIM,NUM_CLASS).to(device)
criterion = nn.NLLLoss()
optimizer = torch.optim.SGD(model.parameters(), lr=LEARN_RATE, momentum = args.momentum)
scheduler = lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

dataloaders = {x: DataLoader(dataset=TrainDataset(), batch_size=32, shuffle=True, num_workers=2) for x in ['train','val']}
#test_lodaer  = DataLoader(dataset=TestDataset(), batch_size=BATCH_SIZE, shuffle=True, num_workers=2)

def train_model(model, criterion, optimizer, scheduler, num_epochs):
    since = time.time()
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0 

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch+1, num_epochs))
        print('-' * 10)

        for phase in ['train','val']:
            if phase == 'train':
                
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0
            count = 0

            for inputs,labels in dataloaders[phase]:
                count += len(inputs)
                inputs,labels = inputs.to(device),labels.to(device)
                inputs,labels = Variable(inputs.float()), Variable(labels)
                
                optimizer.zero_grad()
                
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs.float())
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)
                    
                    if phase =='train':
                        loss.backward()
                        optimizer.step()
                        
                
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                            
            epoch_loss = running_loss / count
            epoch_acc = running_corrects.double() / count
            
            print('{} Loss: {:.4f} Acc: {:.4f}'.format(
                phase, epoch_loss, epoch_acc))
            
            #scheduler.step()

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())
                
        print()
    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))

    # 가장 나은 모델 가중치를 불러옴
    model.load_state_dict(best_model_wts)
    return model


best_model = train_model(model, criterion, optimizer, scheduler, NUM_EPOCH)
torch.save(model.state_dict(), 'model/model.pth')

