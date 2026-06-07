"""
Test conversations for the Inbound Voice Agent.
"""
import json
from datetime import datetime

# Sample test conversations
TEST_CONVERSATIONS = [
    {
        "name": "General Information",
        "customer_id": "cust_001",
        "conversation": [
            {
                "customer": "What is Breakout?",
                "expected_topics": [
                    "escape room",
                    "real-life",
                    "puzzles",
                    "storyline"
                ]
            },
            {
                "customer": "Are players actually locked inside?",
                "expected_topics": [
                    "not locked",
                    "staff monitor",
                    "assist"
                ]
            }
        ]
    },

    {
        "name": "Booking Information",
        "customer_id": "cust_002",
        "conversation": [
            {
                "customer": "Do I need to book in advance?",
                "expected_topics": [
                    "online booking",
                    "advance booking",
                    "required"
                ]
            },
            {
                "customer": "Can I walk in without booking?",
                "expected_topics": [
                    "walk-ins",
                    "slot availability",
                    "advance payment"
                ]
            }
        ]
    },

    {
        "name": "Escape Room Pricing",
        "customer_id": "cust_003",
        "conversation": [
            {
                "customer": "How much does an escape room cost?",
                "expected_topics": [
                    "700",
                    "1000",
                    "per person"
                ]
            },
            {
                "customer": "Do you offer student discounts?",
                "expected_topics": [
                    "10%",
                    "student discount",
                    "valid ID"
                ]
            }
        ]
    },

    {
        "name": "Birthday Party Queries",
        "customer_id": "cust_004",
        "conversation": [
            {
                "customer": "Do you host birthday parties?",
                "expected_topics": [
                    "birthday parties",
                    "escape room",
                    "karaoke"
                ]
            },
            {
                "customer": "How many people can attend a birthday party?",
                "expected_topics": [
                    "50-80",
                    "35-40",
                    "capacity"
                ]
            }
        ]
    },

    {
        "name": "Corporate Events",
        "customer_id": "cust_005",
        "conversation": [
            {
                "customer": "Do you conduct corporate team building events?",
                "expected_topics": [
                    "corporate events",
                    "team building",
                    "escape room"
                ]
            },
            {
                "customer": "What activities are available?",
                "expected_topics": [
                    "scavenger hunt",
                    "detective job",
                    "virtual events"
                ]
            }
        ]
    },

    {
        "name": "Location and Timing",
        "customer_id": "cust_006",
        "conversation": [
            {
                "customer": "Where is Breakout located?",
                "expected_topics": [
                    "Koramangala",
                    "Whitefield",
                    "JP Nagar"
                ]
            },
            {
                "customer": "How early should I arrive?",
                "expected_topics": [
                    "20 minutes",
                    "before slot"
                ]
            }
        ]
    },

    {
        "name": "Escalation Scenario",
        "customer_id": "cust_007",
        "conversation": [
            {
                "customer": "What is your international shipping policy?",
                "expected_topics": [
                    "not found",
                    "escalation",
                    "human assistance"
                ]
            }
        ]
    }
]


def get_test_conversations():
    """Get all test conversations."""
    return TEST_CONVERSATIONS


def get_conversation_by_name(name: str):
    """Get test conversation by name."""
    for conv in TEST_CONVERSATIONS:
        if conv["name"].lower() == name.lower():
            return conv
    return None


if __name__ == "__main__":
    # Print test conversations
    print("Inbound Agent Test Conversations")
    print("=" * 50)

    for i, conv in enumerate(TEST_CONVERSATIONS, 1):
        print(f"\n{i}. {conv['name']}")
        print(f"   Customer ID: {conv['customer_id']}")
        print(f"   Messages: {len(conv['conversation'])}")
        for j, msg in enumerate(conv['conversation'], 1):
            print(f"   - {msg['customer'][:50]}...")
