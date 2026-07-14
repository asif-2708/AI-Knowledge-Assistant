import re

class ContentGuardrails:
    # 1. Prompt Injection and Jailbreak Patterns
    PROMPT_INJECTION_PATTERNS = [
        r"(ignore|disregard|override|forget)\s+(all\s+)?(previous|prior)\s+(instructions|prompts|directives)",
        r"you\s+are\s+now\s+a(n)?\s+(unrestricted|jailbroken|developer\s+mode)",
        r"system\s+(prompt|override|bypass)",
        r"ignore\s+the\s+system\s+prompt",
        r"dan\s+mode|jailbreak",
        r"assistant\s+instructions\s+override",
    ]
    
    # 2. PII Patterns (API keys, Emails, Credit Cards)
    PII_PATTERNS = {
        "api_key": r"(sk-[a-zA-Z0-9]{20,})|(AIzaSy[a-zA-Z0-9_\-]{35})|(gsk_[a-zA-Z0-9_\-]{40,})|(AQ\.[a-zA-Z0-9_\-]{45,})",
        "email": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    }
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> tuple[bool, str]:
        """
        Check if the prompt contains potential jailbreaks or prompt injections.
        Returns (is_safe, message).
        """
        if not prompt:
            return True, ""
            
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return False, "Safety Alert: Input query was flagged by guardrails as a potential prompt injection attempt."
        return True, ""
        
    @classmethod
    def sanitize_output(cls, text: str) -> str:
        """
        Scan response text for PII or API Keys and redact them.
        """
        if not text:
            return text
            
        sanitized = text
        for pii_type, pattern in cls.PII_PATTERNS.items():
            sanitized = re.sub(pattern, f"[REDACTED {pii_type.upper()}]", sanitized)
        return sanitized
