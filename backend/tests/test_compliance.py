"""Unit tests for compliance rules."""

from datetime import datetime, timedelta, timezone
import pytest

from app.compliance.deterministic import (
    check_no_operator_mention,
    check_recording_disclosure,
)


def test_recording_disclosure_pass_early():
    call_start = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    turns = [
        {
            "idx": 0,
            "speaker": "agent",
            "text": "Hello, thank you for calling Acme Support. Please note that this call is recorded for quality purposes.",
            "started_at": call_start + timedelta(seconds=2.5),
        },
        {
            "idx": 1,
            "speaker": "user",
            "text": "Hi, I need help with my account.",
            "started_at": call_start + timedelta(seconds=7.0),
        },
    ]

    result = check_recording_disclosure(turns, call_start)
    assert result["status"] == "pass"
    assert result["offending_turn_idx"] == 0
    assert "at 2.5s" in result["detail"]


def test_recording_disclosure_pass_boundary_29_9():
    call_start = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    turns = [
        {
            "idx": 0,
            "speaker": "agent",
            "text": "Good afternoon, welcome to customer service.",
            "started_at": call_start + timedelta(seconds=1.0),
        },
        {
            "idx": 1,
            "speaker": "user",
            "text": "Hello, can you hear me?",
            "started_at": call_start + timedelta(seconds=15.0),
        },
        {
            "idx": 2,
            "speaker": "agent",
            "text": "Yes, I can hear you clearly. Just a reminder that our conversation is being recorded.",
            "started_at": call_start + timedelta(seconds=29.9),
        },
    ]

    result = check_recording_disclosure(turns, call_start)
    assert result["status"] == "pass"
    assert result["offending_turn_idx"] == 2


def test_recording_disclosure_fail_boundary_30_1():
    call_start = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    turns = [
        {
            "idx": 0,
            "speaker": "agent",
            "text": "Good afternoon, welcome to customer service.",
            "started_at": call_start + timedelta(seconds=1.0),
        },
        {
            "idx": 1,
            "speaker": "agent",
            "text": "By the way, this call is recorded.",
            "started_at": call_start + timedelta(seconds=30.1),
        },
    ]

    result = check_recording_disclosure(turns, call_start)
    assert result["status"] == "fail"
    assert result["offending_turn_idx"] == 1
    assert "late at 30.1s" in result["detail"]


def test_recording_disclosure_fail_user_mentioned_not_agent():
    call_start = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    turns = [
        {
            "idx": 0,
            "speaker": "agent",
            "text": "Hello! How can I help you today?",
            "started_at": call_start + timedelta(seconds=2.0),
        },
        {
            "idx": 1,
            "speaker": "user",
            "text": "Is this call being recorded?",
            "started_at": call_start + timedelta(seconds=5.0),
        },
    ]

    result = check_recording_disclosure(turns, call_start)
    assert result["status"] == "fail"
    assert result["offending_turn_idx"] is None


def test_recording_disclosure_fail_no_mention():
    call_start = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
    turns = [
        {
            "idx": 0,
            "speaker": "agent",
            "text": "Hello, Acme support. How can I help?",
            "started_at": call_start + timedelta(seconds=2.0),
        },
        {
            "idx": 1,
            "speaker": "user",
            "text": "My router is broken.",
            "started_at": call_start + timedelta(seconds=8.0),
        },
    ]

    result = check_recording_disclosure(turns, call_start)
    assert result["status"] == "fail"


def test_no_operator_mention_pass():
    turns = [
        {"idx": 0, "speaker": "agent", "text": "I can offer you a 10% discount on your next month's bill."},
        {"idx": 1, "speaker": "user", "text": "That sounds great, thank you!"},
    ]
    result = check_no_operator_mention(turns)
    assert result["status"] == "pass"


def test_no_operator_mention_fail():
    turns = [
        {"idx": 0, "speaker": "agent", "text": "My supervisor just told me to offer you a discount."},
    ]
    result = check_no_operator_mention(turns)
    assert result["status"] == "fail"
    assert result["offending_turn_idx"] == 0
    assert "supervisor" in result["detail"].lower()
