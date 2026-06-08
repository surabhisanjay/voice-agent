# """
# LangGraph workflow for the Inbound Voice Agent.
# """
# import logging
# import uuid
# import re
# import json
# from typing import Any, Dict, List
# from datetime import datetime
# from langgraph.graph import StateGraph, END
# from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# from langchain_ollama import ChatOllama
# from sqlalchemy.orm import Session
# from app.config import settings
# from app.rag.retriever import DocumentRetriever
# from app.agent.memory import ConversationMemory
# from app.models import EscalationLog

# logger = logging.getLogger(__name__)


# class AgentState:
#     """State for the agent graph."""

#     def __init__(self):
#         self.user_input: str = ""
#         self.retrieved_documents: List[str] = []
#         self.context: str = ""
#         self.response: str = ""
#         self.confidence_score: float = 0.0
#         self.should_escalate: bool = False
#         self.escalation_reason: str = ""
#         self.memory: ConversationMemory = None
#         self.db: Session = None


# class InboundVoiceAgent:
#     """LangGraph-based inbound voice agent."""

#     def __init__(self, db: Session):
#         """Initialize the agent."""
#         self.db = db
        
#         self.llm = ChatOllama(
#             model=settings.llm_model,
#             temperature=0.1,
#             top_p=0.8
#         )
#         self.retriever = DocumentRetriever(k=5, score_threshold=0.6)
#         self.graph = self._build_graph()
#         logger.info("InboundVoiceAgent initialized")

#     def _build_graph(self) -> StateGraph:
#         """Build the LangGraph workflow."""
#         graph = StateGraph(dict)

#         graph.add_node("retrieve", self._retrieve_documents)
#         graph.add_node("generate", self._generate_response)
#         graph.add_node("evaluate", self._evaluate_confidence)
#         graph.add_node("escalate", self._handle_escalation)
#         graph.add_node("respond", self._prepare_response)

#         graph.add_edge("retrieve", "generate")
#         graph.add_conditional_edges(
#             "generate",
#             self._should_escalate,
#             {True: "escalate", False: "evaluate"}
#         )
#         graph.add_edge("evaluate", "respond")
#         graph.add_edge("escalate", "respond")
#         graph.add_edge("respond", END)

#         graph.set_entry_point("retrieve")
#         return graph.compile()

#     def _retrieve_documents(self, state: Dict[str, Any]) -> Dict[str, Any]:
        
#         """Retrieve relevant documents."""
#         user_input = state.get("user_input", "")
#         logger.info(f"Retrieving documents for: {user_input}")

#         if not user_input:
#             state["retrieved_documents"] = []
#             state["context"] = "No query provided."
#             return state

#         documents = self.retriever.retrieve(user_input, k=3)
#         state["retrieved_documents"] = [doc.page_content for doc in documents]
#         state["context"] = self.retriever.format_context(documents)

#         logger.info(f"Retrieved {len(documents)} documents")
#         return state

#     def _generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         """Generate response using LLM."""
#         user_input = state.get("user_input", "")
#         context = state.get("context", "")
#         memory = state.get("memory")

#         conversation_history = memory.get_context_string() if memory else ""

#         system_prompt = f"""
# You are a customer support assistant.

# Use ONLY the information provided in the retrieved documents.

# Rules:
# - Answer directly and confidently when the answer exists in the documents.
# - Summarize information in natural customer-friendly language.
# - Do not copy raw document passages.
# - Do not mention filenames or document names.
# - Do not invent information.
# - If the answer is not available in the retrieved documents, say:
#   "I couldn't find information about that in the available documents."

# For questions like:
# - "What is..."
# - "Tell me about..."
# - "Explain..."
# - "Describe..."

# provide a short explanation rather than quoting text.

# Retrieved Information:
# {context}

# Conversation History:
# {conversation_history}
# """
#         extracted_context = self._extract_relevant_context(context, user_input)
#         if extracted_context:
#             context = (
#                 "Relevant extracted passage:\n"
#                 f"{extracted_context}\n\n"
#                 "Full retrieved documents:\n"
#                 f"{context}"
#             )

#         try:
#             messages = [
#                 SystemMessage(content=system_prompt),
#                 HumanMessage(content=user_input)
#             ]

#             response = self.llm.invoke(messages)
#             state["response"] = response.content
#             logger.info(f"Generated response: {response.content[:100]}")

#             # if self._should_override_no_info_response(state["response"], context):
#             #     extracted = self._extract_relevant_context(context, user_input)
#             #     if extracted:
#             #         state["response"] = (
#             #             "According to the provided documents: "
#             #             f"{extracted}"
#             #         )
#             #         logger.info("Overrode missing-info response with document excerpt.")

#         except Exception as e:
#             logger.error(f"Error generating response: {e}")
#             state["response"] = (
#                 "Sorry, I'm currently unable to access the knowledge base or LLM service. "
#                 "Please try again later or contact a human representative."
#             )
#             state["should_escalate"] = True
#             state["escalation_reason"] = "llm_error"
#             state["confidence_score"] = 0.0

#         if not state["response"].strip():
#             state["response"] = (
#                 "Sorry, I'm currently unable to answer that question. "
#                 "Please try again later or contact a human representative."
#             )
#             state["should_escalate"] = True
#             state["escalation_reason"] = "empty_response"
#             state["confidence_score"] = 0.0

#         return state

#     def _should_override_no_info_response(self, response: str, context: str) -> bool:
#         """Determine whether a no-info response should be overridden."""
#         response_lower = response.lower()

#         no_info_patterns = [
#             r"couldn't find any(?:.*)information",
#             r"could not find any(?:.*)information",
#             r"no relevant information",
#             r"information is not available",
#             r"does not appear to (?:contain|include) the answer",
#             r"no.*documents.*found",
#             r"i don't have enough information",
#             r"i don't have access",
#             r"unable to.*find",
#             r"\bpossibly\b",
#             r"\bmight\b",
#             r"\bmay be\b",
#             r"\bit could\b",
#             r"\bit may\b",
#             r"\bit might\b",
#             r"\bperhaps\b",
#             r"\bmaybe\b",
#             r"it appears",
#         ]

#         if not context.strip():
#             return False

#         return any(re.search(pattern, response_lower) for pattern in no_info_patterns)

#     def _extract_relevant_context(self, context: str, user_input: str) -> str:
#         """Extract relevant sentences from retrieved context based on query content."""
#         user_input_lower = user_input.lower()

#         # Keywords that are specifically useful for customer policy queries.
#         important_terms = [
#             "cancellation",
#             "cancel",
#             "refund",
#             "reschedule",
#             "rescheduling",
#             "policy",
#             "fee",
#             "booking",
#             "advance",
#             "payment",
#             "decor",
#             "decoration",
#             "decorations",
#             "catering",
#             "venue",
#             "service",
#             "deposit",
#             "availability",
#             "hours",
#             "pricing",
#         ]
#         query_terms = [term for term in important_terms if term in user_input_lower]

#         # Fallback to matching any meaningful word from user input if the query
#         # doesn't contain our predefined keywords.
#         if not query_terms:
#             query_terms = [
#                 word
#                 for word in re.findall(r"\b[a-z]{4,}\b", user_input_lower)
#                 if word not in {"what", "when", "where", "your", "you", "can", "the", "and", "for", "with", "this", "that"}
#             ]

#         if not query_terms:
#             return ""

#         sentences = re.split(r'(?<=[.!?])\s+', context)
#         matches = []
#         for sentence in sentences:
#             sentence_lower = sentence.lower()
#             if any(term in sentence_lower for term in query_terms):
#                 cleaned = sentence.strip()
#                 if cleaned and cleaned not in matches:
#                     matches.append(cleaned)

#         if not matches:
#             # Use the first two sentences of context as a last-resort fallback.
#             sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', context) if s.strip()]
#             return " ".join(sentences[:2]) if sentences else ""

#         return " ".join(matches[:3])

#     def _should_escalate(self, state: Dict[str, Any]) -> bool:
#         """Determine if query should be escalated."""
#         context = state.get("context", "")
#         response = state.get("response", "")

#         if "No relevant documents found" in context:
#             state["escalation_reason"] = "no_documents_found"
#             state["confidence_score"] = 0.25
#             logger.info("No relevant documents found; not escalating automatically.")
#             return False

#         escalation_phrases = [
#             "unable to access",
#             "please try again later",
#             "escalating your inquiry"
#         ]
#         if any(phrase in response.lower() for phrase in escalation_phrases):
#             state["confidence_score"] = 0.0
#             state["should_escalate"] = True
#             state["escalation_reason"] = state.get("escalation_reason", "low_confidence")
#             if state["escalation_reason"] == "":
#                 state["escalation_reason"] = "low_confidence"
#             return True

#         return False

#     def _evaluate_confidence(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         """Evaluate response confidence."""
#         state["confidence_score"] = 0.85
#         return state

#     def _handle_escalation(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         """Handle escalation."""
#         session_id = state.get("session_id", "")
#         reason = state.get("escalation_reason", "low_confidence")

#         escalation = EscalationLog(
#             id=str(uuid.uuid4()),
#             session_id=session_id,
#             message_id=str(uuid.uuid4()),
#             reason=reason,
#             confidence_score=0.0,
#             resolved=False
#         )
#         self.db.add(escalation)
#         self.db.commit()

#         state["confidence_score"] = 0.0
#         state["should_escalate"] = True
#         state["response"] = (
#             "I don't have enough information to fully answer your question. "
#             "I'm escalating your inquiry to a human agent who will assist you shortly."
#         )
#         logger.info(f"Query escalated: {reason}")
#         return state

#     def _prepare_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         """Prepare final response."""
#         return state

#     def process_query(self, user_input: str, session_id: str, memory: ConversationMemory) -> Dict[str, Any]:
#         """Process a user query through the graph."""
#         state = {
#             "user_input": user_input,
#             "session_id": session_id,
#             "memory": memory,
#             "db": self.db,
#             "retrieved_documents": [],
#             "context": "",
#             "response": "",
#             "confidence_score": 0.0,
#             "should_escalate": False,
#             "escalation_reason": ""
#         }

#         result = self.graph.invoke(state)
#         return result
"""
LangGraph workflow for the Inbound Voice Agent.
"""
import logging
import uuid
import re
import json
from typing import Any, Dict, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session
from app.config import settings
from app.rag.retriever import DocumentRetriever
from app.agent.memory import ConversationMemory
from app.models import EscalationLog

logger = logging.getLogger(__name__)


class AgentState:
    """State for the agent graph."""

    def __init__(self):
        self.user_input: str = ""
        self.retrieved_documents: List[str] = []
        self.context: str = ""
        self.response: str = ""
        self.confidence_score: float = 0.0
        self.should_escalate: bool = False
        self.escalation_reason: str = ""
        self.memory: ConversationMemory = None
        self.db: Session = None


class InboundVoiceAgent:
    """LangGraph-based inbound voice agent."""

    def __init__(self, db: Session):
        """Initialize the agent."""
        self.db = db
        
        self.llm = ChatOllama(
            model=settings.llm_model,
            temperature=0.1,
            top_p=0.8
        )
        self.retriever = DocumentRetriever(k=5, score_threshold=0.6)
        self.graph = self._build_graph()
        logger.info("InboundVoiceAgent initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph = StateGraph(dict)

        graph.add_node("retrieve", self._retrieve_documents)
        graph.add_node("generate", self._generate_response)
        graph.add_node("evaluate", self._evaluate_confidence)
        graph.add_node("escalate", self._handle_escalation)
        graph.add_node("respond", self._prepare_response)

        graph.add_edge("retrieve", "generate")
        graph.add_conditional_edges(
            "generate",
            self._should_escalate,
            {True: "escalate", False: "evaluate"}
        )
        graph.add_edge("evaluate", "respond")
        graph.add_edge("escalate", "respond")
        graph.add_edge("respond", END)

        graph.set_entry_point("retrieve")
        return graph.compile()

    def _retrieve_documents(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant documents."""
        user_input = state.get("user_input", "")
        logger.info(f"Retrieving documents for: {user_input}")

        if not user_input:
            state["retrieved_documents"] = []
            state["context"] = "No query provided."
            return state

        query = user_input.lower()

        if "how long" in query:
            query += " duration time length minutes hours"

        if query.startswith("what is"):
            query += " description overview explanation"

        if query.startswith("tell me about"):
            query += " description overview explanation"

        documents = self.retriever.retrieve(query, k=5)

        state["retrieved_documents"] = [doc.page_content for doc in documents]
        state["context"] = self.retriever.format_context(documents)

        logger.info(f"Retrieved {len(documents)} documents")
        return state

    def _generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using LLM."""
        user_input = state.get("user_input", "")
        context = state.get("context", "")
        memory = state.get("memory")

        conversation_history = memory.get_context_string() if memory else ""

        system_prompt = f"""
You are a customer support assistant.

Use ONLY the information provided in the retrieved documents.

Rules:
- Answer directly and confidently when the answer exists in the documents.
- Summarize information in natural customer-friendly language.
- Do not copy raw document passages.
- Do not mention filenames or document names.
- Do not invent information.
- If the answer is not available in the retrieved documents, say:
  "I couldn't find information about that in the available documents."

For questions like:
- "What is..."
- "Tell me about..."
- "Explain..."
- "Describe..."

provide a short explanation rather than quoting text.

Retrieved Information:
{context}

Conversation History:
{conversation_history}
"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]

            response = self.llm.invoke(messages)
            state["response"] = response.content
            logger.info(f"Generated response: {response.content[:100]}")

            # if self._should_override_no_info_response(state["response"], context):
            #     extracted = self._extract_relevant_context(context, user_input)
            #     if extracted:
            #         state["response"] = (
            #             "According to the provided documents: "
            #             f"{extracted}"
            #         )
            #         logger.info("Overrode missing-info response with document excerpt.")

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            state["response"] = (
                "Sorry, I'm currently unable to access the knowledge base or LLM service. "
                "Please try again later or contact a human representative."
            )
            state["should_escalate"] = True
            state["escalation_reason"] = "llm_error"
            state["confidence_score"] = 0.0

        if not state["response"].strip():
            state["response"] = (
                "Sorry, I'm currently unable to answer that question. "
                "Please try again later or contact a human representative."
            )
            state["should_escalate"] = True
            state["escalation_reason"] = "empty_response"
            state["confidence_score"] = 0.0

        return state

    def _should_override_no_info_response(self, response: str, context: str) -> bool:
        """Determine whether a no-info response should be overridden."""
        response_lower = response.lower()

        no_info_patterns = [
            r"couldn't find any(?:.*)information",
            r"could not find any(?:.*)information",
            r"no relevant information",
            r"information is not available",
            r"does not appear to (?:contain|include) the answer",
            r"no.*documents.*found",
            r"i don't have enough information",
            r"i don't have access",
            r"unable to.*find",
            r"\bpossibly\b",
            r"\bmight\b",
            r"\bmay be\b",
            r"\bit could\b",
            r"\bit may\b",
            r"\bit might\b",
            r"\bperhaps\b",
            r"\bmaybe\b",
            r"it appears",
        ]

        if not context.strip():
            return False

        return any(re.search(pattern, response_lower) for pattern in no_info_patterns)

    def _extract_relevant_context(self, context: str, user_input: str) -> str:
        """Extract relevant sentences from retrieved context based on query content."""
        user_input_lower = user_input.lower()

        # Keywords that are specifically useful for customer policy queries.
        important_terms = [
            "cancellation",
            "cancel",
            "refund",
            "reschedule",
            "rescheduling",
            "policy",
            "fee",
            "booking",
            "advance",
            "payment",
            "decor",
            "decoration",
            "decorations",
            "catering",
            "venue",
            "service",
            "deposit",
            "availability",
            "hours",
            "pricing",
        ]
        query_terms = [term for term in important_terms if term in user_input_lower]

        # Fallback to matching any meaningful word from user input if the query
        # doesn't contain our predefined keywords.
        if not query_terms:
            query_terms = [
                word
                for word in re.findall(r"\b[a-z]{4,}\b", user_input_lower)
                if word not in {"what", "when", "where", "your", "you", "can", "the", "and", "for", "with", "this", "that"}
            ]

        if not query_terms:
            return ""

        sentences = re.split(r'(?<=[.!?])\s+', context)
        matches = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in query_terms):
                cleaned = sentence.strip()
                if cleaned and cleaned not in matches:
                    matches.append(cleaned)

        if not matches:
            # Use the first two sentences of context as a last-resort fallback.
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', context) if s.strip()]
            return " ".join(sentences[:2]) if sentences else ""

        return " ".join(matches[:3])

    def _should_escalate(self, state: Dict[str, Any]) -> bool:
        """Determine if query should be escalated."""
        context = state.get("context", "")
        response = state.get("response", "")

        if "No relevant documents found" in context:
            state["escalation_reason"] = "no_documents_found"
            state["confidence_score"] = 0.25
            logger.info("No relevant documents found; not escalating automatically.")
            return False

        escalation_phrases = [
            "unable to access",
            "please try again later",
            "escalating your inquiry"
        ]
        if any(phrase in response.lower() for phrase in escalation_phrases):
            state["confidence_score"] = 0.0
            state["should_escalate"] = True
            state["escalation_reason"] = state.get("escalation_reason", "low_confidence")
            if state["escalation_reason"] == "":
                state["escalation_reason"] = "low_confidence"
            return True

        return False

    def _evaluate_confidence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate response confidence."""
        state["confidence_score"] = 0.85
        return state

    def _handle_escalation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle escalation."""
        session_id = state.get("session_id", "")
        reason = state.get("escalation_reason", "low_confidence")

        escalation = EscalationLog(
            id=str(uuid.uuid4()),
            session_id=session_id,
            message_id=str(uuid.uuid4()),
            reason=reason,
            confidence_score=0.0,
            resolved=False
        )
        self.db.add(escalation)
        self.db.commit()

        state["confidence_score"] = 0.0
        state["should_escalate"] = True
        state["response"] = (
            "I don't have enough information to fully answer your question. "
            "I'm escalating your inquiry to a human agent who will assist you shortly."
        )
        logger.info(f"Query escalated: {reason}")
        return state

    def _prepare_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare final response."""
        return state

    def process_query(self, user_input: str, session_id: str, memory: ConversationMemory) -> Dict[str, Any]:
        """Process a user query through the graph."""
        state = {
            "user_input": user_input,
            "session_id": session_id,
            "memory": memory,
            "db": self.db,
            "retrieved_documents": [],
            "context": "",
            "response": "",
            "confidence_score": 0.0,
            "should_escalate": False,
            "escalation_reason": ""
        }

        result = self.graph.invoke(state)
        return result
