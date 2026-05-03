"""
similarity.py - Name and path similarity backends.

Features:
- TF-IDF character and path token similarity
- Optional RapidFuzz edit similarity
- Optional sentence-transformer embeddings
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def clean_names(names):
    return [
        "" if x is None or (isinstance(x, float) and np.isnan(x)) else str(x)
        for x in names
    ]


class NameSimilarity:
    def __init__(
        self,
        method="tfidf",
        model_name="all-MiniLM-L6-v2",
        ngram_range=(2, 4),
        tokenizer="char",
        max_features=30000,
    ):
        self.method = method
        self.model = None
        self.tokenizer = tokenizer
        self.ngram_range = ngram_range
        self.max_features = max_features

        if method == "bert":
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "The 'bert' backend requires sentence-transformers. "
                    "Use --name-sim tfidf or install the optional dependency."
                ) from exc

            self.model = SentenceTransformer(model_name)
        elif method == "tfidf":
            analyzer = "char_wb" if tokenizer == "char" else self._path_tokenizer
            self.vectorizer = TfidfVectorizer(
                analyzer=analyzer, ngram_range=ngram_range, max_features=max_features
            )

    def compute(self, names1, names2, mask=None):
        if self.method == "rapidfuzz":
            return self._rapidfuzz_matrix(names1, names2, mask)
        elif self.method == "tfidf":
            return self._tfidf_sparse_matrix(names1, names2, mask)
        elif self.method == "bert":
            return self._bert_matrix(names1, names2, mask)
        else:
            raise ValueError("Unsupported method: " + self.method)

    def _rapidfuzz_matrix(self, names1, names2, mask):
        try:
            from rapidfuzz.distance import Levenshtein
        except ImportError as exc:
            raise ImportError(
                "The 'rapidfuzz' backend requires rapidfuzz. "
                "Use --name-sim tfidf or install the optional dependency."
            ) from exc

        sim_matrix = np.zeros((len(names1), len(names2)), dtype=np.float32)
        for i, name1 in enumerate(names1):
            for j, name2 in enumerate(names2):
                if mask is None or mask[i][j]:
                    sim_matrix[i][j] = Levenshtein.normalized_similarity(
                        str(name1), str(name2)
                    )
        return sim_matrix.astype(np.float16)

    def _tfidf_sparse_matrix(self, names1, names2, mask):
        names1 = clean_names(names1)
        names2 = clean_names(names2)
        all_names = names1 + names2

        print("[INFO] Vectorizing with TF-IDF (sparse)...")
        tfidf_matrix = self.vectorizer.fit_transform(all_names)
        n1 = len(names1)
        tfidf1 = tfidf_matrix[:n1]
        tfidf2 = tfidf_matrix[n1:]

        print("[INFO] Computing sparse cosine similarity...")
        sim_sparse = cosine_similarity(tfidf1, tfidf2, dense_output=False)
        sim_dense = sim_sparse.toarray()

        if mask is not None:
            sim_dense = np.where(mask, sim_dense, 0.0)

        return sim_dense.astype(np.float16)

    def _bert_matrix(self, names1, names2, mask):
        embeddings1 = self.model.encode(
            names1, convert_to_tensor=True, show_progress_bar=True
        )
        embeddings2 = self.model.encode(
            names2, convert_to_tensor=True, show_progress_bar=True
        )
        sim_matrix = cosine_similarity(
            embeddings1.cpu().numpy(), embeddings2.cpu().numpy()
        )
        if mask is not None:
            sim_matrix = np.where(mask, sim_matrix, 0.0)
        return sim_matrix.astype(np.float16)

    def _path_tokenizer(self, string):
        return string.replace("\\", "/").split("/")
