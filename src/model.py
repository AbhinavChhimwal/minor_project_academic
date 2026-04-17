import torch.nn as nn
import torch.nn.functional as F


class SiameseNetwork(nn.Module):
    def __init__(self, vocab_size: int, embed_dim: int = 128, hidden_dim: int = 128):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.encoder = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.proj = nn.Linear(hidden_dim * 2, hidden_dim)

    def encode(self, x):
        emb = self.embedding(x)
        out, _ = self.encoder(emb)
        pooled = out.mean(dim=1)
        vec = self.proj(pooled)
        return F.normalize(vec, p=2, dim=1)

    def forward(self, x1, x2):
        return self.encode(x1), self.encode(x2)


class ContrastiveLoss(nn.Module):
    def __init__(self, margin=1.0):
        super().__init__()
        self.margin = margin

    def forward(self, out1, out2, label):
        dist = F.pairwise_distance(out1, out2)
        loss = label * (dist ** 2) + (1 - label) * (F.relu(self.margin - dist) ** 2)
        return loss.mean()
