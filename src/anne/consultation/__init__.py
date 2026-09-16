"""Consultation instruments for ANNE V1 (evidence only, not cognitive authority)."""

from anne.consultation.chatgpt_web import ChatGPTWebConsultationAdapter
from anne.consultation.factory import create_consultation_adapter
from anne.consultation.openai_api import ChatGPTConsultationAdapter

__all__ = [
    "ChatGPTConsultationAdapter",
    "ChatGPTWebConsultationAdapter",
    "create_consultation_adapter",
]
