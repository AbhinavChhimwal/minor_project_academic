import matplotlib.pyplot as plt
import torch
from torch.utils.data import DataLoader

from .config import (
    BATCH_SIZE,
    EPOCHS,
    EMBED_DIM,
    HIDDEN_DIM,
    LR,
    MARGIN,
    MODEL_PATH,
    MODELS_DIR,
    TRAIN_FILE,
    VOCAB_PATH,
)
from .data_loader import MRPCDataset, save_vocab
from .model import ContrastiveLoss, SiameseNetwork


def train():
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(f'MRPC train file not found: {TRAIN_FILE}')

    dataset = MRPCDataset(TRAIN_FILE)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    save_vocab(dataset.vocab, VOCAB_PATH)

    model = SiameseNetwork(
        vocab_size=len(dataset.vocab),
        embed_dim=EMBED_DIM,
        hidden_dim=HIDDEN_DIM,
    )
    criterion = ContrastiveLoss(margin=MARGIN)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    losses = []
    model.train()
    for epoch in range(EPOCHS):
        running = 0.0
        for s1, s2, y in loader:
            o1, o2 = model(s1, s2)
            loss = criterion(o1, o2, y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            running += float(loss.item())

        avg = running / max(1, len(loader))
        losses.append(avg)
        print(f'Epoch {epoch + 1}/{EPOCHS} - loss: {avg:.4f}')

    torch.save(model.state_dict(), MODEL_PATH)
    print(f'Model saved to: {MODEL_PATH}')

    plt.figure(figsize=(7, 4))
    plt.plot(losses, marker='o')
    plt.title('Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(MODELS_DIR / 'training_loss.png')


if __name__ == '__main__':
    train()
