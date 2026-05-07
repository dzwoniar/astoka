"""Selective extract from SamurAIGPT/AI-Youtube-Shorts-Generator (MIT).

Source: https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator
License: MIT (see LICENSE file in this directory)
Attribution: ATTRIBUTION.md

We pull only:
- chunking.py     — Long-Video Aware 20-min/60s overlap (PRD HIGH-04, RESEARCH §6)
- dedupe.py       — IoU-based Non-Maximum Suppression (PRD HIGH-07, RESEARCH §5)
- prompts/        — base prompt templates for highlight reranking (RESEARCH §4)

These modules are intentionally minimal Python — extracted/rewritten from the upstream
repo to avoid pulling its full dependency stack (it includes its own pipeline runner,
audio extraction, etc., which we replace with our own per-sprint code).
"""
