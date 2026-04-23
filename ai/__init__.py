"""
AI Processing Layer: Transform raw crypto data into trading signals.

This package orchestrates the AI pipeline:
1. ollama_client: Ollama API wrapper for LLM/vision models
2. summarizer: Reduce articles to key points (token optimization)
3. sentiment: Analyze news sentiment with confidence scores
4. input_builder: Combine all data into AI-ready JSON structure
5. llava_agent: Vision-based chart analysis
6. decision_engine: Final trading decision synthesis

Typical usage:
    from ai.input_builder import AIInputBuilder
    from ai.sentiment import SentimentAnalyzer
    from ai.summarizer import NewsSummarizer
    from ai.llava_agent import LLaVAChartAnalyzer
    from ai.decision_engine import DecisionEngine
    
    # Build AI inputs from raw data
    ai_inputs = AIInputBuilder.build_all_ai_inputs()
    
    # Analyze sentiment
    analyzer = SentimentAnalyzer()
    sentiments = analyzer.analyze_all_coins()
    
    # Analyze charts
    chart_analyzer = LLaVAChartAnalyzer()
    chart_analyses = chart_analyzer.analyze_all_charts(ai_inputs)
    
    # Generate trading decisions
    decisions = DecisionEngine.generate_all_trading_decisions(
        ai_inputs,
        sentiments,
        chart_analyses
    )
"""

__version__ = "1.0.0"
__author__ = "Crypto AI Pipeline"

# Lazy imports to allow flexible Ollama availability
def get_ollama_client():
    """Get Ollama client instance."""
    from ai.ollama_client import get_ollama_client as _get
    return _get()


def get_summarizer(use_ollama=True):
    """Get NewsSummarizer instance."""
    from ai.summarizer import NewsSummarizer
    return NewsSummarizer(use_ollama=use_ollama)


def get_sentiment_analyzer(use_ollama=True):
    """Get SentimentAnalyzer instance."""
    from ai.sentiment import SentimentAnalyzer
    return SentimentAnalyzer(use_ollama=use_ollama)


def get_input_builder():
    """Get AIInputBuilder interface."""
    from ai.input_builder import AIInputBuilder
    return AIInputBuilder


def get_chart_analyzer():
    """Get LLaVAChartAnalyzer instance."""
    from ai.llava_agent import LLaVAChartAnalyzer
    return LLaVAChartAnalyzer()


def get_decision_engine():
    """Get DecisionEngine interface."""
    from ai.decision_engine import DecisionEngine
    return DecisionEngine


__all__ = [
    "get_ollama_client",
    "get_summarizer",
    "get_sentiment_analyzer",
    "get_input_builder",
    "get_chart_analyzer",
    "get_decision_engine",
]
