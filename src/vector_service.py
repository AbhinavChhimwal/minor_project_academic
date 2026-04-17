import re

import torch

from .config import EMBED_DIM, HIDDEN_DIM, MAX_LEN, MODEL_PATH, VOCAB_PATH
from .data_loader import encode, load_vocab
from .model import SiameseNetwork


def sentence_split(text: str):
    chunks = re.split(r'(?<=[.!?])\s+', text.strip())
    return [c.strip() for c in chunks if c.strip()]


class Vectorizer:
    def __init__(self):
        self.vocab = load_vocab(VOCAB_PATH)
        self.model = SiameseNetwork(
            vocab_size=len(self.vocab),
            embed_dim=EMBED_DIM,
            hidden_dim=HIDDEN_DIM,
        )
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
        self.model.eval()

    @torch.no_grad()
    def vectorize_sentence(self, sentence: str):
        x = encode(sentence, self.vocab, max_len=MAX_LEN).unsqueeze(0)
        vec = self.model.encode(x).squeeze(0).cpu().numpy().astype('float32')
        return vec

    def vectorize_text(self, text: str):
        sents = sentence_split(text)
        vectors = [self.vectorize_sentence(s) for s in sents]
        return sents, vectors
