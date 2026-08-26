"""Safe environment and repository metadata for reproducible benchmarks."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BenchmarkEnvironment:
    """Non-secret provider settings recorded with benchmark artifacts."""

    provider: str
    model: str
    max_tokens: int
    timeout_seconds: float
    reasoning_effort: str | None
    git_commit: str


_MODEL_SETTINGS: dict[str, tuple[str, str]] = {
    "anthropic": ("CLAUDE_MODEL", "claude-sonnet-5"),
    "openai": ("OPENAI_MODEL", "gpt-5.6-luna"),
    "groq": ("GROQ_MODEL", "openai/gpt-oss-20b"),
    "openrouter": ("OPENROUTER_MODEL", "openrouter/free"),
    "custom": ("OPENAI_COMPAT_MODEL", "unknown"),
}

_GROQ_GPT_OSS_MODELS = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}


def benchmark_environment_from_env(
    env: Mapping[str, str] | None = None,
    *,
    repository_root: Path | None = None,
) -> BenchmarkEnvironment:
    """Read only non-secret settings after provider composition has validated the environment."""
    settings = os.environ if env is None else env
    provider = settings.get("LLM_PROVIDER", "anthropic").strip().lower()
    model_key, default_model = _MODEL_SETTINGS.get(provider, ("", "unknown"))
    model = settings.get(model_key, default_model).strip() if model_key else default_model

    return BenchmarkEnvironment(
        provider=provider,
        model=model,
        max_tokens=int(settings.get("LLM_MAX_TOKENS", "1200")),
        timeout_seconds=float(settings.get("LLM_TIMEOUT_SECONDS", "30")),
        reasoning_effort=_effective_reasoning_effort(provider=provider, model=model),
        git_commit=_git_commit(
            settings=settings,
            repository_root=repository_root or Path.cwd(),
        ),
    )


def _effective_reasoning_effort(*, provider: str, model: str) -> str | None:
    if provider == "groq" and model in _GROQ_GPT_OSS_MODELS:
        return "medium"
    return None


def _git_commit(*, settings: Mapping[str, str], repository_root: Path) -> str:
    explicit = settings.get("AUTONOMY_LAB_GIT_COMMIT") or settings.get("GITHUB_SHA")
    if explicit and explicit.strip():
        return explicit.strip()

    git_dir = repository_root / ".git"
    if git_dir.is_file():
        pointer = git_dir.read_text(encoding="utf-8").strip()
        prefix = "gitdir: "
        if pointer.startswith(prefix):
            candidate = Path(pointer.removeprefix(prefix))
            if candidate.is_absolute():
                git_dir = candidate
            else:
                git_dir = (repository_root / candidate).resolve()

    head = git_dir / "HEAD"
    if not head.is_file():
        return "unknown"
    head_value = head.read_text(encoding="utf-8").strip()
    if not head_value.startswith("ref: "):
        return head_value or "unknown"

    ref_name = head_value.removeprefix("ref: ")
    loose_ref = git_dir / ref_name
    if loose_ref.is_file():
        return loose_ref.read_text(encoding="utf-8").strip() or "unknown"

    packed_refs = git_dir / "packed-refs"
    if packed_refs.is_file():
        for line in packed_refs.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith(("#", "^")):
                continue
            sha, _, name = line.partition(" ")
            if name == ref_name:
                return sha
    return "unknown"
