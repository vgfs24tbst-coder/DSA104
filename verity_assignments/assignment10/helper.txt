import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModel
from torch.optim import AdamW
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit.Chem import MACCSkeys


class ESOLDataset(Dataset):
    def __init__(self, df, tokenizer, max_length=128): ### initiation fct for this class. We can call it with the params df and tokeniser, max_length default 128
        self.df = df
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        smiles = self.df.iloc[idx]["SMILES"]
        label = self.df.iloc[idx]["LogKOC"]

        enc = self.tokenizer(
            smiles,
            truncation=True,
            padding="max_length", ### needed for converting to fixed size tensor, bc batch inputs can be diff length -> model can follow same pattern
            max_length=self.max_length,
            return_tensors="pt" ### datatype to return : pytorach 
        )

        return {
            "input_ids": enc["input_ids"].squeeze(0), ### encode / tokenise the input ids and perfoms a dim reduction : reduce the actual output of the shape ``[N, 1]`` to ``[N]``, which is comparable to y
            "attention_mask": enc["attention_mask"].squeeze(0), ### dito but for the attention mask -> mechanism used to indicate which tokens the model should ignore when computing attention scores
            "labels": torch.tensor(label, dtype=torch.float)
        }


class chemberta_esol_regressor(nn.Module):
    def __init__(self, model_name, hidden_dim=None):
        super().__init__()

        # general encoder
        self.encoder = AutoModel.from_pretrained(model_name) ### init with our encode model of choice, set to said encoder from nthe AutoModel pack

        if hidden_dim is None:
            hidden_dim = self.encoder.config.hidden_size ### set the hidden dim to the hidden size of the model (attr.).

        # Regression head (task-specific)
        self.fc1 = nn.Linear(hidden_dim, 256) ### input is the init size of model, reduce to 256
        self.act = nn.ReLU() ### activation funct: if x <=0 -> fct(x)=0, else fct(x)=x
        self.dropout = nn.Dropout(p=0.2) 
        self.fc2 = nn.Linear(256, 1) ### output from 256 to 1 output

    def forward(self, input_ids, attention_mask): ###  forward propagation, takes inpu ids and attention mask (which tokens to process and which to ignore)
        # Encoder forward
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        # Pooling (explicit & visible)
        # Use [CLS] token representation
        cls_embedding = outputs.last_hidden_state[:, 0, :] ### Sequence of hidden-states at the output of the last layer of the model., cls embedding: save CLS token, cls:classification

        # Regression head forward
        x = self.fc1(cls_embedding)
        x = self.act(x)
        x = self.dropout(x)
        x = self.fc2(x)

        return x.squeeze(-1)
    


def evaluate(model, dataloader):
    model.eval() ### put model into evaluation mode
    preds, targets = [], []

    with torch.no_grad(): ### disable gradient tracking for evaluation
        for batch in dataloader:
            input_ids = batch["input_ids"]
            attention_mask = batch["attention_mask"] ### used to indicate which tokens the model should ignore when computing attention scores for this batch
            labels = batch["labels"]

            outputs = model(input_ids, attention_mask)
            preds.append(outputs.cpu().numpy())
            targets.append(labels.cpu().numpy())

    preds = np.concatenate(preds).tolist()
    targets = np.concatenate(targets)
    rmse = np.sqrt(mean_squared_error(targets, preds))
    r2 = r2_score(targets, preds)
    return np.array(preds), r2, rmse



def maccs_fp_from_smiles(smiles_list):
    fps = []
    valid_idx = []

    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        fp = MACCSkeys.GenMACCSKeys(mol)
        fps.append(np.array(fp))
        valid_idx.append(i)

    return np.array(fps), valid_idx

def maccs_fp_from_smiles_as_bitvectors(smiles_list):
    fps = []
    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        fp = MACCSkeys.GenMACCSKeys(mol)
        fps.append(fp)
    return fps