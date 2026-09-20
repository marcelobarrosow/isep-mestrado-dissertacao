"""Baseline and pipeline prompts, adapted to each generator architecture."""

from __future__ import annotations

from emotion_analyzer import EmotionalContext


def build_direct_prompt(user_text: str, arch: str = "chat") -> str:
    if arch == "causal_dialogue":
        return f"User: {user_text}\nAssistant:"
    if arch == "seq2seq":
        return user_text
    return (
        "You are a conversational assistant.\n\n"
        f"User message:\n{user_text}\n\n"
        "Produce a clear, helpful, and natural answer in English. "
        "Write 2 to 4 complete sentences and stop."
    )


def build_contextual_prompt(
    user_text: str, ctx: EmotionalContext, arch: str = "chat"
) -> str:
    if arch == "causal_dialogue":
        if ctx.ambivalent:
            return (
                f"User: {user_text}\n"
                f"(The user seems ambivalent: "
                f"{ctx.dominant_positive_emotion} and {ctx.dominant_negative_emotion}.)\n"
                "Assistant:"
            )
        return f"User: {user_text}\nAssistant:"
    if arch == "seq2seq":
        if ctx.ambivalent:
            return (
                f"{user_text} "
                f"[emotional ambivalence: {ctx.dominant_positive_emotion} "
                f"and {ctx.dominant_negative_emotion}]"
            )
        return user_text
    if ctx.ambivalent:
        context_text = (
            "Additional emotional context:\n"
            "The user's message appears to contain emotional ambivalence.\n"
            f"The dominant positive emotion is {ctx.dominant_positive_emotion}.\n"
            f"The dominant negative emotion is {ctx.dominant_negative_emotion}."
        )
    else:
        context_text = (
            "Additional emotional context:\n"
            "No clear emotional ambivalence was detected."
        )
    return (
        "You are a conversational assistant.\n\n"
        f"User message:\n{user_text}\n\n"
        f"{context_text}\n\n"
        "Use this emotional context only as background information when answering.\n"
        "Do not mention the emotional analysis, emotion labels, scores, or pipeline.\n"
        "Do not change your normal response style solely because this metadata is present.\n\n"
        "Produce a clear, helpful, and natural answer in English. "
        "Write 2 to 4 complete sentences and stop."
    )
