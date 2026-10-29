"""Part D tasks 1-4: chunking, TF-IDF retrieval, grounded answer(), evaluation."""
import glob, os, sys
import pandas as pd
sys.path.insert(0, os.getcwd())
import mock_llm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

POLICY_DIR = os.path.join("data", "policies")

def chunk_words(words, size=40, overlap=10):
    """First chunk = words[0:size]; next starts size-overlap later; stop after the first chunk whose end >= len(words)."""
    step, chunks, start = size - overlap, [], 0
    while True:
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words): break
        start += step
    return chunks

def load_chunks(size=40, overlap=10, folder=POLICY_DIR):
    out = []
    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        words = open(path, encoding="utf-8").read().split()
        for i, ch in enumerate(chunk_words(words, size, overlap)):
            out.append({"source": os.path.basename(path), "chunk_id": i, "text": ch})
    return out

class Index:
    def __init__(self, size=40, overlap=10):
        self.chunks = load_chunks(size, overlap)
        self.vec = TfidfVectorizer()
        self.matrix = self.vec.fit_transform([c["text"] for c in self.chunks])   # fitted on chunk texts only
    def retrieve(self, query, k=3):
        sims = cosine_similarity(self.vec.transform([query]), self.matrix)[0]   # same fitted vectoriser for the query
        top = sims.argsort()[::-1][:k]
        return [{"source": self.chunks[i]["source"], "score": float(sims[i]), "text": self.chunks[i]["text"]} for i in top]

_default = None
def default_index():
    global _default
    if _default is None: _default = Index(40, 10)
    return _default
def retrieve(query, k=3):
    return default_index().retrieve(query, k)

SYSTEM = ("You are a POLICY ASSISTANT. Answer only from the supplied context. "
          "If the answer is not in the context, say that you could not find the information.")
def answer(question, index=None):
    hits = (index or default_index()).retrieve(question, 3)
    context = "\n".join(f"[{h['source']}]\n{h['text']}" for h in hits)
    user = f"CONTEXT:\n{context}\nQUESTION:\n{question}"
    resp = mock_llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])
    return resp.choices[0].message.content, [h["source"] for h in hits]

def evaluate(index):
    ev = pd.read_csv("data/raw/policy_eval.csv", keep_default_na=False)
    doc_hit = fact_hit = fb = n_ans = n_un = 0; fails = []
    for r in ev.itertuples(index=False):
        text, srcs = answer(r.question, index)
        if r.expected_doc == "NONE":
            n_un += 1; ok = text.startswith("I could not find"); fb += ok
            if not ok: fails.append((r.question, "unanswerable question did not get the fallback", text))
        else:
            n_ans += 1; d = r.expected_doc in srcs; f = r.expected_fact in text
            doc_hit += d; fact_hit += f
            if not (d and f): fails.append((r.question, f"doc_in_top3={d}, fact_in_answer={f}", text))
    return dict(n_chunks=len(index.chunks), doc=f"{doc_hit}/{n_ans}", fact=f"{fact_hit}/{n_ans}", fallback=f"{fb}/{n_un}"), fails

if __name__ == "__main__":
    idx = Index()
    from collections import Counter
    print(len(idx.chunks), Counter(c["source"] for c in idx.chunks))
    print([h["source"] for h in retrieve("refund policy late delivery")])
    print(evaluate(idx)); r0, f0 = evaluate(Index(40, 0)); print(r0); [print(x) for x in f0]
