"""FinBERT-based financial sentiment analysis with lazy model loading."""

from __future__ import annotations

from typing import Any

_model = None
_tokenizer = None


def _ensure_loaded():
    """Lazy-load the FinBERT model on first use (~420MB download, CPU-only)."""
    global _model, _tokenizer
    if _model is not None:
        return

    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    _tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    _model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
    _model.eval()


_LABELS = ["positive", "negative", "neutral"]


def score_headlines(headlines: list[str]) -> list[dict[str, Any]]:
    """Score a batch of headlines using FinBERT.

    Returns list of {text, sentiment, score, scores} dicts.
    """
    if not headlines:
        return []

    _ensure_loaded()

    import torch

    results = []
    # Process in batches of 16 to manage memory
    batch_size = 16
    for i in range(0, len(headlines), batch_size):
        batch = headlines[i : i + batch_size]
        inputs = _tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )

        with torch.no_grad():
            outputs = _model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

        for j, text in enumerate(batch):
            scores = probs[j].tolist()
            best_idx = scores.index(max(scores))
            results.append({
                "text": text,
                "sentiment": _LABELS[best_idx],
                "score": round(scores[best_idx], 4),
                "scores": {
                    "positive": round(scores[0], 4),
                    "negative": round(scores[1], 4),
                    "neutral": round(scores[2], 4),
                },
            })

    return results


def aggregate_sentiment(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate sentiment from scored headlines."""
    if not scored:
        return {"overall": "neutral", "avg_score": 0.0, "count": 0}

    pos = sum(1 for s in scored if s["sentiment"] == "positive")
    neg = sum(1 for s in scored if s["sentiment"] == "negative")
    neu = sum(1 for s in scored if s["sentiment"] == "neutral")
    total = len(scored)

    avg_positive = sum(s["scores"]["positive"] for s in scored) / total
    avg_negative = sum(s["scores"]["negative"] for s in scored) / total

    net_score = avg_positive - avg_negative

    if net_score > 0.15:
        overall = "bullish"
    elif net_score < -0.15:
        overall = "bearish"
    else:
        overall = "neutral"

    return {
        "overall": overall,
        "net_score": round(net_score, 4),
        "positive_count": pos,
        "negative_count": neg,
        "neutral_count": neu,
        "total": total,
    }
