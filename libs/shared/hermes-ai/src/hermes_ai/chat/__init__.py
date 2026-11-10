"""Conversational RAG orchestration for Hermes.

This package is imported lazily through :attr:`hermes_ai.client.HermesAi.chat`
so the ingestion worker never loads LangChain or LangGraph at startup.
"""
