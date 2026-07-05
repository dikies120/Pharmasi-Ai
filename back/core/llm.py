import ollama
from typing import Any, Optional
from back.core.settings import settings

class LLM:

    def __init__(self):
        self.host = settings.OLLAMA_HOST.strip()
        self.client = ollama.Client(host=self.host)
        self.configured_model = settings.OLLAMA_MODEL
        self.model = self.configured_model
        self.model_names: list[str] = []
        self.model_available = self.debug_connection(verbose=False)

    @staticmethod
    def _normalized_model_name(model_name: str) -> str:
        return str(model_name or "").strip().lower().split("/", 1)[-1]

    def _resolve_model_name(self, candidates: list[str]) -> str | None:
        if not candidates:
            return None

        target = self.configured_model.strip()
        if not target:
            return None

        for candidate in candidates:
            if candidate == target:
                return candidate

        target_lower = target.lower()
        for candidate in candidates:
            if candidate.lower() == target_lower:
                return candidate

        target_normalized = self._normalized_model_name(target)
        for candidate in candidates:
            if self._normalized_model_name(candidate) == target_normalized:
                return candidate

        return None

    def debug_connection(self, verbose: bool = True) -> bool:
        try:
            models_response = self.client.list()
            if isinstance(models_response, dict):
                raw_models = models_response.get("models", [])
            else:
                raw_models = getattr(models_response, "models", [])

            model_names = []
            for model in raw_models:
                if isinstance(model, dict):
                    model_name = model.get("name") or model.get("model")
                else:
                    model_name = getattr(model, "name", None) or getattr(model, "model", None)

                if model_name:
                    model_names.append(str(model_name))

            self.model_names = model_names

            resolved_model = self._resolve_model_name(model_names)
            model_found = resolved_model is not None

            if model_found:
                self.model = resolved_model
            else:
                self.model = self.configured_model

            if verbose:
                if model_found:
                    if self.model != self.configured_model:
                        print(
                            f"[LLM DEBUG] Connected to model '{self.model}' on {self.host} "
                            f"(configured: '{self.configured_model}')"
                        )
                    else:
                        print(f"[LLM DEBUG] Connected to model '{self.model}' on {self.host}")
                else:
                    print(
                        f"[LLM DEBUG] Connected to Ollama on {self.host}, "
                        f"but model '{self.configured_model}' is not in local list: {model_names}"
                    )

            return model_found
        except Exception as exc:
            self.model_names = []
            self.model = self.configured_model
            if verbose:
                print(f"[LLM DEBUG] Failed to connect to Ollama on {self.host}: {exc}")
            return False

    def _debug_connection(self) -> None:
        self.model_available = self.debug_connection(verbose=True)

    def generate(
        self,
        prompt: str,
        options: Optional[dict[str, Any]] = None,
        response_format: Optional[str] = None,
        system: Optional[str] = None,
    ) -> str:
        if not self.model_available:
            self.model_available = self.debug_connection(verbose=False)

        if not self.model_available:
            raise RuntimeError(
                f"Model '{self.configured_model}' tidak tersedia di Ollama {self.host}. "
                f"Available: {self.model_names}"
            )

        generate_kwargs: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "options": options or {},
        }
        if response_format:
            generate_kwargs["format"] = response_format
        if system:
            generate_kwargs["system"] = system

        response = self.client.generate(**generate_kwargs)
        return response["response"]


def get_llm():
    return LLM()


def _run_module_debug() -> None:
    print("[LLM DEBUG] Running back.core.llm self-check...")
    llm = get_llm()
    llm.debug_connection(verbose=True)


if __name__ == "__main__":
    _run_module_debug()