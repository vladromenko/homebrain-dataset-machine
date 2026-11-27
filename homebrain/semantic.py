"""Compact BGE ONNX embeddings, CPU only, combined with SQLite FTS."""
import threading
from pathlib import Path
import numpy as np


class Encoder:
    def __init__(self, directory):
        self.directory,self.session,self.tokenizer = Path(directory),None,None
        self.lock = threading.Lock()

    def encode(self, texts):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        with self.lock:
            if self.session is None:
                options = ort.SessionOptions()
                options.intra_op_num_threads = 1
                options.inter_op_num_threads = 1
                self.session = ort.InferenceSession(str(self.directory/"model_quantized.onnx"),options,providers=["CPUExecutionProvider"])
                self.tokenizer = Tokenizer.from_file(str(self.directory/"tokenizer.json"))
                self.tokenizer.enable_truncation(max_length=384)
                self.tokenizer.enable_padding()
            tokens = self.tokenizer.encode_batch(texts)
            ids = np.asarray([t.ids for t in tokens],np.int64)
            mask = np.asarray([t.attention_mask for t in tokens],np.int64)
            inputs = {"input_ids":ids,"attention_mask":mask,"token_type_ids":np.zeros_like(ids)}
            wanted = {i.name for i in self.session.get_inputs()}
            output = self.session.run(None,{k:v for k,v in inputs.items() if k in wanted})[0]
            vectors = output[:,0,:] if output.ndim==3 else output
            return vectors/np.maximum(np.linalg.norm(vectors,axis=1,keepdims=True),1e-10)


class Hybrid:
    def __init__(self, store, encoder):
        self.store,self.encoder = store,encoder
        with store.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS vectors(rowid INTEGER PRIMARY KEY,hash TEXT,vector BLOB)")

    def index(self):
        with self.store.db() as db:
            db.execute("DELETE FROM vectors WHERE rowid NOT IN (SELECT rowid FROM documents)")
            rows = db.execute("SELECT d.rowid,d.text,d.hash FROM documents d WHERE NOT EXISTS (SELECT 1 FROM vectors v WHERE v.rowid=d.rowid AND v.hash=d.hash)").fetchall()
        for offset in range(0,len(rows),12):
            batch = rows[offset:offset+12]
            vectors = self.encoder.encode([r["text"] for r in batch])
            with self.store.db() as db:
                for row,vector in zip(batch,vectors):
                    db.execute("INSERT OR REPLACE INTO vectors VALUES(?,?,?)", (row["rowid"],row["hash"],vector.astype(np.float32).tobytes()))

    def search(self, query):
        lexical = self.store.search(query)
        with self.store.db() as db:
            rows = db.execute("SELECT d.*,d.rowid,v.vector FROM documents d JOIN vectors v ON d.rowid=v.rowid AND d.hash=v.hash").fetchall()
        if not rows:
            return lexical
        vector = self.encoder.encode(["Represent this sentence for searching relevant passages: "+query])[0]
        ranked = sorted(rows,key=lambda r:float(np.frombuffer(r["vector"],np.float32)@vector),reverse=True)[:4]
        scores = {}
        for listing in (lexical,[{k:r[k] for k in r.keys() if k not in ("vector","rowid")} for r in ranked]):
            for rank,item in enumerate(listing):
                key = (item["path"],item["text"])
                previous = scores.get(key,(0,item))[0]
                scores[key] = (previous+1/(60+rank),item)
        result = {}
        for score,item in sorted(scores.values(),key=lambda r:r[0],reverse=True):
            if item["path"] not in result:
                result[item["path"]] = item
        return list(result.values())[:4]
