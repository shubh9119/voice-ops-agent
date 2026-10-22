"""Unit tests for agent worker latency computation."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from voiceagent.latency import compute_turn_metrics


def test_compute_turn_metrics_valid():
    raw_metrics = {
        "transcription_delay": 0.185,
        "end_of_turn_delay": 0.120,
        "llm_node_ttft": 0.095,
        "tts_node_ttfb": 0.145,
        "e2e_latency": 0.545,
    }

    result = compute_turn_metrics(raw_metrics, turn_idx=3)

    assert result["turn_idx"] == 3
    assert result["transcription_delay_ms"] == 185.0
    assert result["end_of_turn_delay_ms"] == 120.0
    assert result["llm_ttft_ms"] == 95.0
    assert result["tts_ttfb_ms"] == 145.0
    assert result["e2e_ms"] == 545.0


def test_compute_turn_metrics_missing():
    raw_metrics = {}

    result = compute_turn_metrics(raw_metrics, turn_idx=0)

    assert result["turn_idx"] == 0
    assert result["transcription_delay_ms"] == 0.0
    assert result["end_of_turn_delay_ms"] == 0.0
    assert result["llm_ttft_ms"] == 0.0
    assert result["tts_ttfb_ms"] == 0.0
    assert result["e2e_ms"] == 0.0
