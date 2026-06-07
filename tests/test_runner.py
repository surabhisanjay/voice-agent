"""
Test runner for the Inbound Voice Agent.
"""
import sys
import os
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_conversations import get_test_conversations
from app.database import init_db, SessionLocal
from app.agent.inbound_agent import InboundVoiceAgent
from app.agent.memory import create_session, get_or_create_memory
from app.rag.ingestion import get_rag_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_test_conversation(agent: InboundVoiceAgent, conversation: dict, db):
    """Run a single test conversation."""
    print(f"\n{'='*60}")
    print(f"Test: {conversation['name']}")
    print(f"Customer ID: {conversation['customer_id']}")
    print(f"{'='*60}")

    session_id = create_session(conversation['customer_id'], db)
    memory = get_or_create_memory(session_id, conversation['customer_id'], db)

    results = {
        "name": conversation['name'],
        "customer_id": conversation['customer_id'],
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "exchanges": []
    }

    for i, exchange in enumerate(conversation['conversation'], 1):
        customer_query = exchange['customer']
        expected_topics = exchange.get('expected_topics', [])

        print(f"\n[Exchange {i}]")
        print(f"Customer: {customer_query}")

        # Process query
        result = agent.process_query(customer_query, session_id, memory)

        # Store in memory
        memory.add_message("user", customer_query)
        memory.add_message(
            "assistant",
            result["response"],
            result["confidence_score"],
            ",".join(result["retrieved_documents"][:3]) if result["retrieved_documents"] else None
        )

        print(f"Agent: {result['response']}")
        print(f"Confidence: {result['confidence_score']:.2f}")
        print(f"Escalated: {result['should_escalate']}")

        # Check if expected topics are in response
        found_topics = []
        response_lower = result['response'].lower()
        for topic in expected_topics:
            if topic.lower() in response_lower:
                found_topics.append(topic)

        print(f"Expected Topics Coverage: {len(found_topics)}/{len(expected_topics)}")

        results['exchanges'].append({
            "customer": customer_query,
            "agent": result["response"],
            "confidence": result["confidence_score"],
            "escalated": result["should_escalate"],
            "expected_topics": expected_topics,
            "found_topics": found_topics,
            "topic_coverage": len(found_topics) / len(expected_topics) if expected_topics else 1.0
        })

    return results


def main():
    """Run all tests."""
    logger.info("Initializing test environment...")

    # Initialize database
    init_db()
    db = SessionLocal()

    # Ensure RAG documents are ingested before running tests
    pipeline = get_rag_pipeline()
    pipeline.ingest_documents()

    # Create agent
    agent = InboundVoiceAgent(db)

    # Get test conversations
    conversations = get_test_conversations()

    logger.info(f"Running {len(conversations)} test conversations...")

    all_results = []

    for conversation in conversations:
        try:
            results = run_test_conversation(agent, conversation, db)
            all_results.append(results)
        except Exception as e:
            logger.error(f"Error running test '{conversation['name']}': {e}")

    # Print summary
    print(f"\n\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    total_exchanges = sum(len(r['exchanges']) for r in all_results)
    total_escalations = sum(
        1 for r in all_results
        for e in r['exchanges']
        if e['escalated']
    )
    avg_confidence = sum(
        e['confidence'] for r in all_results
        for e in r['exchanges']
    ) / total_exchanges if total_exchanges > 0 else 0

    print(f"Tests Run: {len(all_results)}")
    print(f"Total Exchanges: {total_exchanges}")
    print(f"Escalations: {total_escalations}")
    print(f"Average Confidence: {avg_confidence:.2f}")

    # Save results to file
    results_file = "test_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Results saved to {results_file}")

    db.close()


if __name__ == "__main__":
    main()
