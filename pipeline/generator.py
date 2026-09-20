"""Hugging Face generators for dissertation anchors E1–E4."""

from __future__ import annotations

import gc
import random
import re
import time
from typing import Any, Dict, Optional

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    GenerationConfig,
    TextStreamer,
)


# Protocol default: greedy decoding (DialoGPT uses beam search in generate()).
TEMPERATURE = None
MAX_NEW_TOKENS_SMALL = 128
MAX_NEW_TOKENS_LARGE = 160  # full 2–4 sentence replies for human rating
SEED = 42

# Dissertation anchors: one public Hugging Face model per historical era.
EPOCH_MODELS: Dict[str, Dict[str, Any]] = {
    "E1": {
        "model_id": "microsoft/DialoGPT-medium",
        "arch": "causal_dialogue",
        "year_label": "2019-2020",
        "large": False,
    },
    "E2": {
        "model_id": "facebook/blenderbot-400M-distill",
        "arch": "seq2seq",
        "year_label": "2020-2021",
        "large": False,
    },
    "E3": {
        "model_id": "microsoft/Phi-3-mini-4k-instruct",
        "arch": "chat",
        "year_label": "2023-2024",
        "large": True,
    },
    "E4": {
        "model_id": "Qwen/Qwen2.5-3B-Instruct",
        "arch": "chat",
        "year_label": "2024-2025",
        "large": True,
    },
}


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def pick_device(prefer_gpu: bool = True) -> str:
    if prefer_gpu and torch.cuda.is_available():
        return "cuda"
    if prefer_gpu and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def pick_dtype(device: str):
    if device in {"cuda", "mps"}:
        return torch.float16
    return torch.float32


def free_memory(device: str) -> None:
    gc.collect()
    if device == "cuda" and torch.cuda.is_available():
        torch.cuda.empty_cache()
    if device == "mps" and getattr(torch, "mps", None) is not None:
        try:
            torch.mps.empty_cache()
        except Exception:
            pass


class HFGenerator:
    def __init__(
        self,
        epoch_id: str,
        model_id: Optional[str] = None,
        device: Optional[str] = None,
    ):
        if epoch_id not in EPOCH_MODELS:
            raise ValueError(f"Unknown epoch_id: {epoch_id}")
        meta = EPOCH_MODELS[epoch_id]
        self.epoch_id = epoch_id
        self.arch = meta["arch"]
        self.large = bool(meta.get("large"))
        self.model_id = model_id or meta["model_id"]
        self.device = device or pick_device(prefer_gpu=True)
        self.dtype = pick_dtype(self.device)
        self.max_new_tokens = MAX_NEW_TOKENS_LARGE if self.large else MAX_NEW_TOKENS_SMALL

        print(
            f"  model={self.model_id}\n"
            f"  device={self.device} dtype={self.dtype} max_new_tokens={self.max_new_tokens}",
            flush=True,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=False)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        load_kwargs: Dict[str, Any] = {
            "dtype": self.dtype,
            "low_cpu_mem_usage": True,
            # Native transformers implementations only. Hub remote modeling_*.py
            # (esp. Phi-3) breaks on transformers 5.x DynamicCache (seen_tokens).
            "trust_remote_code": False,
        }
        if self.device == "mps":
            load_kwargs["attn_implementation"] = "eager"

        if self.arch == "seq2seq":
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id, **load_kwargs)
        else:
            self.model = AutoModelForCausalLM.from_pretrained(self.model_id, **load_kwargs)

        print(f"  architecture={type(self.model).__module__}.{type(self.model).__name__}", flush=True)
        print(f"  moving weights to {self.device} ...", flush=True)
        self.model.to(self.device)
        self.model.eval()
        # Transformers 5: Hub generation_config often has do_sample=None, which
        # is treated as SAMPLE (multinomial). Force greedy on the model object.
        self.model.generation_config.do_sample = False
        self.model.generation_config.temperature = None
        self.model.generation_config.top_p = None
        self.model.generation_config.top_k = None
        free_memory(self.device)
        print("  model ready", flush=True)

    def close(self) -> None:
        try:
            del self.model
        except Exception:
            pass
        free_memory(self.device)

    def _generate_from_ids(self, input_ids, attention_mask=None, attempt: int = 0) -> str:
        # Explicit GenerationConfig: Hub files leave do_sample=None, and in
        # transformers>=5 that falls through to multinomial sampling.
        eos = self.model.generation_config.eos_token_id
        if eos is None:
            eos = self.tokenizer.eos_token_id
        pad = self.model.generation_config.pad_token_id
        if pad is None:
            pad = self.tokenizer.pad_token_id

        # DialoGPT: beam search is far more coherent than greedy/sample on this model.
        use_beams = self.arch == "causal_dialogue"
        gen_kwargs: Dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens if not use_beams else min(80, self.max_new_tokens),
            "do_sample": False,
            "num_beams": 5 if use_beams else 1,
            "early_stopping": True if use_beams else False,
            "pad_token_id": pad,
            "eos_token_id": eos,
            "use_cache": True,
            "temperature": None,
            "top_p": None,
            "top_k": None,
        }
        if use_beams:
            gen_kwargs["no_repeat_ngram_size"] = 3
            gen_kwargs["min_new_tokens"] = 12
            gen_kwargs["length_penalty"] = 1.6

        gen_config = GenerationConfig(**gen_kwargs)
        streamer = None if use_beams else TextStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )
        mode = "beam5" if use_beams else "greedy"
        print(
            f"     generating {mode} ({self.device}, max_new_tokens={gen_kwargs['max_new_tokens']}, try={attempt + 1})",
            flush=True,
        )
        if self.large:
            print("     (first token can take 1–3 min — do not interrupt)", flush=True)
        print("     --- response ---", flush=True)
        t0 = time.time()
        with torch.inference_mode():
            output = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                generation_config=gen_config,
                streamer=streamer,
            )
        if self.device == "mps":
            try:
                torch.mps.synchronize()
            except Exception:
                pass
        elapsed = time.time() - t0
        print(f"\n     --- generate done in {elapsed:.1f}s ---", flush=True)
        if self.arch in {"causal_dialogue", "chat"}:
            new_tokens = output[0][input_ids.shape[-1] :]
            text = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        else:
            text = self.tokenizer.decode(output[0], skip_special_tokens=True).strip()
        # DialoGPT often continues the dialogue with a fake next User turn
        text = re.split(r"(?i)\n?\s*user\s*:", text)[0].strip()
        if text:
            print(text, flush=True)
        del output
        free_memory(self.device)
        return text

    def generate(self, prompt: str, user_text: str = "", attempt: int = 0) -> str:
        max_len = 512 if self.arch != "chat" else 768
        if self.arch == "chat":
            messages = [{"role": "user", "content": prompt}]
            if hasattr(self.tokenizer, "apply_chat_template"):
                text = self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            else:
                text = prompt
        else:
            text = prompt

        encoded = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=max_len
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        return self._generate_from_ids(
            encoded["input_ids"], encoded.get("attention_mask"), attempt=attempt
        )
