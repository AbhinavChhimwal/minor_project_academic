import json
from collections import Counter

import pandas as pd
import torch
from torch.utils.data import Dataset

from .config import MAX_LEN


def simple_tokenize(text: str):
    return text.lower().strip().split()


def build_vocab(sentences, min_freq=1):
    counter = Counter()
    for sentence in sentences:
        counter.update(simple_tokenize(str(sentence)))

    vocab = {'<pad>': 0, '<unk>': 1}
    for token, freq in counter.items():
        if freq >= min_freq:
            vocab[token] = len(vocab)
    return vocab


def encode(text: str, vocab, max_len=MAX_LEN):
    tokens = simple_tokenize(str(text))
    ids = [vocab.get(tok, vocab['<unk>']) for tok in tokens[:max_len]]
    if len(ids) < max_len:
        ids.extend([vocab['<pad>']] * (max_len - len(ids)))
    return torch.tensor(ids, dtype=torch.long)


class MRPCDataset(Dataset):
    def __init__(self, file_path, vocab=None, max_len=MAX_LEN):
        self.df = pd.read_csv(file_path, sep='	')
        self.max_len = max_len

        self.s1_col = 'string1' if 'string1' in self.df.columns else '#1 String'
        self.s2_col = 'string2' if 'string2' in self.df.columns else '#2 String'
        self.label_col = 'Quality'

        if vocab is None:
            all_text = self.df[self.s1_col].tolist() + self.df[self.s2_col].tolist()
            self.vocab = build_vocab(all_text)
        else:
            self.vocab = vocab

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        s1 = encode(row[self.s1_col], self.vocab, self.max_len)
        s2 = encode(row[self.s2_col], self.vocab, self.max_len)
        label = torch.tensor(float(row[self.label_col]), dtype=torch.float32)
        return s1, s2, label


def save_vocab(vocab, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, indent=2)


def load_vocab(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
