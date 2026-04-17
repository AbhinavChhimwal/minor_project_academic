from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'
MODELS_DIR = ROOT / 'models'

TRAIN_FILE = RAW_DIR / 'msr_paraphrase_train.txt'
TEST_FILE = RAW_DIR / 'msr_paraphrase_test.txt'

MODEL_PATH = MODELS_DIR / 'plagiarism_model.pth'
VOCAB_PATH = MODELS_DIR / 'vocab.json'
DB_PATH = DATA_DIR / 'plagiarism.sqlite3'
FAISS_PATH = DATA_DIR / 'faiss.index'

MAX_LEN = 40
EMBED_DIM = 128
HIDDEN_DIM = 128
BATCH_SIZE = 32
EPOCHS = 5
LR = 1e-3
MARGIN = 1.0
